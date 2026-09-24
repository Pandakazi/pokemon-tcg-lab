"""Read-only web adapter. No MCP, Qt, synchronization or provider dependency."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query

from tcg_lab.card_db import SQLiteCards
from tcg_lab.cards import CardLookupError, check_id, public_card
from .images import TCGdexImages
from .library_identity import library_signature, basic_image_priority
from .web_models import LibraryQuery, CardPage, CardDetail, Status


def filter_options(cards, category):
    """Present source classifications; frontend never infers card taxonomy."""
    families = {'Pokemon': [('pokemon_types','Pokémon type','types'), ('stages','Stage','stage')],
                'Trainer': [('trainer_types','Trainer subtype','trainerType')],
                'Energy': [('energy_types','Energy classification','energyType')]}
    result = []
    with closing(cards.connect()) as db:
        for parameter, label, field in [*families[category], ('regulation_marks','Regulation mark','regulationMark')]:
            # Paths come only from the fixed declarations above.
            values = [row[0] for row in db.execute(
                "SELECT DISTINCT j.value FROM cards c,json_each(c.raw,?) j WHERE c.standard=1 AND c.game='tcg' AND c.category=? AND j.type='text' ORDER BY j.value",
                ('$.' + field, category))]
            if values:
                result.append({'parameter': parameter, 'label': label, 'values': values})
    return result


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

    def _search_page(self, db, where, params, page, page_size):
        """One newest eligible printing per conservative engine identity.

        Filter first so a mark-specific search can select that printing. Group and
        count before pagination. Missing release dates sort last; regulation and
        exact ID break release-date ties. No identity tables or cache writes needed.
        MCP keeps the base service's exact-printing search contract.
        """
        db.create_function('functional_identity', 1,
                           lambda raw: library_signature(json.loads(raw)), deterministic=True)
        db.create_function('basic_image_priority', 1,
                           lambda raw: basic_image_priority(json.loads(raw)), deterministic=True)
        representatives = f"""WITH eligible AS (SELECT * FROM cards WHERE {where}),
            ranked AS (
                SELECT c.raw,c.game,c.id,ROW_NUMBER() OVER (
                    PARTITION BY functional_identity(c.raw)
                    ORDER BY basic_image_priority(c.raw) DESC,
                             COALESCE(json_extract(s.raw,'$.releaseDate'),'') DESC,
                             COALESCE(c.regulation,'') DESC,c.id DESC) representative
                FROM eligible c LEFT JOIN sets s ON s.id=c.set_id)
            """
        total = db.execute(representatives + 'SELECT count(*) FROM ranked WHERE representative=1', params).fetchone()[0]
        rows = db.execute(representatives + 'SELECT raw,game FROM ranked WHERE representative=1 ORDER BY id LIMIT ? OFFSET ?',
                          [*params, page_size, (page - 1) * page_size]).fetchall()
        return total, rows


def create_app(database=None):
    app = FastAPI(title='PokéLab API', version='0.1.0')
    cards = ReadOnlyCards(database or os.getenv('TCG_CARDS_DB_PATH', 'data/cards.sqlite3'))
    images = TCGdexImages()

    def unavailable():
        return HTTPException(503, detail={'code': 'card_cache_unavailable',
            'message': 'The local card database is unavailable. Initialize it with python -m tcg_lab.sync_cards, then retry.'})

    @app.get('/api/v1/status', response_model=Status, response_model_exclude_unset=True)
    def status():
        try:
            result = cards.status()
            if not result['cards']:
                raise CardLookupError('Empty cache')
            sync = result.get('last_sync') or {'status': 'not_completed'}
            return {'app': 'PokéLab', 'ready': True, 'source': 'TCGdex SQLite',
                    'cards': result['cards'], 'sync': {key: sync[key] for key in ('status', 'finished_at', 'missing') if key in sync}}
        except (sqlite3.Error, OSError, ValueError):
            raise unavailable() from None

    @app.get('/api/v1/cards', response_model=CardPage, response_model_exclude_unset=True)
    def browse(query: Annotated[LibraryQuery, Query()]):
        try:
            filters = query.model_dump(exclude={'q', 'page', 'page_size', 'include_image', 'has_ability'})
            result = cards.search(query.q, page=query.page, page_size=query.page_size, include_image=query.include_image,
                                  format='standard', legality='legal', game='tcg', **filters)
            ids = [card['id'] for card in result['cards']]
            with closing(cards.connect()) as db:
                stamps = {row['id']: row['checked_at'] for row in db.execute(
                    'SELECT id,checked_at FROM cards WHERE id IN (' + ','.join('?' for _ in ids) + ')', ids)} if ids else {}
            for card in result['cards']:
                base = card.pop('image', None)
                if query.include_image:
                    card['image_url'] = images.url({'image': base})
                card['legality_provenance'] = {'source': 'TCGdex', 'checked_at': stamps[card['id']]}
            result['filter_options'] = filter_options(cards, query.category)
            return result
        except (sqlite3.Error, OSError, ValueError):
            raise unavailable() from None

    @app.get('/api/v1/cards/{printing_id}', response_model=CardDetail, response_model_exclude_unset=True)
    def detail(printing_id: str, include_image: bool = False):
        try:
            check_id(printing_id)
        except CardLookupError:
            raise HTTPException(422, detail={'code': 'invalid_printing_id', 'message': 'Use an exact printing ID.'}) from None
        try:
            with closing(cards.connect()) as db:
                cards._ready(db)
                if not db.execute('SELECT 1 FROM cards WHERE id=?', (printing_id,)).fetchone():
                    raise HTTPException(404, detail={'code': 'card_not_found', 'message': 'This exact printing is not in the local database.'})
            record = cards.get(printing_id, include_image=True)
            image = images.url(record['card'], large=True)
            record['card'] = public_card(record['card'], False)
            if include_image:
                record['card']['image_url'] = image
            record['card']['legality_provenance'] = {'source': 'TCGdex', 'checked_at': record['checked_at']}
            return record
        except (sqlite3.Error, OSError, ValueError):
            raise unavailable() from None

    return app


app = create_app()
