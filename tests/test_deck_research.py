"""Offline foundation tests; reuse the certified local stores and mapping fixtures."""
from copy import deepcopy
import json
import socket
import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError
from pokelab import deck_research as d
from pokelab.agent_context import canonical
from pokelab.agent_context_sources import Unavailable
from pokelab.rules.models import digest
from tcg_lab.card_db import SQLiteCards
from test_agent_context import setup
from test_research import research, KEY, TODAY


@pytest.fixture(autouse=True)
def blocked(monkeypatch):
    def deny(*a,**k): raise AssertionError('No network in deck foundation')
    monkeypatch.setattr(socket.socket,'connect',deny)
    monkeypatch.setattr(socket.socket,'connect_ex',deny)


def profile(setup, **kw):
    return d.build_profile(setup[0],revision=7,as_of=TODAY,archetype=KEY,**kw)


def test_snapshot_provenance_readonly_determinism(setup,monkeypatch):
    sources,_=setup; before={k:p.read_bytes() for k,p in sources.paths.items()}
    connect=sqlite3.connect
    def readonly(path,*a,**kw):
        assert kw.get('uri') and '?mode=ro' in str(path)
        return connect(path,*a,**kw)
    monkeypatch.setattr(sqlite3,'connect',readonly)
    one=profile(setup);two=profile(setup)
    assert one==two and canonical(one)==canonical(two)
    assert one.total==60 and one.population.eligible_lists==16
    assert one.population.excluded_unmapped==1 and len(one.population.references)==16
    assert all(r.url and r.event_date and r.content_hash for r in one.population.references)
    assert one.content_hash==digest(one.model_dump(mode='json',exclude={'content_hash'}))
    assert before=={k:p.read_bytes() for k,p in sources.paths.items()}
    with pytest.raises(ValidationError): one.total=1
    assert len(one.matching_observations)==16  # Ambiguous exact vectors, never a chosen creator.


@pytest.mark.parametrize('included,expected',[(16,{'ARCHETYPE_CORE','COMMON_PRESENT'}),(10,{'COMMON_PRESENT'}),
    (5,set()),(4,{'UNCOMMON_PRESENT'})])
def test_thresholds(included,expected):
    row=d.compare('id','card',2,[2]*included+[0]*(20-included))
    assert set(row.characteristics)==expected
    assert row.inclusion_rate==included/20


def test_math_absence_and_quantity_boundaries():
    row=d.compare('id','card',5,[0,1,2,2,4])
    assert row.mean_quantity_when_included==2.25 and row.median_quantity_when_included==2
    assert row.modes==(2,) and row.typical_range==(1,4)
    assert [(b.quantity,b.lists) for b in row.distribution]==[(0,1),(1,1),(2,2),(4,1)]
    assert 'ABOVE_TYPICAL_QUANTITY' in row.characteristics
    assert 'ABOVE_TYPICAL_QUANTITY' not in d.compare('i','c',4,[1,2,4]).characteristics
    assert 'BELOW_TYPICAL_QUANTITY' in d.compare('i','c',1,[2,3]).characteristics
    absent=d.compare('i','c',0,[2]*10+[0]*10)
    assert absent.characteristics==('COMMON_ABSENT',) and absent.active_quantity==0
    assert d.compare('i','c',3,[1]*4+[0]*16).characteristics==('UNCOMMON_PRESENT','ABOVE_TYPICAL_QUANTITY')
    assert d.compare('i','c',2,[1,3]).modes==(1,3)
    assert d.compare('i','c',2,[]).inclusion_rate is None
    assert not d.compare('i','c',4,[2],False).characteristics


def test_equivalent_printings_collapse_and_finishes_do_not_split(setup):
    sources,_=setup; original=profile(setup)
    store=SQLiteCards(sources.paths['cards']);raw=deepcopy(store.get('sm2-1')['card'])
    raw.update(id='sm2-99',localId='99');store.put(raw)
    with sqlite3.connect(sources.paths['workspace']) as db:
        document=json.loads(db.execute('SELECT document FROM workspace').fetchone()[0])
        document['entries'][0]['allocations']=[dict(printing_id='sm2-1',variant='normal',quantity=2),dict(printing_id='sm2-99',variant='holo',quantity=2)]
        db.execute('UPDATE workspace SET document=?',(json.dumps(document),))
    after=profile(setup)
    assert after.comparisons==original.comparisons
    assert len(after.comparisons)==2 and sum(c.quantity for c in after.cards)==60


def test_revision_unavailable_archetype_and_confidence(setup):
    with pytest.raises(Unavailable): d.build_profile(setup[0],revision=8,as_of=TODAY)
    p=d.build_profile(setup[0],revision=7,as_of=TODAY)
    assert p.population.archetype is None and 'comparison_population' in p.unavailable
    p=d.build_profile(setup[0],revision=7,as_of=TODAY,archetype='not-in-cache')
    assert p.population.archetype is None
    with sqlite3.connect(setup[0].paths['competitive']) as db: db.execute('DELETE FROM competitive_decks WHERE rank>3')
    p=profile(setup)
    assert p.population.status=='limited_evidence'
    assert all(c.inclusion_rate is None and not c.characteristics for c in p.comparisons)


@pytest.mark.parametrize('question,expected',[
    ('What is this deck trying to do?',{'DECK_OVERVIEW'}),
    ('How does this deck differ from typical Dragapult decks?',{'ARCHETYPE_COMPARISON'}),
    ('What cards in this deck are unusual for Dragapult?',{'PRESENT_DEVIATIONS','ARCHETYPE_COMPARISON'}),
    ('What common Dragapult cards is this deck not playing?',{'ABSENT_CARDS','ARCHETYPE_COMPARISON'}),
    ('Why might this deck run two Risky Ruins?',{'CARD_ROLE','CARD_QUANTITY','ARCHETYPE_COMPARISON'}),
    ('Why did Rohit Potti choose Budew?',{'CREATOR_INTENT','CARD_ROLE'}),
    ('Why is this deck built around Charizard ex?',{'DECK_OVERVIEW','CARD_ROLE'}),
    ('How does this ability interact with the attack?',{'MECHANICAL_INTERACTION'}),
    ('What tournament evidence supports this?',{'COMPETITIVE_CONTEXT'}),
    ('Hello there',{'UNKNOWN'}),
])
def test_classifier(setup,question,expected):
    p=profile(setup)
    # Only names are substituted to exercise deterministic matching; no Pokemon claims.
    cards=(p.cards[0].model_copy(update={'name':'Risky Ruins'}),p.cards[1].model_copy(update={'name':'Budew'}))
    p=p.model_copy(update={'cards':cards})
    assert set(d.classify(question,p).categories)==expected
    assert p.population.name=='Fixture Archetype'  # Question cannot manufacture Dragapult/Charizard identity.
    assert not d.classify('Charizard ex',p).card_references
    assert not d.classify('Budewish',p).card_references


def test_selection_caps_hash_separation_and_budgets(setup):
    p=profile(setup); results=[]
    for question in ('What is this deck trying to do?','How does this deck differ from typical decks?',
                     'What common cards is this deck not playing?','Why run four Basic 1?','hello'):
        packet=d.select_evidence(p,question);results.append(packet)
        assert packet==d.select_evidence(p,question)
        assert packet.serialized_bytes==len(canonical(packet).encode())<=24*1024
        assert packet.content_hash==digest(packet.model_dump(mode='json',exclude={'content_hash'}))
        refs={r.id for r in packet.references}
        assert all(set(i.references)<=refs for i in packet.evidence)
        assert all(i.classification=='SOURCE_FACT' for i in packet.evidence if i.kind=='mechanics')
        assert all(i.classification=='EMPIRICAL_EVIDENCE' for i in packet.evidence if i.kind=='comparison')
        assert 'creator_intent' in packet.coverage.unavailable
    assert results[0].evidence!=results[1].evidence
    assert results[3].intent.card_references
    huge=p.model_copy(update={'cards':tuple(c.model_copy(update={'printed':(d.FieldValue(field='effect',value='x'*30000),)}) for c in p.cards)})
    packet=d.select_evidence(huge,'What is this deck trying to do?')
    assert any(s.startswith('budget/mechanics') for s in packet.coverage.omitted)
    assert packet.serialized_bytes<=d.EVIDENCE_BYTES


def test_absent_retrieval_and_cap_metadata(setup):
    p=profile(setup); base=p.cards[0]; cards=[]; rows=[]
    for i in range(30):
        key=f'absent-{i:02}'
        cards.append(base.model_copy(update={'identity':key,'name':key,'quantity':0}))
        rows.append(d.compare(key,key,0,[2]*16))
    p=p.model_copy(update={'cards':tuple(cards),'comparisons':tuple(rows)})
    packet=d.select_evidence(p,'What common cards is this deck not playing?')
    comparisons=[i for i in packet.evidence if i.kind=='comparison']
    assert len(comparisons)==10 and comparisons[0].identity=='absent-00'
    assert 'cap/comparison:20' in packet.coverage.omitted
    assert all(json.loads(next(f.value for f in i.fields if f.field=='active_quantity'))==0 for i in comparisons)
    assert packet==d.select_evidence(p,'What common cards is this deck not playing?')


def test_basic_energy_population_uses_existing_type_identity(setup):
    sources,research=setup; store=SQLiteCards(sources.paths['cards'])
    raw=deepcopy(store.get('sm2-3')['card']);raw.update(id='sm2-4',localId='4',name='Basic Water Energy')
    store.put(raw)
    catalog=research.collection.catalog()[0]
    old,new=catalog['sm2-3']['functional_id'],catalog['sm2-4']['functional_id']
    assert old!=new
    with sqlite3.connect(sources.paths['competitive']) as db:
        for event,rank,text in db.execute('SELECT event_id,rank,cards FROM competitive_decks WHERE resolved=1').fetchall():
            values=json.loads(text);values[old]-=1;values[new]=1
            db.execute('UPDATE competitive_decks SET cards=? WHERE event_id=? AND rank=?',(json.dumps(values),event,rank))
    p=profile(setup)
    energy=next(c for c in p.comparisons if c.identity=='deck-basic-energy:Water')
    assert energy.distribution==(d.Bucket(quantity=56,lists=16),)
    assert len(p.comparisons)==2


def test_newly_unresolvable_population_list_is_explicitly_excluded(setup):
    with sqlite3.connect(setup[0].paths['competitive']) as db:
        db.execute('UPDATE competitive_decks SET cards=? WHERE rank=1',(json.dumps({'missing-current-identity':60}),))
    p=profile(setup)
    assert p.population.eligible_lists==15 and p.population.excluded_current_identity==1
    assert p.population.excluded_unmapped==1


def test_evolution_and_ace_spec_are_sourced_not_guessed(setup):
    store=SQLiteCards(setup[0].paths['cards']);raw=store.get('sm2-1')['card']
    raw.update(evolveFrom='Water Energy',stage='Stage1',rarity='ACE SPEC')
    store.put(raw)
    from pokelab.decks import deck_identity
    catalog=setup[1].collection.catalog()[0]
    with sqlite3.connect(setup[0].paths['workspace']) as db:
        document=json.loads(db.execute('SELECT document FROM workspace').fetchone()[0])
        document['entries'][0]['identity']=deck_identity(catalog['sm2-1'])
        db.execute('UPDATE workspace SET document=?',(json.dumps(document),))
    # Synthetic printed relation verifies extraction only, not a valid gameplay evolution.
    p=profile(setup)
    assert all(c.reference.source=='TCGdex' for c in p.cards)
    assert all(c.ace_spec is not None for c in p.cards)
    selected=next(c for c in p.cards if c.quantity and c.category=='Pokemon')
    assert selected.ace_spec is True and selected.evolves_from=='Water Energy'
    assert selected.evolution_parents==('deck-basic-energy:Water',)
    assert 'semantic-functions:draw-search-acceleration-disruption-recovery' in p.unavailable


def test_retrieval_intents_and_rank_ties_with_meaningful_deviations(setup):
    p=profile(setup);base=p.cards[0]
    cards=tuple(base.model_copy(update={'identity':key,'name':name,'quantity':qty}) for key,name,qty in
                [('a','Rare Card',3),('b','Absent Card',0),('c','Core Card',2)])
    rows=(d.compare('a','Rare Card',3,[1]*3+[0]*17),d.compare('b','Absent Card',0,[2]*20),d.compare('c','Core Card',2,[2]*20))
    p=p.model_copy(update={'cards':cards,'comparisons':rows})
    questions=['What is this deck trying to do?','How does this deck differ from typical decks?',
               'What common cards is this deck not playing?','Why run three Rare Card?']
    packets=[d.select_evidence(p,q) for q in questions]
    orders=[tuple((e.kind,e.identity) for e in packet.evidence) for packet in packets]
    assert len(set(orders))==4
    assert next(i.identity for i in packets[2].evidence if i.kind=='comparison')=='b'
    assert next(i.identity for i in packets[3].evidence if i.kind=='comparison')=='a'
    for packet in packets:
        assert all(any(c.kind=='comparison' and c.identity==i.identity for c in packet.evidence)
                   for i in packet.evidence if i.kind=='deviation')
    reversed_profile=p.model_copy(update={'cards':tuple(reversed(cards)),'comparisons':tuple(reversed(rows))})
    # Input card ordering must not affect question matching or retrieval tie breaks.
    assert d.select_evidence(p,questions[1])==d.select_evidence(reversed_profile,questions[1])


def test_frozen_dragapult_profile_packet_replay(monkeypatch):
    from pokelab import agent_providers
    monkeypatch.setattr(agent_providers,'complete',lambda *a,**k:pytest.fail('Provider forbidden'))
    root=Path(__file__).resolve().parents[1]/'docs'/'phase-7c2-dragapult'
    p=d.Profile.model_validate_json((root/'profile.json').read_text(encoding='utf-8'))
    stored=d.Packet.model_validate_json((root/'packet.json').read_text(encoding='utf-8'))
    assert p.revision==157 and p.total==60 and p.population.eligible_lists==159
    assert p.content_hash==digest(p.model_dump(mode='json',exclude={'content_hash'}))
    replay=d.select_evidence(p,stored.question)
    assert replay==stored and canonical(replay)==(root/'packet.json').read_text(encoding='utf-8').strip()
    assert replay.content_hash=='83b2826ab9483495f98f573a7417ceef6e815b728a3e88c43351338253e39fce'
    assert replay.serialized_bytes==12648
    assert len([e for e in replay.evidence if e.kind=='comparison'])==d.CORE_ORIENTATION_CAP
    assert 'rank/core-orientation:18' in replay.coverage.omitted
    assert next(c for c in p.comparisons if c.name=='Risky Ruins').lists_including==138
    for question in ('What is this deck trying to do?','Why run two Risky Ruins?',
                     'What common cards is this deck not playing?','Why did Rohit Potti choose Budew?','Hello'):
        packet=d.select_evidence(p,question)
        assert packet.serialized_bytes<=d.EVIDENCE_BYTES
        assert packet==d.select_evidence(p,question)


def test_question_bounds_and_missing_population_do_not_create_identity(setup):
    p=d.build_profile(setup[0],revision=7,as_of=TODAY)
    with pytest.raises(ValueError): d.classify('x'*2001,p)
    packet=d.select_evidence(p,'Why is this deck built around Charizard ex?')
    assert 'comparison_population' in packet.coverage.unavailable
    assert not packet.intent.card_references and p.population.archetype is None
    with pytest.raises(ValueError): d.select_evidence(p.model_copy(update={'configuration_hash':'old-config'}),'Overview')
