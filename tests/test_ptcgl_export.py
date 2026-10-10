import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from tcg_lab.card_db import SQLiteCards
from pokelab.api import create_app
from test_card_data import card,set_record


@pytest.fixture
def export_api(tmp_path):
    cards=SQLiteCards(tmp_path/'cards.sqlite3')
    return cards,TestClient(create_app(cards.path,tmp_path/'collection.sqlite3',tmp_path/'competitive.sqlite3'))


def add(cards,id,name,code=None,number='001',category='Pokemon',online=None,**fields):
    set_id=id.rsplit('-',1)[0]
    metadata=set_record(set_id);metadata.pop('tcgOnline')
    if code:metadata['abbreviation']={'official':code}
    if online:metadata['tcgOnline']=online
    cards.put_set(metadata)
    raw=card(id,name);raw.update(category=category,localId=number,**fields)
    cards.put(raw)


def copy(api,rows):return api.post('/api/v1/decks/export-ptcgl',json={'cards':rows})


def test_full_published_deck_matches_ptcgl_fixture_and_does_not_write(export_api):
    cards,api=export_api
    fixture=json.loads(Path('tests/fixtures/ptcgl-export.json').read_text(encoding='utf-8'))
    for metadata in fixture['sets']:cards.put_set(metadata)
    for raw in fixture['cards']:cards.put(raw)
    before=cards.path.read_bytes()
    result=copy(api,fixture['rows']);assert result.status_code==200,result.text
    assert result.json()['text']==fixture['expected']
    assert result.json()['category_totals']=={'Pokemon':20,'Trainer':32,'Energy':8}
    assert result.json()['total']==60 and result.json()['warnings']==[]
    assert cards.path.read_bytes()==before
    assert not cards.path.with_name('collection.sqlite3').exists()


@pytest.mark.parametrize('name,code,online,number,expected',[
    ('Dreepy','PRE',None,'071','Dreepy PRE 71'),
    ('Flareon','BRS:TG','BRS','TG01','Flareon BRS TG01'),
    ('Hisuian Voltorb','CRZ:GG','CRZ','GG01','Hisuian Voltorb CRZ GG01'),
    ('Sprigatito','SVP',None,'001','Sprigatito SVP 1'),
    ("Boss's Orders",'PAL',None,'172',"Boss's Orders PAL 172"),
    ("Lillie's Determination",'MEG',None,'123',"Lillie's Determination MEG 123"),
    ('Pokégear 3.0','SVI',None,'186','Pokégear 3.0 SVI 186'),
])
def test_printing_metadata_not_internal_id_or_requested_name(export_api,name,code,online,number,expected):
    cards,api=export_api;add(cards,'example-001',name,code,number,online=online)
    result=copy(api,[{'printing_id':'example-001','quantity':2}])
    assert result.status_code==200,result.text
    assert f'2 {expected}' in result.json()['text'] and 'example-001' not in result.json()['text']


def test_basic_energy_exact_and_explicit_export_only_fallback(export_api):
    cards,api=export_api
    add(cards,'sve-007','Darkness Energy','SVE','007','Energy',energyType='Normal',types=['Darkness'])
    add(cards,'mee-002','Fire Energy','MEE','002','Energy',energyType='Normal',types=[])
    add(cards,'tk-bw-z-3','Darkness Energy','TK5Z','3','Energy',energyType='Normal',types=['Darkness'])
    metadata=set_record('tk-bw-z','tk');metadata.pop('tcgOnline');metadata['abbreviation']={'official':'TK5Z'};cards.put_set(metadata)
    before=cards.path.read_bytes()
    result=copy(api,[{'printing_id':'tk-bw-z-3','quantity':2},{'printing_id':'mee-002','quantity':3},{'printing_id':'sve-007','quantity':1}]).json()
    assert '3 Basic {D} Energy SVE 7' in result['text']
    assert '3 Basic {R} Energy MEE 2' in result['text']
    assert result['category_totals']['Energy']==6 and result['total']==6
    assert len(result['warnings'])==1 and 'allocations are unchanged' in result['warnings'][0]
    assert 'tk-bw-z' not in result['text'] and cards.path.read_bytes()==before


@pytest.mark.parametrize('code,number',[(None,'001'),('BRS:TG','TG01'),('PRE','1\nunsafe'),('PRE','1/131')])
def test_unmapped_printing_never_returns_partial_malformed_text(export_api,code,number):
    cards,api=export_api;add(cards,'bad-1','Unknown printing',code,number)
    add(cards,'ok-1','Good printing','PRE','1')
    result=copy(api,[{'printing_id':'ok-1','quantity':4},{'printing_id':'bad-1','quantity':1}])
    assert result.status_code==422 and 'text' not in result.json()


@pytest.mark.parametrize('rows',[[{'printing_id':'missing-1','quantity':1}],[],[{'printing_id':'x-1','quantity':True}],[{'printing_id':'x-1','quantity':0}]])
def test_invalid_export_is_bounded_and_explicit(export_api,rows):
    assert copy(export_api[1],rows).status_code==422


def test_null_abbreviation_is_unmapped_not_an_internal_error(export_api):
    cards,api=export_api;add(cards,'unknown-1','Unmapped card')
    metadata=set_record('unknown');metadata.pop('tcgOnline');metadata['abbreviation']=None;cards.put_set(metadata)
    assert copy(api,[{'printing_id':'unknown-1','quantity':1}]).status_code==422
