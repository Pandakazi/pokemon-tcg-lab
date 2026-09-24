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
