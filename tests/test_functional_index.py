"""Deterministic gameplay-index, format-policy and exact-state compatibility proof."""
from copy import deepcopy
from contextlib import closing
import json
import socket
import pytest
from tcg_lab.card_db import SQLiteCards
from pokelab.collection import Collection
from pokelab.api import ReadOnlyCards
from pokelab.decks import DeckProvider,deck_identity,Decks
from pokelab.agent_deck_proposals import Resolver,Candidate
from pokelab.functional_index import gameplay_signature,VERSION
from pokelab.engine import functional_signature

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(socket.socket,'connect',lambda *a,**kw:pytest.fail('No network'))


def card(id='qa-010',name='Example',category='Pokemon',**kw):
    raw=dict(id=id,name=name,category=category,set={'id':'qa','cardCount':{'official':100}},localId=id.split('-')[-1],rarity='Common',regulationMark='H',legal={'standard':False},variants={'normal':True,'reverse':True})
    if category=='Pokemon':raw.update(hp=100,stage='Basic',types=['Psychic'],attacks=[dict(name='Focus',cost=['Psychic'],damage=20,effect='Draw 1 card.')])
    else:raw.update(trainerType='Item',effect='Draw 1 card.')
    raw.update(kw);return raw


def setup(tmp_path,raws):
    cards=SQLiteCards(tmp_path/'cards.db')
    cards.put_set(dict(id='qa',serie={'id':'sv'}))
    for raw in raws:cards.put(raw)
    collection=Collection(ReadOnlyCards(cards.path),tmp_path/'collection.db');collection.initialize()
    return cards,collection,Resolver(collection,cards.path)


def test_trainer_formatting_index_and_canonical_base(tmp_path,monkeypatch):
    base=card(name='Ultra Ball',category='Trainer',effect='Discard 2 cards.\n\nSearch your deck.')
    premium=dict(base,id='qa-150',localId='150',rarity='Special illustration rare',effect='Discard 2 cards.\n Search your deck.')
    old=dict(base,id='qa-001',localId='1',regulationMark='G',legal={'standard':True})
    cards,collection,resolver=setup(tmp_path,[premium,old,base])
    before=collection.path.read_bytes()
    with closing(cards.connect()) as db:
        assert db.execute('SELECT count(*) FROM gameplay_functions').fetchone()[0]==1
        item=db.execute('SELECT * FROM gameplay_functions').fetchone()
        assert item['standard']==1 and item['canonical_printing']=='qa-010'
    # Runtime must not recompute normalized signatures or write the cache.
    import pokelab.functional_index as index
    monkeypatch.setattr(index,'gameplay_signature',lambda *a:pytest.fail('Runtime regrouping'))
    import pokelab.collection as collection_module
    monkeypatch.setattr(collection_module,'functional_signature',lambda *a:pytest.fail('Runtime legacy regrouping'))
    collection=Collection(ReadOnlyCards(cards.path),collection.path)
    resolver=Resolver(collection,cards.path)
    for printing in (None,'qa-001','missing','qa-150'):
        record,state,_=resolver.resolve(Candidate(name='Ultra Ball',printing_id=printing),generated=True)
        assert state=='resolved' and record['card']['id']=='qa-010' and deck_identity(record)==item['id']
    legacy=deck_identity(collection.catalog()[0]['qa-001'])
    assert DeckProvider(collection).get(legacy)['card']['legal']['standard'] is True
    assert collection.path.read_bytes()==before
    assert functional_signature(base)!=functional_signature(premium) # old hashes preserved


def test_pokemon_art_and_genuine_ambiguity(tmp_path):
    base=card();alt=dict(base,id='qa-200',localId='200',rarity='Special illustration rare')
    changed=deepcopy(base);changed.update(id='qa-011',localId='11',hp=120);changed['attacks'][0]['name']='Different Attack'
    cards,collection,r=setup(tmp_path,[alt,base,changed])
    assert gameplay_signature(base)==gameplay_signature(alt)!=gameplay_signature(changed)
    with closing(cards.connect()) as db:assert db.execute('SELECT count(*) FROM gameplay_functions').fetchone()[0]==2
    assert r.resolve(Candidate(name='Example'),generated=True)[1]=='ambiguous'
    assert r.resolve(Candidate(name='Example',role='use Different Attack'),generated=True)[0]['card']['id']=='qa-011'
    assert r.resolve(Candidate(name='Example',printing_id='qa-200'),generated=True)[0]['card']['id']=='qa-010'


@pytest.mark.parametrize('field,value',[('hp',110),('stage','Stage1'),('evolveFrom','Earlier'),('types',['Fire']),('retreat',2),('weaknesses',[{'type':'Darkness','value':'x2'}]),('abilities',[{'name':'Focus','effect':'Draw 2 cards.'}]),('rules',['Take an extra Prize.'])])
def test_gameplay_differences_stay_separate(field,value):
    original=card();changed=dict(original,**{field:value})
    assert gameplay_signature(original)!=gameplay_signature(changed)


def test_config_overrides_stale_flags_and_does_not_invent_coverage(tmp_path):
    rotated=card(name='Rotated',regulationMark='G',legal={'standard':True})
    missing=card(id='qa-020',name='No evidence');missing.pop('regulationMark');missing['legal']={}
    current=card(id='qa-030',name='Current',regulationMark='I',legal={'standard':False})
    _,_,r=setup(tmp_path,[rotated,missing,current])
    assert r.resolve(Candidate(name='Rotated'),generated=True)[1]=='illegal'
    assert r.resolve(Candidate(name='No evidence'),generated=True)[1]=='unknown_legality'
    assert r.resolve(Candidate(name='Current',printing_id='qa-010'),generated=True)[1]=='resolved'


def test_basic_energy_type_and_special_effects(tmp_path):
    water=card(name='Water Energy',category='Energy',energyType='Normal',types=['Water']);water.pop('effect');water.pop('trainerType')
    art=dict(water,id='qa-011',name='Basic Water Energy',localId='11',rarity='Hyper rare')
    special=dict(water,id='qa-012',name='Special Energy',energyType='Special',effect='Provides Water Energy.')
    other=dict(special,id='qa-013',effect='Provides Fire Energy.')
    _,_,r=setup(tmp_path,[water,art,special,other])
    assert gameplay_signature(water)==gameplay_signature(art)=='deck-basic-energy:Water'
    assert gameplay_signature(special)!=gameplay_signature(other)
    assert deck_identity(r.resolve(Candidate(name='Water Energy'),generated=True)[0])=='deck-basic-energy:Water'


def test_ingestion_updates_group_legality_and_canonical(tmp_path):
    old=card(regulationMark='G');cards,collection,_=setup(tmp_path,[old])
    newer=dict(old,id='qa-020',localId='20',regulationMark='H');cards.put(newer)
    r=Resolver(collection,cards.path)
    assert r.resolve(Candidate(name='Example'),generated=True)[0]['card']['id']=='qa-020'
    newer['regulationMark']='G';cards.put(newer)
    assert Resolver(collection,cards.path).resolve(Candidate(name='Example'),generated=True)[1]=='illegal'


def test_old_exact_allocation_uses_index_without_rewriting_identity(tmp_path):
    base=card(name='Example',regulationMark='H')
    old=deepcopy(base);old.update(id='qa-001',localId='1',regulationMark='G');old['attacks'][0]['effect']='Draw  1\ncard.'
    cards,collection,_=setup(tmp_path,[old,base])
    record=collection.catalog()[0]['qa-001'];legacy=deck_identity(record)
    document=dict(name='Historical',has_saved=False,entries=[dict(identity=legacy,quantity=1,allocations=[dict(printing_id='qa-001',variant='reverse',quantity=1)])])
    before=deepcopy(document);cache=cards.path.read_bytes();ownership=collection.path.read_bytes()
    result=Decks(collection,tmp_path/'workspace.db').validation(document)
    assert result['state']=='IN PROGRESS' and not result['unknown']
    assert document==before and cards.path.read_bytes()==cache and collection.path.read_bytes()==ownership


def test_canonical_avoids_promo_before_low_collector_number(tmp_path):
    base=card(id='qa-020');promo=dict(base,id='svp-001',localId='1',set={'id':'svp','name':'Promos'},rarity='Promo')
    _,_,r=setup(tmp_path,[promo,base])
    assert r.resolve(Candidate(name='Example'),generated=True)[0]['card']['id']=='qa-020'


def test_offline_rebuild_preserves_legacy_hashes_and_raw_records(tmp_path):
    from pokelab.functional_index import rebuild
    raws=[card(),card(id='qa-200',rarity='Special illustration rare')]
    cards,collection,_=setup(tmp_path,raws)
    before={p:(r['functional_id'],r['library_id']) for p,r in collection.catalog()[0].items()}
    state=collection.path.read_bytes()
    with closing(cards.connect()) as db,db:
        original=list(db.execute('SELECT id,raw FROM cards ORDER BY id'))
        rebuild(db)
        assert [tuple(r) for r in original]==[tuple(r) for r in db.execute('SELECT id,raw FROM cards ORDER BY id')]
    after=Collection(ReadOnlyCards(cards.path),collection.path).catalog()[0]
    assert before=={p:(r['functional_id'],r['library_id']) for p,r in after.items()}
    assert collection.path.read_bytes()==state
