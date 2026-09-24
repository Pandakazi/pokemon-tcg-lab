"""Read-only web adapter. No MCP, Qt, synchronization or provider dependency."""
from contextlib import closing
import os
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException, Query

from tcg_lab.card_db import SQLiteCards
from tcg_lab.cards import CardLookupError
from .images import TCGdexImages


class ReadOnlyCards(SQLiteCards):
    """Use existing lookup semantics without creating or migrating a database."""
    def __init__(self, path):
        self.path = Path(path).resolve()

    def connect(self):
        db = sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True, timeout=5)
        db.row_factory = sqlite3.Row
        if db.execute('PRAGMA user_version').fetchone()[0] != 1:
            db.close()
            raise CardLookupError('Unsupported database version')
        return db


def create_app(database=None):
    app = FastAPI(title='PokéLab API', version='0.1.0')
    cards = ReadOnlyCards(database or os.getenv('TCG_CARDS_DB_PATH', 'data/cards.sqlite3'))
    images = TCGdexImages()

    def unavailable():
        return HTTPException(503, detail={'code': 'card_cache_unavailable',
            'message': 'The local card database is unavailable. Initialize it with python -m tcg_lab.sync_cards, then retry.'})

    @app.get('/api/v1/status')
    def status():
        try:
            result = cards.status()
            if not result['cards']:
                raise CardLookupError('Empty cache')
            sync = result.get('last_sync') or {}
            return {'app': 'PokéLab', 'ready': True, 'source': 'TCGdex SQLite',
                    'cards': result['cards'], 'sync': {key: sync[key] for key in ('status', 'finished_at', 'missing') if key in sync}}
        except (sqlite3.Error, OSError, ValueError):
            raise unavailable() from None

    @app.get('/api/v1/cards')
    def browse(page: int = Query(1, ge=1, le=10000),
               page_size: int = Query(24, ge=1, le=50), include_image: bool = False):
        try:
            result = cards.search(page=page, page_size=page_size, include_image=include_image,
                                  format='standard', legality='legal', category='Pokemon', game='tcg')
            ids = [card['id'] for card in result['cards']]
            with closing(cards.connect()) as db:
                stamps = {row['id']: row['checked_at'] for row in db.execute(
                    'SELECT id,checked_at FROM cards WHERE id IN (' + ','.join('?' for _ in ids) + ')', ids)} if ids else {}
            for card in result['cards']:
                base = card.pop('image', None)
                if include_image:
                    card['image_url'] = images.url({'image': base})
                card['legality_provenance'] = {'source': 'TCGdex', 'checked_at': stamps[card['id']]}
            return result
        except (sqlite3.Error, OSError, ValueError):
            raise unavailable() from None

    return app


app = create_app()
