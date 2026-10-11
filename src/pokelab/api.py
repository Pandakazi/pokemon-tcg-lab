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
from .research import Research
from .research_models import ResearchSummary, CardStatistics, EvidencePage, TournamentDeck, Composite
from .decks import Decks, DeckCommand, DeckConflict, ResearchCopy, deck_identity
from .images import TCGdexImages
from .library_identity import library_signature, basic_image_priority, REPRESENTATIVE_ORDER_SQL
from .variation_families import variation_members
from .web_models import LibraryQuery, CardPage, CardDetail, Status, Ownership, QuantityWrite, Preference, VariationPage, Category


def filter_options(cards, category):
    """Present source classifications; frontend never infers card taxonomy."""
    families = {'Pokemon': [('pokemon_types','Pokémon type','types'), ('stages','Stage','stage')],
                'Trainer': [('trainer_types','Trainer subtype','trainerType')],
                'Energy': [('energy_types','Energy classification','energyType')]}
    result = []
    with closing(cards.connect()) as db:
        for parameter, label, field in [*families[category], ('regulation_marks','Regulation mark','regulationMark'), ('illustrators','Illustrator','illustrator')]:
            # Paths come only from the fixed declarations above.
            scope = "c.game='tcg'" if parameter == 'illustrators' else "c.standard=1 AND c.game='tcg' AND c.category=?"
            values = [row[0] for row in db.execute(
                f"SELECT DISTINCT j.value FROM cards c,json_each(c.raw,?) j WHERE {scope} AND j.type='text' ORDER BY j.value",
                ('$.' + field,) if parameter == 'illustrators' else ('$.' + field, category))]
            if values:
                result.append({'parameter': parameter, 'label': label, 'values': values})
    return result


class ReadOnlyCards(SQLiteCards):
    """Use existing lookup semantics without creating or migrating a database."""
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.collection_snapshot = None
        self.ownership = 'all'
        self.exact_printings = False

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
        if self.exact_printings:
            return super()._search_page(db, where, params, page, page_size)
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
                    ORDER BY {REPRESENTATIVE_ORDER_SQL}) representative
                FROM eligible c LEFT JOIN sets s ON s.id=c.set_id)
            """
        total = db.execute(representatives + 'SELECT count(*) FROM ranked WHERE representative=1', params).fetchone()[0]
        rows = db.execute(representatives + 'SELECT raw,game FROM ranked WHERE representative=1 ORDER BY id LIMIT ? OFFSET ?',
                          [*params, page_size, (page - 1) * page_size]).fetchall()
        return total, rows


def create_app(database=None, state_database=None, competitive_database=None, format_start=None, deck_database=None):
    app = FastAPI(title='PokéLab API', version='0.1.0')
    cards = ReadOnlyCards(database or os.getenv('TCG_CARDS_DB_PATH', 'data/cards.sqlite3'))
    images = TCGdexImages()
    collection = Collection(cards, state_database or os.getenv('POKELAB_USER_DB_PATH') or cards.path.with_name('user-state.sqlite3'))
    competitive = Competitive(cards, competitive_database or os.getenv('POKELAB_COMPETITIVE_DB_PATH') or cards.path.with_name('competitive.sqlite3'),
                              format_start or os.getenv('POKELAB_FORMAT_START'))
    if competitive.path == collection.path:
        raise ValueError('Competitive storage must be separate from collection storage')
    decks = Decks(collection, deck_database or os.getenv('POKELAB_DECK_DB_PATH') or collection.path.with_name('deck-workspace.sqlite3'))
    if decks.path == competitive.path:
        raise ValueError('Deck storage must be separate from competitive storage')
    research = Research(competitive,collection)

    # Product research uses the certified provider boundary, never the benchmark
    # harness or legacy desktop Agent. Source adapters import lazily to avoid the
    # existing ReadOnlyCards composition cycle.
    from .agent_research import ResearchService, ResearchRequest, DEADLINE_SECONDS
    agent = ResearchService(dict(cards=cards.path, collection=collection.path,
        workspace=decks.path, competitive=competitive.path), competitive.format_start.isoformat() if competitive.format_start else None)
    app.state.research_agent = agent
    from .agent_settings import AgentSettings, ApplySettings
    app.state.agent_settings = AgentSettings()
    agent.settings = app.state.agent_settings
    from .competitive_sync import ManualCompetitiveSync
    app.state.competitive_sync=ManualCompetitiveSync(competitive)

    @app.get('/api/v1/competitive/sync')
    def competitive_sync_status():
        return app.state.competitive_sync.status()

    from .ptcgl_export import ExportRequest,ExportUnavailable,export_ptcgl

    @app.post('/api/v1/decks/export-ptcgl')
    def export_deck(request: ExportRequest):
        try:return export_ptcgl(cards,request)
        except ExportUnavailable as error:
            raise HTTPException(422,detail=str(error)) from None
        except (sqlite3.Error,OSError,ValueError):
            raise HTTPException(503,detail='Local export metadata is unavailable. Nothing was copied.') from None

    @app.post('/api/v1/competitive/sync')
    def competitive_manual_sync():
        from fastapi.responses import JSONResponse
        try:result=app.state.competitive_sync.run()
        except (OSError,sqlite3.Error,ValueError):
            return JSONResponse(status_code=503,content={'status':'failed','message':'Competitive data could not be refreshed. Previous data is still available.'})
        return JSONResponse(status_code=200 if result['status']=='complete' else 409 if result['status'] in ('cooldown','running') else 503,content=result)

    @app.get('/api/v1/agent/status')
    def agent_status():
        return app.state.research_agent.status()

    from starlette.requests import Request as HttpRequest

    async def settings_body(request):
        from urllib.parse import urlsplit
        # Guard Host as well as Origin (including DNS rebinding). No CORS.
        local = ('localhost', '127.0.0.1', '::1')
        origin = request.headers.get('origin')
        host = request.url.hostname
        if host not in local or request.headers.get('sec-fetch-site') == 'cross-site':
            raise HTTPException(403, detail='Settings require a local origin.')
        if origin:
            parsed = urlsplit(origin)
            if parsed.scheme not in ('http', 'https') or parsed.hostname != host or parsed.hostname not in local:
                raise HTTPException(403, detail='Settings require a same-host local origin.')
        if request.headers.get('content-type', '').split(';')[0] != 'application/json':
            raise HTTPException(415, detail='JSON required.')
        raw = b''
        async for chunk in request.stream():
            raw += chunk
            if len(raw) > 8192:
                raise HTTPException(413, detail='Settings request too large.')
        return raw

    @app.get('/api/v1/settings/agent')
    def settings_status():
        from fastapi.responses import JSONResponse
        return JSONResponse(app.state.agent_settings.status(app.state.research_agent), headers={'Cache-Control': 'no-store'})

    @app.post('/api/v1/settings/agent/test-apply')
    async def settings_apply(request: HttpRequest):
        import asyncio
        from pydantic import ValidationError
        from fastapi.responses import StreamingResponse
        raw = await settings_body(request)
        try:
            query = ApplySettings.model_validate_json(raw)
        except (ValidationError, ValueError):
            # Never echo a pasted secret through FastAPI validation diagnostics.
            raise HTTPException(422, detail='Choose one provider and enter a valid API key.') from None

        async def progress():
            loop = asyncio.get_running_loop()
            queue = asyncio.Queue()
            def worker():
                try:
                    for event in app.state.agent_settings.test_apply(query, transport=app.state.research_agent.transport):
                        loop.call_soon_threadsafe(queue.put_nowait, event)
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, None)
            # Keep the entire transaction in one worker/context. It retains the
            # shared flight lock even if the browser disconnects while waiting.
            task = asyncio.create_task(asyncio.to_thread(worker))
            try:
                while True:
                    event = await queue.get()
                    if event is None:
                        break
                    yield json.dumps(event) + '\n'
                await task
            finally:
                # Do not cancel a provider call or release its lock prematurely.
                task.add_done_callback(lambda finished: finished.exception() if not finished.cancelled() else None)
        return StreamingResponse(progress(), media_type='application/x-ndjson',
            headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})

    @app.post('/api/v1/settings/agent/disconnect')
    async def settings_disconnect(request: HttpRequest):
        from fastapi.responses import JSONResponse
        raw = await settings_body(request)
        if raw.strip() != b'{}':
            raise HTTPException(422, detail='Invalid disconnect request.')
        result = app.state.agent_settings.disconnect()
        return JSONResponse(result, status_code=200 if result['ok'] else 409, headers={'Cache-Control': 'no-store'})

    @app.post('/api/v1/agent/research')
    async def agent_research(request: HttpRequest):
        import asyncio
        from urllib.parse import urlsplit
        from pydantic import ValidationError
        # Local development uses a same-host Vite proxy. Never accept a remote
        # web origin or simple form submission that could trigger paid traffic.
        origin = request.headers.get('origin')
        if origin and (urlsplit(origin).hostname not in ('localhost', '127.0.0.1', '[::1]', '::1')
                       or urlsplit(origin).hostname != request.url.hostname):
            raise HTTPException(403, detail='Research requires a same-host local origin.')
        if request.headers.get('content-type', '').split(';')[0] != 'application/json':
            raise HTTPException(415, detail='JSON required.')
        raw = b''
        async for chunk in request.stream():
            raw += chunk
            if len(raw) > 8192:
                raise HTTPException(413, detail='Research request too large.')
        try:
            query = ResearchRequest.model_validate_json(raw)
            if not query.question.strip():
                raise ValueError()
        except (ValidationError, ValueError):
            # Do not echo invalid user input into framework validation responses.
            raise HTTPException(422, detail='Invalid research context or question.') from None
        try:
            # A timed-out worker retains its single-flight lock until transport
            # exits; timeout must never permit overlapping/retried inference.
            return await asyncio.wait_for(asyncio.to_thread(app.state.research_agent.run, query), DEADLINE_SECONDS)
        except TimeoutError:
            return dict(status='request_timeout', answer=None)

    def research_read(operation):
        try:
            return operation()
        except KeyError as error:
            raise HTTPException(404,detail=str(error)) from None
        except (sqlite3.Error,OSError,ValueError):
            raise HTTPException(503,detail='Local research evidence or card mapping is unavailable. Stored evidence is preserved.') from None

    @app.get('/api/v1/research/archetypes/{key}',response_model=ResearchSummary)
    def archetype_research(key:str,window:Literal['7','30','90','format']='30'):
        return research_read(lambda:research.selected(key,window)[0])

    @app.get('/api/v1/research/archetypes/{key}/cards',response_model=CardStatistics)
    def archetype_cards(key:str,window:Literal['7','30','90','format']='30'):
        return research_read(lambda:research.statistics(key,window))

    @app.get('/api/v1/research/archetypes/{key}/decks',response_model=EvidencePage)
    def archetype_decks(key:str,window:Literal['7','30','90','format']='30',page:int=Query(1,ge=1,le=10000),page_size:int=Query(20,ge=1,le=50),include_excluded:bool=False):
        return research_read(lambda:research.evidence_page(key,window,page,page_size,include_excluded))

    @app.get('/api/v1/research/archetypes/{key}/composite',response_model=Composite)
    def archetype_composite(key:str,window:Literal['7','30','90','format']='30'):
        return research_read(lambda:research.composite(key,window))

    @app.get('/api/v1/research/tournament-decks/{key}',response_model=TournamentDeck)
    def tournament_deck(key:str):
        return research_read(lambda:research.tournament_deck(key))

    @app.post('/api/v1/deck-workspace/copy-research')
    def copy_research(body: ResearchCopy):
        try:
            return decks.copy_research(body, research)
        except KeyError as error:
            raise HTTPException(404, detail=str(error)) from None
        except DeckConflict as error:
            raise HTTPException(409, detail=str(error)) from None
        except ValueError as error:
            raise HTTPException(422, detail=str(error)) from None
        except (sqlite3.Error, OSError):
            raise HTTPException(503, detail='Copy failed. Reload the active deck before retrying; no partial deck was created.') from None

    @app.get('/api/v1/deck-workspace')
    def deck_workspace():
        try:
            return decks.read()
        except (sqlite3.Error, OSError, ValueError):
            raise HTTPException(503, detail='Deck workspace or card cache unavailable. Your stored decks have been preserved.') from None

    @app.post('/api/v1/deck-workspace')
    def change_deck(body: DeckCommand):
        try:
            return decks.apply(body)
        except DeckConflict as error:
            raise HTTPException(409, detail=str(error)) from None
        except ValueError as error:
            raise HTTPException(422, detail=str(error)) from None
        except (sqlite3.Error, OSError):
            raise HTTPException(503, detail='Unable to save deck changes. Retry; your last stored draft is preserved.') from None

    @app.get('/api/v1/competitive/cards/{printing_id}', response_model=CompetitiveResearch)
    def competitive_card(printing_id: str, window: Literal['7','30','90','format']='30',
                         source: Literal['limitless-main']='limitless-main', trend: bool=True):
        # Resolve exact printing to the existing canonical functional identity.
        # Catalogue-only access: no collection initialization or upstream calls.
        try:
            catalog = collection.catalog()
            records = catalog[0]
            if printing_id not in records:
                raise HTTPException(404, detail='Exact printing not found')
            return competitive.stats(records[printing_id]['functional_id'],window,include_trend=trend,card_catalog=catalog)
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
        result['deck_identity'] = deck_identity(record)
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
    def variations(printing_id: str, scope: Literal['functional','library','deck','family']='functional',
                   page: int=Query(1,ge=1,le=10000), page_size: int=Query(24,ge=1,le=50)):
        snapshot = state(); require_printing(printing_id, snapshot)
        record = snapshot.records[printing_id]
        ids = (snapshot.functions[record['functional_id']] if scope == 'functional' else snapshot.libraries[record['library_id']])
        if scope == 'deck':
            key = deck_identity(record)
            ids = [id for id in ids if deck_identity(snapshot.records[id]) == key]
        elif scope == 'family':
            ids = variation_members(snapshot, printing_id)
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
    def owned_collection(category: Category | None=None, q: str=Query('',max_length=100), illustrators: list[str]=Query(default=[],max_length=26),
                         page: int=Query(1,ge=1,le=10000), page_size: int=Query(24,ge=1,le=50)):
        if any(len(name)>100 for name in illustrators):raise HTTPException(422,detail='Illustrator names must be at most 100 characters.')
        snapshot = state()
        pairs = [(id,v) for (id,v),n in sorted(snapshot.quantities.items()) if n>0 and id in snapshot.records
                 and (category is None or snapshot.records[id]['card']['category']==category)
                 and (not q.strip() or q.strip().casefold() in snapshot.records[id]['card']['name'].casefold() or q.strip().casefold() in snapshot.records[id]['card'].get('illustrator','').casefold() or q.strip()==id)
                 and (not illustrators or snapshot.records[id]['card'].get('illustrator') in illustrators)]
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
            if query.illustrators:
                # Artist discovery is an exact-printing catalog, independent of
                # the competitive Library's default legality/identity filters.
                browser.exact_printings = True
                browser.ownership = 'all'
                filters = {'illustrators': query.illustrators}
            else:
                filters.update(format='standard', legality='legal')
            result = browser.search(query.q, page=query.page, page_size=query.page_size, include_image=query.include_image,
                                  game='tcg', **filters)
            displayed=[]
            for card in result['cards']:
                printing,variant=(card['id'],snapshot.default_variant(card['id'])) if query.illustrators else snapshot.displayed(card['id'])
                displayed.append(owned_summary(snapshot,printing,variant,query.include_image))
            result['cards']=displayed
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
            record['card']['deck_identity'] = deck_identity(snapshot.records[printing_id])
            return record
        except (sqlite3.Error, OSError, ValueError):
            raise unavailable() from None

    return app


app = create_app()
