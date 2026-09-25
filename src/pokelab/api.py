"""Read-only card adapter plus isolated local collection writes. No MCP/Qt dependency."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query

from tcg_lab.card_db import SQLiteCards
from tcg_lab.cards import CardLookupError, check_id, public_card, summary
from .collection import Collection, identity
from .competitive import Competitive
from .competitive_models import CompetitiveResearch
from .images import TCGdexImages
from .library_identity import library_signature, basic_image_priority
from .web_models import LibraryQuery, CardPage, CardDetail, Status, Ownership, QuantityWrite, Preference, VariationPage, Category


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
        self.collection_snapshot = None
        self.ownership = 'all'

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
        if self.collection_snapshot is not None and self.ownership != 'all':
            totals = self.collection_snapshot.library_totals
            db.create_function('library_owned', 1, lambda raw: totals.get(identity(library_signature(json.loads(raw))),0), deterministic=True)
            where += ' AND library_owned(raw)' + ('>0' if self.ownership == 'owned' else '=0')
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


def create_app(database=None, state_database=None, competitive_database=None, format_start=None):
    app = FastAPI(title='PokéLab API', version='0.1.0')
    cards = ReadOnlyCards(database or os.getenv('TCG_CARDS_DB_PATH', 'data/cards.sqlite3'))
    images = TCGdexImages()
    collection = Collection(cards, state_database or os.getenv('POKELAB_USER_DB_PATH') or cards.path.with_name('user-state.sqlite3'))
    competitive = Competitive(cards, competitive_database or os.getenv('POKELAB_COMPETITIVE_DB_PATH') or cards.path.with_name('competitive.sqlite3'),
                              format_start or os.getenv('POKELAB_FORMAT_START'))
    if competitive.path == collection.path:
        raise ValueError('Competitive storage must be separate from collection storage')

    @app.get('/api/v1/competitive/cards/{printing_id}', response_model=CompetitiveResearch)
    def competitive_card(printing_id: str, window: Literal['7','30','90','format']='30',
                         source: Literal['limitless-main']='limitless-main', trend: bool=True):
        # Resolve exact printing to the existing canonical functional identity.
        # Catalogue-only access: no collection initialization or upstream calls.
        try:
            records, _, _ = collection.catalog()
            if printing_id not in records:
                raise HTTPException(404, detail='Exact printing not found')
            return competitive.stats(records[printing_id]['functional_id'],window,include_trend=trend)
        except (sqlite3.Error, OSError, ValueError):
            raise HTTPException(503, detail={'code':'competitive_unavailable','message':'Competitive mapping or evidence storage is unavailable.'}) from None

    def state():
        try:
            collection.catalog()
        except (sqlite3.Error, OSError, ValueError):
            raise unavailable() from None
        try:
            return collection.snapshot()
        except (sqlite3.Error, OSError, ValueError):
            raise HTTPException(503, detail={'code':'user_state_unavailable', 'message':'Card cache or local collection storage is unavailable. Check database paths and permissions.'}) from None

    def require_printing(id, snapshot):
        try:
            check_id(id)
        except ValueError:
            raise HTTPException(422, detail='Use an exact printing ID.') from None
        if id not in snapshot.records:
            raise HTTPException(404, detail='Exact printing not found.')

    def owned_summary(snapshot, id, variant, include_image=True):
        record = snapshot.records[id]
        result = summary(record['card'], False)
        result['game'] = record['game']
        result['legality_provenance'] = {'source':'TCGdex', 'checked_at':record['checked_at']}
        result['ownership'] = snapshot.ownership(id, variant)
        if include_image:
            result['image_url'] = images.url(record['card'])
        return result

    @app.get('/api/v1/cards/{printing_id}/ownership', response_model=Ownership)
    def ownership(printing_id: str, variant: str = Query('unspecified', min_length=1, max_length=100)):
        snapshot = state(); require_printing(printing_id, snapshot)
        try:
            snapshot.validate_variant(printing_id, variant)
            return snapshot.ownership(printing_id, variant)
        except ValueError as error:
            raise HTTPException(422, detail=str(error)) from None

    @app.put('/api/v1/collection/{printing_id}', response_model=Ownership)
    def set_quantity(printing_id: str, body: QuantityWrite):
        snapshot = state(); require_printing(printing_id, snapshot)
        try:
            return collection.update(printing_id, **body.model_dump())
        except ValueError as error:
            raise HTTPException(422, detail=str(error)) from None
        except (sqlite3.Error, OSError):
            raise HTTPException(503, detail='Unable to save local collection.') from None

    @app.get('/api/v1/library/{printing_id}/preference', response_model=Preference)
    def preference(printing_id: str):
        snapshot = state(); require_printing(printing_id, snapshot)
        id, variant = snapshot.displayed(printing_id)
        return {'printing_id':id, 'variant':variant}

    @app.put('/api/v1/library/{printing_id}/preference', response_model=Preference)
    def set_preference(printing_id: str, body: Preference):
        snapshot = state(); require_printing(printing_id, snapshot); require_printing(body.printing_id, snapshot)
        try:
            return collection.prefer(printing_id, body.printing_id, body.variant)
        except ValueError as error:
            raise HTTPException(422, detail=str(error)) from None
        except (sqlite3.Error, OSError):
            raise HTTPException(503, detail='Unable to save Library preference.') from None

    @app.get('/api/v1/cards/{printing_id}/variations', response_model=VariationPage, response_model_exclude_unset=True)
    def variations(printing_id: str, scope: Literal['functional','library']='functional',
                   page: int=Query(1,ge=1,le=10000), page_size: int=Query(24,ge=1,le=50)):
        snapshot = state(); require_printing(printing_id, snapshot)
        record = snapshot.records[printing_id]
        ids = (snapshot.functions[record['functional_id']] if scope == 'functional' else snapshot.libraries[record['library_id']])
        pairs = [(id,v) for id in sorted(ids) for v in snapshot.presentation_variants(id)]
        result = variation_page(snapshot, pairs, page, page_size)
        page_ids = dict.fromkeys(id for id,_ in pairs[(page-1)*page_size:page*page_size])
        result['unassigned'] = [owned_summary(snapshot,id,'unspecified') for id in page_ids
                                if 'unspecified' not in snapshot.presentation_variants(id)
                                and snapshot.quantities.get((id,'unspecified'),0)>0]
        return result

    def variation_page(snapshot, pairs, page, page_size):
        return {'cards':[owned_summary(snapshot,id,v) for id,v in pairs[(page-1)*page_size:page*page_size]],
                'total':len(pairs), 'page':page, 'page_size':page_size,
                'next_page':page+1 if page*page_size<len(pairs) else None}

    @app.get('/api/v1/collection', response_model=VariationPage, response_model_exclude_unset=True)
    def owned_collection(category: Category | None=None, q: str=Query('',max_length=100),
                         page: int=Query(1,ge=1,le=10000), page_size: int=Query(24,ge=1,le=50)):
        snapshot = state()
        pairs = [(id,v) for (id,v),n in sorted(snapshot.quantities.items()) if n>0 and id in snapshot.records
                 and (category is None or snapshot.records[id]['card']['category']==category)
                 and (not q.strip() or q.strip().casefold() in snapshot.records[id]['card']['name'].casefold() or q.strip()==id)]
        return variation_page(snapshot, pairs, page, page_size)

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
            snapshot = state()
            browser = ReadOnlyCards(cards.path)
            browser.collection_snapshot, browser.ownership = snapshot, query.ownership
            filters = query.model_dump(exclude={'q', 'page', 'page_size', 'include_image', 'has_ability', 'ownership'})
            result = browser.search(query.q, page=query.page, page_size=query.page_size, include_image=query.include_image,
                                  format='standard', legality='legal', game='tcg', **filters)
            result['cards'] = [owned_summary(snapshot, *snapshot.displayed(card['id']), query.include_image) for card in result['cards']]
            result['filter_options'] = filter_options(cards, query.category)
            return result
        except (sqlite3.Error, OSError, ValueError):
            raise unavailable() from None

    @app.get('/api/v1/cards/{printing_id}', response_model=CardDetail, response_model_exclude_unset=True)
    def detail(printing_id: str, include_image: bool = False, variant: str | None=Query(None,min_length=1,max_length=100)):
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
            snapshot = state()
            if variant is None:
                variant = ('unspecified' if snapshot.quantities.get((printing_id,'unspecified'),0)>0
                           else snapshot.default_variant(printing_id))
            try:
                snapshot.validate_variant(printing_id, variant)
            except ValueError as error:
                raise HTTPException(422, detail=str(error)) from None
            record['card']['ownership'] = snapshot.ownership(printing_id, variant)
            return record
        except (sqlite3.Error, OSError, ValueError):
            raise unavailable() from None

    return app


app = create_app()
