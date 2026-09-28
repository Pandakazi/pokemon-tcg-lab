"""Actual Standard corpus examples plus explicitly synthetic safety edge cases."""
from dataclasses import asdict
import gzip
import json
from pathlib import Path
import socket
import sqlite3

import pytest

from pokelab import mechanics_discovery as m
from pokelab.engine import functional_signature

FIXTURE=json.loads((Path(__file__).parent/'fixtures/mechanics_standard_examples.json').read_text(encoding='utf-8'))
RECORDS={r['card']['id']:r for r in FIXTURE['records']}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args,**kw): raise AssertionError('No network in discovery')
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    monkeypatch.setattr(socket.socket,'connect_ex',forbidden)


def effects(printing):
    r=RECORDS[printing]
    return [m.represent(r['card'],kind,i,item,r['checked_at']) for kind,i,item in m.components(r['card'])]


@pytest.mark.parametrize('case',FIXTURE['cases'],ids=lambda c:c['label'])
def test_real_standard_examples(case):
    card=RECORDS[case['printing']]['card']
    assert card['legal']['standard'] is True
    e=next(e for e in effects(card['id']) if e.component==case['component'] and e.component_index==case['index'])
    assert case['label'] in e.mechanics
    assert e.source_card_hash==m.digest(card)
    assert e.normalized_text==m.normalize(e.raw_text)
    for atom in e.atoms:
        if atom.span:
            assert e.normalized_text[atom.span.start:atom.span.end]==atom.span.text
    assert e==next(x for x in effects(card['id']) if x.id==e.id)


def synthetic(text,**structured):
    card=dict(id='synthetic-1',name='Unpublished fixture',category='Trainer',legal={'standard':True},effect=text)
    return m.represent(card,'trainer_effect',0,dict(effect=text,**structured),'fixture')


def test_compound_actions_order_and_distinct_controller():
    e=synthetic("Discard an Energy from your opponent's Active Pokémon. Then draw 2 cards.")
    assert [a.action for a in e.atoms]==['discard','draw']
    assert e.atoms[0].affected_player=="your opponent's"
    assert e.atoms[1].affected_player is None
    assert e.atoms[1].quantity=='2' and e.atoms[1].previous_atom==0
    assert e.atoms[1].relationship=='text_order_not_execution'
    assert {'energy_denial','draw'}<=set(e.mechanics)
    assert e.representation=='partial' and 'compound_scope_not_executed' in e.ambiguities


def test_mill_directions_not_collapsed_or_confused_with_hand_energy():
    assert 'opponent_mill' in synthetic("Discard the top 2 cards of your opponent's deck.").mechanics
    assert 'opponent_mill' not in synthetic('Discard the top 2 cards of your deck.').mechanics
    assert 'self_mill' in synthetic('Discard the top 2 cards of your deck.').mechanics
    for text in ["Discard 2 cards from your opponent's hand.","Discard an Energy from your opponent's Active Pokémon."]:
        assert not {'self_mill','opponent_mill'} & set(synthetic(text).mechanics)


def test_novel_effect_survives_without_taxonomy_or_atoms():
    text='Quantum braid the lunar sigils of both players.'
    e=synthetic(text)
    assert e.raw_text==text and e.normalized_text==text.casefold()
    assert not e.atoms and not e.mechanics and e.representation=='unclassified'
    assert e.unmatched_spans[0].text==e.normalized_text
    assert 'other' not in e.mechanics


def test_unknown_tail_and_conditional_scope_preserved():
    text='If tails, draw 2 cards. Quantum braid the lunar sigils.'
    e=synthetic(text)
    assert 'draw' in e.mechanics and e.representation=='partial'
    assert any('quantum braid' in s.text for s in e.unmatched_spans)
    assert 'condition_or_timing_scope_unresolved' in e.ambiguities
    assert e.atoms[0].context=='if tails,'


def test_corpus_ability_usage_not_global_lock():
    e=next(e for e in effects('me04-038') if e.component=='ability')
    assert 'self_ability_use_restriction' in e.mechanics and 'ability_lock' not in e.mechanics
    assert 'ability_lock' in effects('me02.5-210')[0].mechanics


def test_missing_attack_cost_never_becomes_zero():
    e=next(e for e in effects('me02.5-221') if e.component=='attack')
    assert 'attack_cost_not_supplied' in e.source_issues
    assert 'cost' not in json.loads(e.structured_json)
    assert 'item_lock' in e.mechanics


def test_unobserved_lost_zone_can_be_represented_without_claiming_corpus_presence():
    e=synthetic('Put a card from your hand into the Lost Zone.')
    assert 'lost_zone_movement' in e.mechanics
    assert e.atoms[0].source_zone=='hand' and e.atoms[0].destination_zone=='lost zone'


def test_raw_cost_and_damage_expression_not_interpreted():
    e=synthetic('This attack does 30 more damage for each card.',cost=['Colorless'],damage='30+')
    assert json.loads(e.structured_json)['cost']==['Colorless']
    assert e.representation=='partial'
    assert any(a.quantity=='30+' for a in e.atoms)


def test_identity_uses_existing_signature_not_name_only():
    import hashlib
    e=effects('me01-173')[0]
    assert e.functional_identity==hashlib.sha256(functional_signature(RECORDS[e.printing]['card']).encode()).hexdigest()[:32]
    assert synthetic('Draw 2 cards.').functional_identity!=synthetic('Draw 3 cards.').functional_identity


def create_db(path):
    with sqlite3.connect(path) as db:
        db.executescript('PRAGMA user_version=1; CREATE TABLE cards(id,category,game,standard,regulation,raw,checked_at,fetched_at); CREATE TABLE metadata(key,value);')
        for id,game,standard,language in [('english','tcg',1,None),('rotated','tcg',0,None),('pocket','pocket',1,None),('foreign','tcg',1,'fr')]:
            card=dict(id=id,name=id,category='Trainer',legal={'standard':bool(standard)},effect='Draw 2 cards.')
            if language: card['language']=language
            db.execute('INSERT INTO cards VALUES (?,?,?,?,?,?,?,?)',(id,'Trainer',game,standard,'H',json.dumps(card),'2026-09-23','2026-09-23'))


def test_readonly_selection_provenance_and_determinism(tmp_path):
    path=tmp_path/'cards.sqlite3';create_db(path);before=path.read_bytes()
    one=m.analyze(path);two=m.analyze(path)
    assert one==two and path.read_bytes()==before
    s,cards,es,_=one
    assert s['selected_printings']==1 and cards[0]['printing']=='english'
    assert s['total_cache_rows']==4 and s['coverage']['usable']==1
    assert s['coverage']['simple']==1 and s['coverage']['partial']==0
    assert es[0].normalized_text=='draw 2 cards.'
    assert s['exclusions']['explicit_non_english']==1


def test_missing_database_is_not_created(tmp_path):
    path=tmp_path/'missing.sqlite3'
    with pytest.raises(sqlite3.OperationalError): m.analyze(path)
    assert not path.exists()


def test_corrupt_source_record_reported_not_silently_included(tmp_path):
    path=tmp_path/'cards.sqlite3';create_db(path)
    with sqlite3.connect(path) as db: db.execute("UPDATE cards SET raw='bad json' WHERE id='english'")
    s,_,_,_=m.analyze(path)
    assert s['source_failures']==[dict(printing='english',reason='invalid_source_record')]


def test_malformed_component_preserved_and_flagged():
    card=dict(id='synthetic-1',name='Malformed',category='Pokemon',attacks='not a list')
    kind,index,data=next(m.components(card))
    e=m.represent(card,kind,index,data,'fixture')
    assert 'component_wrong_type' in e.source_issues
    assert json.loads(e.structured_json)['original']=='not a list'


def test_other_component_ids_keep_effect_and_rules_separate():
    card=dict(id='synthetic-1',name='Other',category='Pokemon',effect='Novel sky rule.',rules=['Novel moon rule.'])
    es=[m.represent(card,kind,i,data,'fixture') for kind,i,data in m.components(card)]
    assert len({e.id for e in es})==2 and all(e.normalized_text for e in es)


def test_artifact_covers_entire_measured_corpus_and_unknowns():
    folder=Path(__file__).parents[1]/'docs/phase-7c3-mechanics'
    s=json.loads((folder/'summary.json').read_text(encoding='utf-8'))
    es=[json.loads(line) for line in gzip.decompress((folder/'effects.jsonl.gz').read_bytes()).decode().splitlines()]
    cards=json.loads(gzip.decompress((folder/'cards.json.gz').read_bytes()).decode())
    assert len(cards)==s['selected_printings']==3345
    assert len(es)==s['coverage']['components'] and len({e['id'] for e in es})==len(es)
    assert m.digest(cards)==s['corpus_hash'] and m.digest(es)==s['effects_hash']
    assert m.digest(m.load_taxonomy())==s['taxonomy_hash']
    assert sum(bool(e['normalized_text']) for e in es)==s['coverage']['text_bearing']
    assert sum(e['representation']=='unclassified' for e in es)==s['coverage']['unclassified']
    assert s['text_audit']['lost_zone']['effect_count']==0
    assert all(e['normalized_text'] and e['unmatched_spans'] for e in es if e['representation']=='unclassified')
