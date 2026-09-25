from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
import sqlite3

import pytest
from fastapi.testclient import TestClient
from pokelab.api import create_app
from pokelab.decks import Decks
from tcg_lab.card_db import SQLiteCards
from test_card_data import card, set_record


@pytest.fixture
def setup(tmp_path):
    cards = SQLiteCards(tmp_path/'cards.sqlite3'); cards.put_set(set_record())
    first = card('sm2-1','Test Basic'); first.update(legal={'standard':True},variants={'normal':True,'reverse':True})
    second = deepcopy(first); second.update(id='sm2-2',localId='2',legal={'standard':False})
    distinct = deepcopy(first); distinct.update(id='sm2-3',localId='3'); distinct['attacks'][0]['damage']=90
    for raw in (first,second,distinct): cards.put(raw)
    for id,name,kind,effect in [('sm2-4','Water Energy','Normal','old'),('sm2-5','Basic Water Energy','Normal','new'),
                                ('sm2-6','Fire Energy','Normal',''),('sm2-7','Special Water','Special','special'),
                                ('sm2-8','Ambiguous Energy','Normal','ambiguous')]:
        cards.put(dict(id=id,name=name,localId=id.split('-')[1],set={'id':'sm2'},category='Energy',energyType=kind,
                       effect=effect,rarity='Common',legal={'standard':True},variants={'normal':True}))
    ace=card('sm2-9','Restricted'); ace.update(category='Trainer',rarity='ACE SPEC',legal={'standard':True}); cards.put(ace)
    illegal=card('sm2-10','Illegal'); cards.put(illegal)
    unknown=card('sm2-11','Unknown'); unknown['legal']={}; cards.put(unknown)
    state=tmp_path/'state.sqlite3'
    client=TestClient(create_app(cards.path,state))
    client.get('/api/v1/cards')  # Initialize certified collection before byte checks.
    return cards,state,client


def mutate(c,action,**kwargs):
    revision=c.get('/api/v1/deck-workspace').json()['revision']
    r=c.post('/api/v1/deck-workspace',json=dict(schema_version=2,action=action,revision=revision,**kwargs))
    assert r.status_code==200,r.text
    return r.json()


def add(c,id,n=1):
    for _ in range(n): result=mutate(c,'quantity',printing_id=id,delta=1)
    return result


def test_states_save_reopen_restart_and_frozen_collection(setup):
    cards,state,c=setup; before=cards.path.read_bytes(); owned=state.read_bytes()
    assert c.get('/api/v1/deck-workspace').json()['validation']['state']=='EMPTY'
    draft=add(c,'sm2-1'); assert draft['validation']['state']=='IN PROGRESS'
    mutate(c,'rename',name='My draft')
    restart=TestClient(create_app(cards.path,state))
    assert restart.get('/api/v1/deck-workspace').json()['deck']['name']=='My draft'
    saved=mutate(restart,'save'); assert saved['validation']['state']=='INVALID'
    assert '59 cards remaining' in saved['validation']['reasons']
    saved_id=saved['deck']['id']
    mutate(c,'new'); reopened=mutate(c,'open',deck_id=saved_id)
    assert reopened['deck']['has_saved'] and reopened['validation']['state']=='INVALID'
    complete=add(c,'sm2-4',59)
    assert complete['validation']['state']=='VALID' and complete['validation']['total']==60
    assert complete['validation']['categories']=={'Pokemon':1,'Energy':59}
    oversized=add(c,'sm2-4'); assert oversized['validation']['state']=='INVALID'
    assert any('61' in r for r in oversized['validation']['reasons'])
    assert cards.path.read_bytes()==before and state.read_bytes()==owned


def test_functional_counts_presentation_and_rule_name_limits(setup):
    cards,state,c=setup
    add(c,'sm2-1',2); grouped=add(c,'sm2-2',2)
    assert len(grouped['deck']['entries'])==1 and grouped['deck']['entries'][0]['quantity']==4
    key=grouped['deck']['entries'][0]['identity']
    result=mutate(c,'default_printing',identity=key,printing_id='sm2-2',variant='reverse')
    assert result['deck']['entries'][0]['quantity']==4
    assert result['validation']['state']=='IN PROGRESS'  # Historical artwork uses a legal equivalent.
    mutate(c,'save'); mutate(c,'new'); result=mutate(c,'open',deck_id=result['deck']['id'])
    assert result['defaults'][key]['variant']=='reverse'
    assert result['defaults'][key]['printing_id']=='sm2-2'
    distinct=add(c,'sm2-3')
    assert len(distinct['deck']['entries'])==2
    assert any('5 copies across printings' in r for r in distinct['validation']['reasons'])
    revision=distinct['revision']
    wrong=c.post('/api/v1/deck-workspace',json=dict(schema_version=2,action='default_printing',revision=revision,identity=key,printing_id='sm2-3'))
    assert wrong.status_code==422


def test_basic_energy_adapter_and_ownership_is_only_context(setup):
    _,_,c=setup
    c.put('/api/v1/collection/sm2-4',json={'variant':'normal','quantity':2})
    add(c,'sm2-1'); add(c,'sm2-4',3); result=add(c,'sm2-5',3)
    water=next(e for e in result['deck']['entries'] if e['identity']=='deck-basic-energy:Water')
    assert water['quantity']==6 and water['owned']['quantity']==2
    assert result['validation']['state']=='IN PROGRESS'
    result=add(c,'sm2-6')
    assert len(result['deck']['entries'])==3
    for id in ('sm2-7','sm2-8'):
        result=add(c,id,5)
        assert any('5 copies' in r for r in result['validation']['reasons'])
    assert c.get('/api/v1/cards/sm2-4/ownership?variant=normal').json()['quantity']==2
    assert c.get('/api/v1/cards/sm2-4').json()['card']['deck_identity']==c.get('/api/v1/cards/sm2-5').json()['card']['deck_identity']


@pytest.mark.parametrize('id,n,reason',[('sm2-1',5,'copies'),('sm2-9',2,'ACE SPEC'),('sm2-10',1,'not legal'),('sm2-4',1,'Basic Pokemon')])
def test_real_rule_violations_override_partial(setup,id,n,reason):
    result=add(setup[2],id,n)
    assert result['validation']['state']=='INVALID'
    assert any(reason in r for r in result['validation']['reasons'])


def test_unknown_evidence_is_never_valid(setup):
    result=add(setup[2],'sm2-11')
    assert result['validation']['state']=='INVALID' and result['validation']['unknown']


def test_unsaved_complete_and_saved_empty(setup):
    c=setup[2]; add(c,'sm2-1'); result=add(c,'sm2-4',59)
    assert not result['deck']['has_saved'] and result['validation']['state']=='VALID'
    mutate(c,'save')
    for entry in result['deck']['entries']: result=mutate(c,'remove',identity=entry['identity'])
    assert result['validation']['state']=='INVALID' and result['validation']['total']==0


def test_zero_removal_and_new_open_discard_guard(setup):
    c=setup[2]; draft=add(c,'sm2-1')
    for action in ('new','open'):
        assert c.post('/api/v1/deck-workspace',json=dict(schema_version=2,action=action,revision=draft['revision'])).status_code==409
    result=mutate(c,'quantity',printing_id='sm2-2',delta=-1)
    assert not result['deck']['entries']
    assert mutate(c,'new',discard=True)['validation']['state']=='EMPTY'


def test_concurrent_revision_conflict_prevents_lost_updates(setup):
    c=setup[2]; revision=c.get('/api/v1/deck-workspace').json()['revision']
    def post(_): return c.post('/api/v1/deck-workspace',json=dict(schema_version=2,action='quantity',revision=revision,printing_id='sm2-1',delta=1)).status_code
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(post,range(2)))
    assert sorted(results)==[200,409]
    assert c.get('/api/v1/deck-workspace').json()['deck']['entries'][0]['quantity']==1


def test_save_failure_visible_without_losing_draft(setup,monkeypatch):
    c=setup[2]; draft=add(c,'sm2-1')
    original=Decks.apply
    def fail(self,command): raise sqlite3.OperationalError('disk full')
    monkeypatch.setattr(Decks,'apply',fail)
    assert c.post('/api/v1/deck-workspace',json=dict(schema_version=2,action='save',revision=draft['revision'])).status_code==503
    monkeypatch.setattr(Decks,'apply',original)
    assert c.get('/api/v1/deck-workspace').json()['deck']==draft['deck']


def test_missing_cache_entry_preserved_and_unknown(setup):
    cards,_,c=setup; draft=add(c,'sm2-1')
    with closing(cards.connect()) as db,db: db.execute("DELETE FROM cards WHERE id IN ('sm2-1','sm2-2')")
    result=c.get('/api/v1/deck-workspace').json()
    assert result['deck']['entries'][0]['identity']==draft['deck']['entries'][0]['identity']
    assert not result['deck']['entries'][0]['presentation_available']
    assert result['validation']['state']=='INVALID' and result['validation']['unknown']


def test_bad_storage_version_does_not_recreate_database(setup):
    _,state,c=setup; c.get('/api/v1/deck-workspace')
    path=state.with_name('deck-workspace.sqlite3')
    with closing(sqlite3.connect(path)) as db,db: db.execute('PRAGMA user_version=99')
    before=path.read_bytes()
    assert c.get('/api/v1/deck-workspace').status_code==503
    assert path.read_bytes()==before
