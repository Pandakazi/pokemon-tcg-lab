from contextlib import closing
import sqlite3
import httpx
import pytest
from fastapi.testclient import TestClient
from pokelab.api import create_app
from tcg_lab.card_db import SQLiteCards
from test_card_data import card, set_record


@pytest.fixture
def cache(tmp_path):
    db = SQLiteCards(tmp_path / 'cards.sqlite3')
    db.put_set(set_record())
    for n in range(3):
        record = card(f'sm2-{n}')
        record['attacks'][0]['damage'] = n * 10  # Three distinct functional cards.
        record['legal']['standard'] = True
        db.put(record)
    db.put(card('sm2-99'))  # Illegal records must not leak into the gallery.
    record = card('sm2-98'); record['legal']['standard'] = True; record['category'] = 'Trainer'
    db.put(record)
    db.metadata('last_sync', {'status': 'complete', 'finished_at': '2026-09-23T00:00:00Z'})
    return db


def test_status_pagination_contract_and_no_upstream(cache, monkeypatch):
    monkeypatch.setattr(httpx.HTTPTransport, 'handle_request', lambda *a, **k: pytest.fail('Unexpected upstream request'))
    before = cache.path.read_bytes()
    client = TestClient(create_app(cache.path))
    assert client.get('/api/v1/status').json()['ready'] is True
    first = client.get('/api/v1/cards?page_size=2').json()
    assert first['total'] == 3 and first['next_page'] == 2
    assert [c['id'] for c in first['cards']] == ['sm2-0', 'sm2-1']
    assert client.get('/api/v1/cards?page=2&page_size=2').json()['cards'][0]['id'] == 'sm2-2'
    assert client.get('/api/v1/cards?page=3&page_size=2').json()['cards'] == []
    for record in first['cards']:
        assert record['category'] == 'Pokemon' and record['legal']['standard'] is True
        assert record['set'] == {'id': 'sm2', 'name': 'Guardians Rising'}
        assert record['localId'] == record['id'].split('-')[1]
        assert record['legality_provenance']['source'] == 'TCGdex'
        assert record['legality_provenance']['checked_at']
        assert not {'image', 'image_url', 'attacks', 'abilities', 'pricing'} & record.keys()
    assert cache.path.read_bytes() == before


@pytest.mark.parametrize('params', ['page=0', 'page=10001', 'page=x', 'page_size=0', 'page_size=51', 'include_image=bad'])
def test_validation(cache, params):
    assert TestClient(create_app(cache.path)).get('/api/v1/cards?' + params).status_code == 422


def test_images_are_opt_in_and_allowlisted(cache):
    client = TestClient(create_app(cache.path))
    assert client.get('/api/v1/cards?include_image=true').json()['cards'][0]['image_url'].endswith('/low.webp')
    record = card('sm2-0'); record['legal']['standard'] = True; record['image'] = 'https://evil.invalid/image'
    cache.put(record)
    assert client.get('/api/v1/cards?include_image=true').json()['cards'][0]['image_url'] is None


@pytest.mark.parametrize('state', ['missing', 'empty', 'corrupt', 'unsupported'])
def test_unavailable_database(tmp_path, state):
    path = tmp_path / 'cache.sqlite3'
    if state == 'empty': SQLiteCards(path)
    if state == 'corrupt': path.write_bytes(b'broken')
    if state == 'unsupported':
        with closing(sqlite3.connect(path)) as db: db.execute('PRAGMA user_version=99')
    client = TestClient(create_app(path))
    for endpoint in ('status', 'cards'):
        result = client.get('/api/v1/' + endpoint)
        assert result.status_code == 503
        assert result.json()['detail']['code'] == 'card_cache_unavailable'
        assert str(path) not in result.text
    if state == 'missing': assert not path.exists()

@pytest.fixture
def library(tmp_path):
    db = SQLiteCards(tmp_path / 'library.sqlite3')
    db.put_set(set_record())
    records = [
        ('sm2-1', 'Psychic Basic', 'Pokemon', {'types':['Psychic'], 'stage':'Basic'}),
        ('sm2-2', 'Dragon Basic', 'Pokemon', {'types':['Dragon'], 'stage':'Basic'}),
        ('sm2-3', 'Dual Evolution', 'Pokemon', {'types':['Psychic','Dragon'], 'stage':'Stage1'}),
        ('sm2-4', 'Water Basic', 'Pokemon', {'types':['Water'], 'stage':'Basic'}),
        ('sm2-5', "Boss's Orders", 'Trainer', {'trainerType':'Supporter'}),
        ('sm2-6', 'Useful Tool', 'Trainer', {'trainerType':'Tool'}),
        ('sm2-7', 'Basic Energy', 'Energy', {'energyType':'Normal'}),
        ('sm2-8', 'Special Energy', 'Energy', {'energyType':'Special'}),
    ]
    for id, name, category, fields in records:
        record=card(id,name)
        record.update(category=category, legal={'standard':True}, regulationMark='H', **fields)
        db.put(record)
    return db


def test_category_search_and_no_results(library):
    client=TestClient(create_app(library.path))
    for category,count in [('Pokemon',4),('Trainer',2),('Energy',2)]:
        result=client.get('/api/v1/cards',params={'category':category}).json()
        assert result['total']==count
        assert all(c['category']==category for c in result['cards'])
    assert client.get('/api/v1/cards?category=Trainer&q=bOsS').json()['cards'][0]['id']=='sm2-5'
    assert client.get('/api/v1/cards?category=Pokemon&q=boss').json()['total']==0
    assert client.get('/api/v1/cards?q=nonexistent').json()['cards']==[]


def test_filter_families_multitype_and_paging(library):
    client=TestClient(create_app(library.path))
    def ids(query): return [c['id'] for c in client.get('/api/v1/cards?'+query).json()['cards']]
    assert ids('pokemon_types=Dragon')==['sm2-2','sm2-3']
    assert ids('pokemon_types=Psychic&pokemon_types=Dragon')==['sm2-1','sm2-2','sm2-3']
    query='pokemon_types=Psychic&pokemon_types=Dragon&stages=Basic&regulation_marks=H&q=BASIC'
    assert ids(query)==['sm2-1','sm2-2']
    assert ids(query+'&page_size=1&page=1')==['sm2-1']
    assert ids(query+'&page_size=1&page=2')==['sm2-2']
    assert ids('category=Trainer&trainer_types=Tool')==['sm2-6']
    assert ids('category=Trainer&trainer_types=Tool&trainer_types=Supporter')==['sm2-5','sm2-6']
    assert ids('category=Energy&energy_types=Special')==['sm2-8']
    assert ids('regulation_marks=I')==[]
    options=client.get('/api/v1/cards?category=Trainer').json()['filter_options']
    assert next(f['values'] for f in options if f['parameter']=='trainer_types')==['Supporter','Tool']


@pytest.mark.parametrize('query',['category=Tool','pokemon_types=Invalid','stages=Stage9','trainer_types=Magic',
 'energy_types=Magic','regulation_marks=ZZ','category=Trainer&pokemon_types=Psychic',
 'category=Energy&trainer_types=Item','category=Pokemon&energy_types=Normal','q='+('x'*101),'unknown=x'])
def test_invalid_library_filters(library,query):
    assert TestClient(create_app(library.path)).get('/api/v1/cards?'+query).status_code==422


def test_exact_detail_metadata_and_read_only(library,monkeypatch):
    monkeypatch.setattr(httpx.HTTPTransport,'handle_request',lambda *a,**k:pytest.fail('Upstream request'))
    before=library.path.read_bytes()
    client=TestClient(create_app(library.path))
    response=client.get('/api/v1/cards/sm2-3')
    assert response.status_code==200
    result=response.json()
    assert result['card']['id']=='sm2-3'
    assert result['card']['types']==['Psychic','Dragon']
    assert result['card']['attacks'][0]['effect']=='The Defending Pokemon cannot retreat.'
    assert result['card']['set']['code']=='GRI'
    assert 'image_url' not in result['card'] and 'https://assets.tcgdex.net' not in response.text
    assert client.get('/api/v1/cards/sm2-3?include_image=true').json()['card']['image_url'].endswith('/high.webp')
    assert client.get('/api/v1/cards/sm2-5').json()['card']['trainerType']=='Supporter'
    assert client.get('/api/v1/cards/sm2-8').json()['card']['energyType']=='Special'
    assert client.get('/api/v1/cards/sm2-999').status_code==404
    assert client.get('/api/v1/cards/bad%20id').status_code==422
    assert library.path.read_bytes()==before


def test_detail_missing_cache_is_503_without_creating_it(tmp_path):
    path=tmp_path/'missing.sqlite3'
    assert TestClient(create_app(path)).get('/api/v1/cards/sm2-3').status_code==503
    assert not path.exists()


def test_empty_families_repeated_values_and_category_unions(library):
    for id, subtype, mark in [('sm2-10', 'Supporter', 'J'), ('sm2-11', 'Item', 'J')]:
        record = card(id, id)
        record.update(category='Trainer', trainerType=subtype, regulationMark=mark, legal={'standard': True})
        library.put(record)
    client = TestClient(create_app(library.path))
    def ids(query):
        response = client.get('/api/v1/cards?' + query)
        assert response.status_code == 200, response.text
        return {c['id'] for c in response.json()['cards']}
    all_trainers = {'sm2-5', 'sm2-6', 'sm2-10', 'sm2-11'}
    assert ids('category=Trainer') == all_trainers
    assert ids('category=Trainer&trainer_types=&regulation_marks=') == all_trainers
    assert ids('category=Trainer&trainer_types=Supporter&regulation_marks=H') == {'sm2-5'}
    assert ids('category=Trainer&trainer_types=Supporter&regulation_marks=H&regulation_marks=J&regulation_marks=H') == {'sm2-5', 'sm2-10'}
    assert ids('category=Trainer&trainer_types=Supporter&trainer_types=Item&regulation_marks=J') == {'sm2-10', 'sm2-11'}
    assert ids('category=Energy&energy_types=') == ids('category=Energy') == {'sm2-7', 'sm2-8'}
    assert ids('category=Energy&energy_types=Normal') == {'sm2-7'}
    assert ids('category=Energy&energy_types=Special') == {'sm2-8'}
    assert ids('category=Energy&energy_types=Normal&energy_types=Special&energy_types=Normal&energy_types=') == {'sm2-7', 'sm2-8'}
    assert ids('pokemon_types=&stages=&regulation_marks=') == ids('category=Pokemon')


def test_has_ability_uses_structured_kind_and_combines_with_filters(library):
    # A legacy power and arbitrary text mentioning Ability are not an Ability.
    for id, abilities in [('sm2-3', [{'type': 'Ancient Trait', 'name': 'Ability'}]), ('sm2-4', [])]:
        record = library.get(id)['card']
        record.update(abilities=abilities, effect='The word Ability alone must not match')
        library.put(record)
    client = TestClient(create_app(library.path))
    query = 'pokemon_types=Psychic&pokemon_types=Dragon&stages=Basic&has_ability=true&page_size=1'
    first = client.get('/api/v1/cards?' + query).json()
    second = client.get('/api/v1/cards?' + query + '&page=2').json()
    assert first['total'] == 2 and first['next_page'] == 2
    assert first['cards'][0]['id'] == 'sm2-1'
    assert second['cards'][0]['id'] == 'sm2-2' and second['next_page'] is None
    assert client.get('/api/v1/cards?has_ability=true').json()['total'] == 2
    assert client.get('/api/v1/cards?has_ability=false').json()['total'] == 4
    assert client.get('/api/v1/cards?has_ability=invalid').status_code == 422
    assert client.get('/api/v1/cards?category=Trainer&has_ability=true').status_code == 422
    assert client.get('/api/v1/cards?category=Energy&has_ability=true').status_code == 422
    assert client.get('/api/v1/cards?ability=Yes').json()['total'] == 2
    assert client.get('/api/v1/cards?ability=No').json()['total'] == 2
    assert client.get('/api/v1/cards?ability=Yes&ability=No&ability=Yes').json()['total'] == 4
    assert client.get('/api/v1/cards?ability=').json()['total'] == 4
    assert client.get('/api/v1/cards?ability=No&stages=Basic&pokemon_types=Psychic&pokemon_types=Water').json()['cards'][0]['id'] == 'sm2-4'
    assert client.get('/api/v1/cards?ability=Maybe').status_code == 422
    assert client.get('/api/v1/cards?category=Energy&ability=No').status_code == 422


def test_library_basic_energy_curates_types_without_changing_engine_identity(tmp_path):
    from pokelab.engine import functional_signature
    from pokelab.library_identity import library_signature
    db = SQLiteCards(tmp_path / 'basic.sqlite3')
    old = set_record('old'); old['releaseDate'] = '2020-01-01'
    new = set_record('new'); new['releaseDate'] = '2026-01-01'
    db.put_set(old); db.put_set(new)
    for n in range(30):
        record = card(f'old-{n}', 'Water Energy')
        record.update(category='Energy', energyType='Normal', types=['Water'], legal={'standard':True}, effect=str(n))
        db.put(record)
    newest = card('new-1', 'Basic Water Energy')
    newest.update(category='Energy', energyType='Normal', types=['Water'], legal={'standard':True})
    db.put(newest)
    fire = dict(newest, id='new-2', name='Basic Fire Energy', types=['Fire']); db.put(fire)
    illegal = dict(newest, id='new-9', legal={'standard':False}); db.put(illegal)
    special = dict(newest, id='new-3', name='Special Water Energy', energyType='Special'); db.put(special)
    ambiguous = dict(newest, id='new-4', name='Prism Energy', types=[]); db.put(ambiguous)
    assert functional_signature(record) != functional_signature(newest)
    assert library_signature(record) == library_signature(newest)
    assert library_signature(special) == functional_signature(special)
    assert library_signature(ambiguous) == functional_signature(ambiguous)
    client = TestClient(create_app(db.path))
    before = db.path.read_bytes()
    all_cards = client.get('/api/v1/cards?category=Energy').json()
    assert [r['id'] for r in all_cards['cards']] == ['new-1','new-2','new-3','new-4']
    for query in ('energy_types=', 'energy_types=Normal&energy_types=Special'):
        assert client.get('/api/v1/cards?category=Energy&'+query).json()['total'] == 4
    assert client.get('/api/v1/cards?category=Energy&energy_types=Special').json()['total'] == 1
    assert client.get('/api/v1/cards/old-1').json()['card']['id'] == 'old-1'
    assert db.search('', category='Energy', format='standard')['total'] == 34
    assert db.path.read_bytes() == before


@pytest.mark.parametrize('category,fields', [
    ('Pokemon', {'types': ['Water'], 'stage': 'Basic'}),
    ('Trainer', {'trainerType': 'Supporter'}),
    ('Energy', {'energyType': 'Normal'}),
])
def test_library_representatives_prevent_reprint_spam_before_paging(tmp_path, category, fields):
    db = SQLiteCards(tmp_path / 'representatives.sqlite3')
    old_set = set_record(); old_set.update(id='old', releaseDate='2020-01-01')
    new_set = set_record(); new_set.update(id='new', releaseDate='2026-01-01')
    db.put_set(old_set); db.put_set(new_set)
    for n in range(30):
        record = card(f'old-{n}', 'Repeated card')
        record.update(category=category, set={'id':'old','name':'Older set'},
                      legal={'standard':True}, regulationMark='H', **fields)
        db.put(record)
    latest = card('new-1', 'Repeated card')
    latest.update(category=category, set={'id':'new','name':'New set'},
                  legal={'standard':True}, regulationMark='J', **fields)
    db.put(latest)
    # A newer nonlegal printing must not replace the legal representative.
    illegal = dict(latest, id='new-99', legal={'standard':False})
    db.put(illegal)
    different = card('new-2', 'Repeated card')
    different.update(category=category, set=latest['set'], legal={'standard':True}, **fields)
    different['attacks'][0]['damage'] = 999  # Same name, different gameplay stays distinct.
    db.put(different)
    client = TestClient(create_app(db.path))
    before = db.path.read_bytes()
    query = f'category={category}&page_size=1'
    first = client.get('/api/v1/cards?' + query).json()
    second = client.get('/api/v1/cards?' + query + '&page=2').json()
    assert first['total'] == 2 and first['next_page'] == 2
    assert first['cards'][0]['id'] == 'new-1'
    assert second['cards'][0]['id'] == 'new-2' and second['next_page'] is None
    empty = client.get('/api/v1/cards?' + query + '&regulation_marks=').json()
    assert empty['total'] == 2 and empty['cards'] == first['cards']
    marked = client.get('/api/v1/cards?' + query + '&regulation_marks=H&regulation_marks=J').json()
    assert marked['total'] == 1 and marked['cards'][0]['id'] == 'new-1'
    h_only = client.get('/api/v1/cards?' + query + '&regulation_marks=H').json()
    assert h_only['total'] == 1 and h_only['cards'][0]['id'].startswith('old-')
    assert client.get('/api/v1/cards/new-1').json()['card']['id'] == 'new-1'
    assert client.get('/api/v1/cards/old-1').json()['card']['id'] == 'old-1'
    assert db.search('', category=category, format='standard')['total'] == 32  # MCP remains exact.
    assert db.path.read_bytes() == before
