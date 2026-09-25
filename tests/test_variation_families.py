"""Real synchronized TCGdex evidence plus deliberate collision mutations."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pokelab.api import create_app
from pokelab.collection import Collection
from pokelab.decks import deck_identity
from pokelab.variation_families import family_signature, variation_members
from tcg_lab.card_db import SQLiteCards
from test_deck_builder import mutate

FIXTURE=json.loads((Path(__file__).parent/'fixtures/variation-families.json').read_text(encoding='utf-8'))
SOURCE={r['card']['id']:r for r in FIXTURE['records']}
MEGA={'me02-013','me02-109','me02-125','me02-130','mep-023','mep-029'}
BOSS={id for id,r in SOURCE.items() if r['card']['name']=="Boss's Orders"}


@pytest.fixture
def family_setup(tmp_path):
    cards=SQLiteCards(tmp_path/'cards.sqlite3')
    for raw in FIXTURE['sets']: cards.put_set(raw)
    for record in FIXTURE['records']: cards.put(record['card'])
    state=tmp_path/'state.sqlite3'; collection=Collection(cards,state)
    snapshot=collection.snapshot()
    client=TestClient(create_app(cards.path,state))
    return cards,state,snapshot,client


def page(client,id,scope='family',**kwargs):
    response=client.get(f'/api/v1/cards/{id}/variations',params=dict(scope=scope,page_size=50,**kwargs))
    assert response.status_code==200,response.text
    return response.json()


def test_real_mega_source_discrepancy_and_complete_bidirectional_family(family_setup):
    _,_,snapshot,c=family_setup
    regular=SOURCE['me02-013']['card']; gold=SOURCE['me02-130']['card']
    assert 'suffix' not in regular and gold['suffix']=='ex'
    assert regular['weaknesses'][0]['value']=='×2' and gold['weaknesses'][0]['value']=='x2'
    assert regular['attacks']==gold['attacks']
    assert regular['variants_detailed'][0]['variantId']!=gold['variants_detailed'][0]['variantId']
    assert gold['variants_detailed'][0]['foil']=='gold'
    # The certified keys stay distinct. Discovery does not fix them by rewriting.
    assert deck_identity(snapshot.records['me02-013'])!=deck_identity(snapshot.records['me02-130'])
    for id in MEGA:
        assert set(variation_members(snapshot,id))==MEGA
        assert {v['id'] for v in page(c,id)['cards']}==MEGA
    assert {v['id'] for v in page(c,'me02-013','functional')['cards']}=={'me02-013','me02-109','me02-125'}
    assert {v['id'] for v in page(c,'me02-130','deck')['cards']}=={'me02-130'}


def test_real_boss_history_full_wording_pair_and_truthful_legality(family_setup):
    _,_,snapshot,c=family_setup
    assert len(BOSS)==9
    for id in BOSS: assert set(variation_members(snapshot,id))==BOSS
    result=page(c,'me01-114')['cards']
    assert {v['id'] for v in result}==BOSS
    assert next(v for v in result if v['id']=='swsh9-132')['legal']['standard'] is False
    assert next(v for v in result if v['id']=='me01-114')['legal']['standard'] is True


def test_actual_same_name_different_gameplay_and_game_stay_separate(family_setup):
    _,_,snapshot,_=family_setup
    for id in ('base1-4','swsh4-25','swsh10.5-010','A1-035'):
        assert variation_members(snapshot,id)==[id]
    pocket=deepcopy(SOURCE['me02-013']);pocket['game']='pocket'
    assert family_signature(pocket)!=family_signature(SOURCE['me02-013'])


@pytest.mark.parametrize('field,value',[
    ('hp',350),('stage','Stage1'),('evolveFrom','Charmander'),('suffix','EX'),
    ('types',['Dragon']),('retreat',3),('rules',['Different rule']),
    ('abilities',[{'type':'Ability','name':'New ability','effect':'Draw a card.'}]),
    ('item',{'effect':'A gameplay item'}),
])
def test_same_set_same_name_different_structured_identity_never_merges(field,value):
    changed=deepcopy(SOURCE['me02-013']);changed['card'][field]=value
    assert family_signature(changed)!=family_signature(SOURCE['me02-013'])


@pytest.mark.parametrize('field,value',[
    ('name','Another attack'),('cost',['Fire']),('damage','100×'),
    ('effect','Discard 1 Energy. This attack does 90 damage.'),
])
def test_attack_differences_are_not_erased(field,value):
    changed=deepcopy(SOURCE['me02-013']);changed['card']['attacks'][0][field]=value
    assert family_signature(changed)!=family_signature(SOURCE['me02-013'])


@pytest.mark.parametrize('change', ['effect','subtype','name','rules','ace'])
def test_boss_alias_is_exact_and_category_gated(change):
    changed=deepcopy(SOURCE['swsh9-132']);card=changed['card']
    if change=='effect':card['effect'] += ' Draw a card.'
    elif change=='subtype':card['trainerType']='Item'
    elif change=='name':card['name']='Different Orders'
    elif change=='rules':card['rules']=['A different restriction']
    else:card['rarity']='ACE SPEC'
    assert family_signature(changed)!=family_signature(SOURCE['me01-114'])


def test_incomplete_records_do_not_bridge_and_cosmetic_evidence_does(family_setup):
    _,_,snapshot,_=family_setup
    changed=deepcopy(SOURCE['me02-013']);changed['card']['id']='missing-1'
    del changed['card']['stage']
    assert family_signature(changed)[0]=='unresolved'
    changed=deepcopy(SOURCE['me02-013']);changed['card']['id']='formatting-1'
    changed['card']['attacks'][0]['effect']='  '+changed['card']['attacks'][0]['effect'].replace(' Energy','\nEnergy')+'  '
    changed['card']['rarity']='Different art rarity';changed['card']['legal']={'standard':False}
    assert family_signature(changed)==family_signature(SOURCE['me02-013'])


def test_basic_type_and_special_energy_keep_existing_semantics(family_setup):
    _,_,snapshot,c=family_setup
    assert set(variation_members(snapshot,'sv03.5-207'))=={'base1-101','sv03.5-207'}
    assert variation_members(snapshot,'base1-98')==['base1-98']
    assert set(variation_members(snapshot,'swsh9-151'))=={'swsh9-151','swsh10-216'}
    assert deck_identity(snapshot.records['base1-101'])==deck_identity(snapshot.records['sv03.5-207'])
    changed=deepcopy(SOURCE['swsh9-151']);changed['card']['effect']+=' Draw a card.'
    assert family_signature(changed)!=family_signature(SOURCE['swsh9-151'])


def test_discovery_preserves_ownership_allocations_defaults_and_library(family_setup):
    cards,state,snapshot,c=family_setup
    for variant,quantity in [('normal',2),('holo',3),('reverse',4)]:
        response=c.put('/api/v1/collection/me02.5-183',json=dict(variant=variant,quantity=quantity))
        assert response.status_code==200
    mutate(c,'quantity',printing_id='me02-013',variant='holo',delta=1,exact=True)
    saved=mutate(c,'save')
    deck_path=state.with_name('deck-workspace.sqlite3')
    before=[p.read_bytes() for p in (cards.path,state,deck_path)]
    original_ids={id:deck_identity(r) for id,r in snapshot.records.items()}
    for id in ('me02-013','me01-114','sv03.5-207'):
        page(c,id)
    assert [p.read_bytes() for p in (cards.path,state,deck_path)]==before
    assert {id:deck_identity(r) for id,r in snapshot.records.items()}==original_ids
    assert c.get('/api/v1/deck-workspace').json()==saved
    finishes={v['ownership']['variant']:v['ownership']['quantity'] for v in page(c,'me01-114')['cards'] if v['id']=='me02.5-183'}
    assert finishes=={'normal':2,'holo':3,'reverse':4}
    # Newly discoverable gold still uses its certified ID, not the anchor's ID.
    selected=mutate(c,'quantity',printing_id='me02-130',variant='holo',delta=1,exact=True)
    assert selected['deck']['entries'][0]==saved['deck']['entries'][0]
    key=original_ids['me02-130']
    assert selected['defaults'][key]['printing_id']=='me02-130'
    implicit=mutate(c,'quantity',printing_id='me02-130',delta=1)
    assert next(e for e in implicit['deck']['entries'] if e['identity']==key)['quantity']==2
    assert state.read_bytes()==before[1]
    reopened=mutate(c,'open',deck_id=saved['deck']['id'],discard=True)
    assert reopened['deck']==saved['deck']


def test_pagination_is_exact_finish_stable(family_setup):
    c=family_setup[3]
    first=c.get('/api/v1/cards/me01-114/variations?scope=family&page_size=3').json()
    second=c.get('/api/v1/cards/me01-114/variations?scope=family&page_size=3&page=2').json()
    pairs=lambda page:{(v['id'],v['ownership']['variant']) for v in page['cards']}
    assert len(pairs(first))==3 and len(pairs(second))==3
    assert not pairs(first)&pairs(second)
    assert first['next_page']==2 and first['total']==len(page(c,'me01-114')['cards'])
