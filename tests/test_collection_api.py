from contextlib import closing
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from pokelab.api import create_app
from pokelab.engine import PokeLabEngine
from tcg_lab.card_db import SQLiteCards
from test_card_data import card, set_record


@pytest.fixture
def setup(tmp_path):
    db = SQLiteCards(tmp_path/'cards.sqlite3'); db.put_set(set_record())
    for id in ('sm2-1','sm2-2','sm2-3'):
        r=card(id,'Same playable card'); r.update(legal={'standard':True},variants={'normal':True,'reverse':True})
        if id=='sm2-3': r['attacks'][0]['damage']=999
        db.put(r)
    state=tmp_path/'state.sqlite3'
    return db,state,TestClient(create_app(db.path,state))


def change(client,id='sm2-1',variant='normal',**operation):
    return client.put('/api/v1/collection/'+id,json={'variant':variant,**operation})


def test_quantities_rollup_filters_persistence_and_read_only_cache(setup):
    db,path,c=setup; before=db.path.read_bytes()
    assert change(c,quantity=2).json()['functional_total']==2
    assert change(c,id='sm2-2',variant='reverse',quantity=3).json()['functional_total']==5
    library=c.get('/api/v1/cards?ownership=owned&stages=Basic&ability=Yes&pokemon_types=Psychic&pokemon_types=Dragon').json()
    assert library['total']==1
    owned=library['cards'][0]['ownership']
    assert owned['functional_total']==5 and owned['quantity']==0  # Representative normal, owned reverse.
    assert c.get('/api/v1/cards?ownership=unowned').json()['total']==1
    assert c.get('/api/v1/collection').json()['total']==2
    restarted=TestClient(create_app(db.path,path))
    assert restarted.get('/api/v1/cards/sm2-2/ownership?variant=reverse').json()['quantity']==3
    assert change(restarted,quantity=1).json()['quantity']==1
    assert change(restarted,delta=-1).json()['quantity']==0
    assert change(restarted,delta=-1).json()['quantity']==0
    assert c.get('/api/v1/collection').json()['total']==1
    assert db.path.read_bytes()==before


@pytest.mark.parametrize('operation',[{'quantity':-1},{'quantity':True},{'quantity':1.2},{'quantity':10000},{'delta':0},{'delta':2},{'quantity':2,'delta':1},{}])
def test_invalid_quantity(setup,operation):
    assert change(setup[2],**operation).status_code==422


def test_variant_validation_and_missing_printings(setup):
    c=setup[2]
    assert change(c,variant='invented',quantity=1).status_code==422
    assert change(c,id='sm2-999',quantity=1).status_code==404
    assert c.get('/api/v1/cards/sm2-1?variant=invented').status_code==422
    assert c.put('/api/v1/library/sm2-1/preference',json={'printing_id':'sm2-3','variant':'normal'}).status_code==422


def test_variations_preferences_inspection_and_invalid_preference_fallback(setup):
    db,path,c=setup
    variations=c.get('/api/v1/cards/sm2-1/variations?page_size=2').json()
    assert variations['total']==6 and variations['next_page']==2
    all_variations=c.get('/api/v1/cards/sm2-1/variations').json()['cards']
    assert {r['id'] for r in all_variations}=={'sm2-1','sm2-2'}
    assert {r['ownership']['variant'] for r in all_variations}=={'unspecified','normal','reverse'}
    assert c.put('/api/v1/library/sm2-2/preference',json={'printing_id':'sm2-1','variant':'reverse'}).status_code==200
    restart=TestClient(create_app(db.path,path))
    library=restart.get('/api/v1/cards').json()['cards']
    selected=next(r for r in library if r['id']=='sm2-1')
    assert selected['ownership']['variant']=='reverse'
    assert change(restart,id=selected['id'],variant='reverse',delta=1).json()['quantity']==1
    assert restart.get('/api/v1/cards/sm2-2?variant=normal').json()['card']['ownership']['quantity']==0
    assert restart.get('/api/v1/library/sm2-2/preference').json()=={'printing_id':'sm2-1','variant':'reverse'}
    with closing(sqlite3.connect(path)) as state, state:
        state.execute("UPDATE library_preferences SET printing_id='missing-1'")
    assert [r['id'] for r in restart.get('/api/v1/cards').json()['cards']]==['sm2-2','sm2-3']


def test_safe_one_time_legacy_import(setup):
    db,path,_=setup
    legacy=PokeLabEngine(db.path); legacy.set_quantity('sm2-1','reverse',4)
    before=db.path.read_bytes()
    c=TestClient(create_app(db.path,path))
    assert c.get('/api/v1/cards/sm2-1/ownership?variant=reverse').json()['quantity']==4
    assert change(c,variant='reverse',quantity=0).status_code==200
    c=TestClient(create_app(db.path,path))
    assert c.get('/api/v1/cards/sm2-1/ownership?variant=reverse').json()['quantity']==0
    assert legacy.collection_quantity('sm2-1','reverse')==4
    assert db.path.read_bytes()==before


def test_atomic_increments(setup):
    c=setup[2]
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses=list(pool.map(lambda _:change(c,delta=1),range(12)))
    assert all(r.status_code==200 for r in responses)
    assert c.get('/api/v1/cards/sm2-1/ownership?variant=normal').json()['quantity']==12


def test_basic_energy_library_rollup_is_distinct_from_canonical_variations(setup):
    db,path,c=setup
    for id,name in [('sm2-10','Water Energy'),('sm2-11','Basic Water Energy')]:
        r=card(id,name); r.update(category='Energy',energyType='Normal',types=['Water'],legal={'standard':True}); db.put(r)
    assert change(c,id='sm2-10',variant='unspecified',quantity=2).status_code==200
    basic=c.get('/api/v1/cards?category=Energy&ownership=owned').json()
    assert basic['total']==1
    assert basic['cards'][0]['ownership']['library_total']==2
    assert basic['cards'][0]['ownership']['functional_total']==0
    assert c.get('/api/v1/cards/sm2-11/variations').json()['total']==1
    assert c.get('/api/v1/cards/sm2-11/variations?scope=library').json()['total']==2
    assert c.put('/api/v1/library/sm2-11/preference',json={'printing_id':'sm2-10','variant':'unspecified'}).status_code==200


@pytest.mark.parametrize('printing,variant',[('sm2-3','normal'),('sm2-1','invented')])
def test_invalid_saved_group_or_finish_falls_back(setup,printing,variant):
    db,path,c=setup
    c.put('/api/v1/library/sm2-2/preference',json={'printing_id':'sm2-1','variant':'normal'})
    with closing(sqlite3.connect(path)) as state, state:
        state.execute('UPDATE library_preferences SET printing_id=?,variant=?',(printing,variant))
    assert [r['id'] for r in c.get('/api/v1/cards').json()['cards']]==['sm2-2','sm2-3']


def test_unknown_state_schema_and_cache_path_collision_are_safe(setup):
    db,path,_=setup
    with closing(sqlite3.connect(path)) as state, state:
        state.execute('PRAGMA user_version=99')
        state.execute('CREATE TABLE personal_note (value TEXT)')
        state.execute("INSERT INTO personal_note VALUES ('keep')")
    before=path.read_bytes()
    c=TestClient(create_app(db.path,path))
    response=c.get('/api/v1/collection')
    assert response.status_code==503 and response.json()['detail']['code']=='user_state_unavailable'
    assert path.read_bytes()==before
    with pytest.raises(ValueError,match='separate'):
        create_app(db.path,db.path)
