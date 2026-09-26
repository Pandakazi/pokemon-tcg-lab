from copy import deepcopy
from datetime import date
import json

import pytest
from fastapi.testclient import TestClient
from pokelab.api import create_app
from pokelab.decks import Decks, DeckCommand, DeckConflict, ResearchCopy, deck_identity
from pokelab.research_identity import evidence_key
from tcg_lab.card_db import SQLiteCards
from test_research import research, seed, KEY


def command(workspace, **values):
    return ResearchCopy(schema_version=2,revision=workspace['revision'],source='tournament',key=evidence_key('1',1),**values)


def stored(decks):
    with decks.connect() as db:
        return {t:[tuple(r) for r in db.execute(f'SELECT * FROM {t} ORDER BY 1')] for t in ('workspace','saved_decks','default_printings')}


@pytest.mark.parametrize('source',['tournament','composite'])
def test_copy_exact_new_saved_preferred_unowned_and_immutable(research,source):
    alternative=deepcopy(research.collection.catalog()[0]['sm2-1']['card'])
    alternative.update(id='sm2-4',localId='4',variants={'normal':True,'reverse':True})
    SQLiteCards(research.collection.cards.path).put(alternative)
    seed(research,[4],day=date.today())
    decks=Decks(research.collection,research.collection.path.with_name('decks.sqlite3'))
    before=decks.read()
    before=decks.apply(DeckCommand(schema_version=2,revision=before['revision'],action='save'))
    old=stored(decks)['saved_decks']
    before=decks.apply(DeckCommand(schema_version=2,revision=before['revision'],action='default_printing',printing_id='sm2-4',variant='reverse'))
    ownership=research.collection.path.read_bytes(); evidence=research.competitive.path.read_bytes()
    result=decks.copy_research(ResearchCopy(schema_version=2,revision=before['revision'],source=source,key=KEY if source=='composite' else evidence_key('1',1)),research)
    assert result['deck']['id']!=before['deck']['id']
    assert result['deck']['has_saved'] and not result['deck']['dirty']
    assert result['validation']['total']==60 and result['validation']['state']=='VALID'
    expected={deck_identity(research.collection.catalog()[0]['sm2-1']):4,deck_identity(research.collection.catalog()[0]['sm2-3']):56}
    assert {e['identity']:e['quantity'] for e in result['deck']['entries']}==expected
    assert result['defaults']==before['defaults']
    first=next(e for e in result['deck']['entries'] if e['identity']==deck_identity(research.collection.catalog()[0]['sm2-1']))
    assert first['allocations'][0]['printing_id']=='sm2-4' and first['allocations'][0]['variant']=='reverse'
    assert all(e['owned']['functional_total']==0 for e in result['deck']['entries'])
    assert all(row in stored(decks)['saved_decks'] for row in old)
    assert decks.read()==result
    assert research.collection.path.read_bytes()==ownership
    assert research.competitive.path.read_bytes()==evidence


def test_dirty_and_stale_protected_then_explicit_discard(research):
    seed(research,[4]);decks=Decks(research.collection,research.collection.path.with_name('decks.sqlite3'))
    initial=decks.read()
    dirty=decks.apply(DeckCommand(schema_version=2,revision=initial['revision'],action='rename',name='Keep me'))
    before=stored(decks)
    with pytest.raises(DeckConflict):decks.copy_research(command(dirty),research)
    with pytest.raises(DeckConflict):decks.copy_research(command(initial,discard=True),research)
    assert stored(decks)==before
    assert decks.copy_research(command(dirty,discard=True),research)['validation']['total']==60


@pytest.mark.parametrize('failure',['unmapped','short','missing_printing','response'])
def test_atomic_failure_leaves_workspace_saved_and_defaults_intact(research,monkeypatch,failure):
    seed(research,[4]);decks=Decks(research.collection,research.collection.path.with_name('decks.sqlite3'))
    before=decks.read(); rows=stored(decks)
    source=deepcopy(research.tournament_deck(evidence_key('1',1)))
    if failure=='unmapped':source['observation']['mapped']=False
    if failure=='short':source['card_count']=59
    if failure=='missing_printing':source['cards'][-1]['card']=None
    if failure=='response':monkeypatch.setattr(decks,'response',lambda *args:(_ for _ in ()).throw(ValueError('Injected post-write validation failure')))
    monkeypatch.setattr(research,'tournament_deck',lambda key:source)
    with pytest.raises(ValueError):decks.copy_research(command(before),research)
    assert stored(decks)==rows


def test_tournament_invalid_copy_is_faithful_not_repaired(research):
    seed(research,[5]);decks=Decks(research.collection,research.collection.path.with_name('decks.sqlite3'))
    result=decks.copy_research(command(decks.read()),research)
    assert result['validation']['total']==60 and result['validation']['state']=='INVALID'
    assert sorted(e['quantity'] for e in result['deck']['entries'])==[5,55]


def test_typed_api_copy_and_rejection(research):
    seed(research,[4],day=date.today())
    app=create_app(database=research.collection.cards.path,state_database=research.collection.path,competitive_database=research.competitive.path,deck_database=research.collection.path.with_name('api-decks.sqlite3'))
    with TestClient(app) as client:
        before=client.get('/api/v1/deck-workspace').json()
        body=command(before).model_dump()
        invalid=client.post('/api/v1/deck-workspace/copy-research',json={**body,'cards':[]})
        assert invalid.status_code==422
        response=client.post('/api/v1/deck-workspace/copy-research',json=body)
        assert response.status_code==200 and response.json()['validation']['total']==60
        assert client.post('/api/v1/deck-workspace/copy-research',json=body).status_code==409
