"""PM QA contracts: ownership, rules, allocations and user defaults stay separate."""
from contextlib import closing
from copy import deepcopy
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient
from pokelab.api import create_app
from pokelab.decks import check_allocations
from test_deck_builder import setup, mutate, add


def exact(client, printing, quantity=1, variant='normal'):
    for _ in range(quantity):
        result = mutate(client, 'quantity', printing_id=printing, variant=variant, delta=1, exact=True)
    return result


def allocations(result, index=0):
    entry = result['deck']['entries'][index]
    assert entry['quantity'] == sum(a['quantity'] for a in entry['allocations'])
    return {(a['printing_id'], a['variant']): a['quantity'] for a in entry['allocations']}


def test_mixed_exact_quantities_rules_and_restart(setup):
    cards, state, client = setup
    ownership = state.read_bytes()
    exact(client, 'sm2-1')
    mixed = exact(client, 'sm2-2', 2, 'reverse')
    expected = {('sm2-1','normal'):1, ('sm2-2','reverse'):2}
    assert allocations(mixed) == expected
    # Decrementing a zero variation cannot steal a different finish's copies.
    unchanged = mutate(client, 'quantity', printing_id='sm2-2', variant='normal', delta=-1, exact=True)
    assert allocations(unchanged) == expected
    saved = mutate(client, 'save')
    restart = TestClient(create_app(cards.path,state))
    assert allocations(restart.get('/api/v1/deck-workspace').json()) == expected
    mutate(restart,'new')
    assert allocations(mutate(restart,'open',deck_id=saved['deck']['id'])) == expected
    invalid = exact(restart,'sm2-2',2)
    assert invalid['deck']['entries'][0]['quantity'] == 5
    assert any('5 copies' in r for r in invalid['validation']['reasons'])
    assert state.read_bytes() == ownership


def test_defaults_replace_persist_and_never_rewrite_decks_or_collection(setup):
    cards,state,c = setup
    before = state.read_bytes()
    original = exact(c,'sm2-1')
    key = original['deck']['entries'][0]['identity']
    saved = mutate(c,'save')
    preferred = mutate(c,'default_printing',printing_id='sm2-2',variant='reverse')
    assert preferred['deck'] == saved['deck']
    assert preferred['validation'] == saved['validation']
    assert preferred['defaults'][key]['printing_id'] == 'sm2-2'
    assert preferred['deck']['entries'][0]['owned']['quantity'] == 0
    assert allocations(add(c,'sm2-1')) == {('sm2-1','normal'):1,('sm2-2','reverse'):1}
    explicit = exact(c,'sm2-1')
    assert allocations(explicit) == {('sm2-1','normal'):2,('sm2-2','reverse'):1}
    replacement = mutate(c,'default_printing',printing_id='sm2-1',variant='reverse')
    assert replacement['deck'] == explicit['deck']
    assert len(replacement['defaults']) == 1
    restart = TestClient(create_app(cards.path,state))
    restored = restart.get('/api/v1/deck-workspace').json()
    assert restored['defaults'] == replacement['defaults']
    mutate(restart,'new',discard=True)
    future = add(restart,'sm2-2')
    assert allocations(future) == {('sm2-1','reverse'):1}
    reopened = mutate(restart,'open',deck_id=saved['deck']['id'],discard=True)
    assert reopened['deck'] == saved['deck']
    assert state.read_bytes() == before


def test_energy_allocations_type_defaults_and_variations(setup):
    _,_,c=setup
    exact(c,'sm2-4',2); result=exact(c,'sm2-5',5)
    assert allocations(result) == {('sm2-4','normal'):2,('sm2-5','normal'):5}
    assert result['deck']['entries'][0]['identity']=='deck-basic-energy:Water'
    mutate(c,'default_printing',printing_id='sm2-5')
    mutate(c,'default_printing',printing_id='sm2-6')
    result=add(c,'sm2-4')
    assert allocations(result)[('sm2-5','normal')]==6
    result=exact(c,'sm2-6')
    assert result['deck']['entries'][1]['identity']=='deck-basic-energy:Fire'
    result=exact(c,'sm2-7')
    assert not result['deck']['entries'][2]['identity'].startswith('deck-basic-energy:')
    assert set(result['defaults'])=={'deck-basic-energy:Water','deck-basic-energy:Fire'}
    page=c.get('/api/v1/cards/sm2-4/variations?scope=deck').json()
    assert {v['id'] for v in page['cards']}=={'sm2-4','sm2-5'}
    # The certified functional/Library endpoints still have their original scope.
    functional=c.get('/api/v1/cards/sm2-4/variations?scope=functional').json()
    assert {v['id'] for v in functional['cards']}=={'sm2-4'}


def legacy_database(state, document, saved_document=None):
    path=state.with_name('deck-workspace.sqlite3')
    with closing(sqlite3.connect(path)) as db,db:
        db.execute('CREATE TABLE workspace (id INTEGER PRIMARY KEY,revision INTEGER,document TEXT)')
        db.execute('CREATE TABLE saved_decks (id TEXT PRIMARY KEY,document TEXT,updated_at TEXT)')
        db.execute('INSERT INTO workspace VALUES (1,107,?)',(json.dumps(document),))
        db.execute('INSERT INTO saved_decks VALUES (?,?,?)',('saved',json.dumps(saved_document or document),'original timestamp'))
        db.execute('PRAGMA user_version=1')
    return path


def legacy_document():
    return dict(id='draft',name='PM QA',format='standard',has_saved=True,dirty=True,
                entries=[dict(identity='deck-basic-energy:Water',quantity=7,printing_id='sm2-4',variant='normal',name='Water Energy',category='Energy')])


def test_atomic_v1_migration_preserves_active_saved_and_original_archive(setup):
    cards,state,c=setup
    old=legacy_document(); path=legacy_database(state,old)
    result=c.get('/api/v1/deck-workspace').json()
    assert result['schema_version']==2 and result['revision']==108
    assert allocations(result)=={('sm2-4','normal'):7}
    assert result['defaults']=={} and result['deck']['dirty']
    with closing(sqlite3.connect(path)) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0]==2
        archived=db.execute('SELECT document FROM migration_v1_backup').fetchall()
        assert len(archived)==2 and all(json.loads(r[0])==old for r in archived)
        assert db.execute('SELECT updated_at FROM saved_decks').fetchone()[0]=='original timestamp'
    # Repeat startup is idempotent, including revision and defaults.
    restart=TestClient(create_app(cards.path,state))
    assert restart.get('/api/v1/deck-workspace').json()==result
    assert allocations(mutate(restart,'open',deck_id='saved',discard=True))=={('sm2-4','normal'):7}


def test_bad_legacy_saved_document_rolls_back_all_migration(setup):
    _,state,c=setup
    old=legacy_document(); bad=deepcopy(old);bad['entries'][0]['quantity']=0
    path=legacy_database(state,old,bad)
    before=path.read_bytes()
    assert c.get('/api/v1/deck-workspace').status_code==503
    assert path.read_bytes()==before
    with closing(sqlite3.connect(path)) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0]==1
        assert json.loads(db.execute('SELECT document FROM workspace').fetchone()[0])==old


@pytest.mark.parametrize('damage',['sum','duplicate','negative','boolean'])
def test_allocation_invariant_rejects_corruption(damage):
    allocation=dict(printing_id='a',variant='normal',quantity=1)
    doc=dict(entries=[dict(identity='f',quantity=1,allocations=[allocation])])
    if damage=='sum': doc['entries'][0]['quantity']=2
    elif damage=='duplicate': doc['entries'][0]['allocations'].append(deepcopy(allocation))
    elif damage=='negative': allocation['quantity']=-1
    else: allocation['quantity']=True
    with pytest.raises(ValueError):check_allocations(doc)


def test_missing_default_keeps_preference_but_implicit_add_uses_available_card(setup):
    cards,_,c=setup
    default=mutate(c,'default_printing',printing_id='sm2-2',variant='reverse')
    key=next(iter(default['defaults']))
    with closing(cards.connect()) as db,db:db.execute("DELETE FROM cards WHERE id='sm2-2'")
    result=add(c,'sm2-1')
    assert allocations(result)=={('sm2-1','normal'):1}
    assert result['defaults'][key]==dict(printing_id='sm2-2',variant='reverse',available=False)


def test_old_client_contract_is_rejected_without_mutation(setup):
    c=setup[2]; before=c.get('/api/v1/deck-workspace').json()
    response=c.post('/api/v1/deck-workspace',json=dict(action='quantity',revision=before['revision'],printing_id='sm2-1',delta=1))
    assert response.status_code==422
    assert c.get('/api/v1/deck-workspace').json()==before
