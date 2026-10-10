from datetime import datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import json
import httpx
from fastapi.testclient import TestClient
from pokelab.api import create_app
from pokelab.competitive_sync import ManualCompetitiveSync
from test_competitive import store,fixture,seed
from test_collection_api import setup,change


def test_manual_sync_existing_importer_success_cooldown_restart_and_failure(store,monkeypatch):
    from pokelab import ingest_competitive
    before=store.cards.path.read_bytes();now=[datetime(2026,10,10,tzinfo=timezone.utc)]
    def handle(request):
        path=request.url.path
        return httpx.Response(200,headers={'content-type':'text/html'},text=fixture('index' if path=='/tournaments' else 'decklists' if path.endswith('/decklists') else 'results'))
    client=httpx.Client(transport=httpx.MockTransport(handle))
    actual=ingest_competitive.refresh;calls=[]
    def bounded_refresh(s,**kwargs):
        calls.append(kwargs)
        return actual(s,client=client,delay=0,max_events=1,progress=lambda _:None)
    monkeypatch.setattr(ingest_competitive,'refresh',bounded_refresh)
    app=create_app(store.cards.path,competitive_database=store.path)
    sync=app.state.competitive_sync;sync.clock=lambda:now[0]
    api=TestClient(app)
    assert api.get('/api/v1/competitive/sync').json()['status']=='ready'
    r=api.post('/api/v1/competitive/sync');assert r.status_code==200,r.text
    success=r.json()['manual_success_at']
    assert r.json()['status']=='complete' and r.json()['retry_after_seconds']==3600
    assert len(calls)==1 and calls[0]['days']==90 and calls[0]['max_events']==25
    assert store.evidence()[0] and store.cards.path.read_bytes()==before
    restarted=create_app(store.cards.path,competitive_database=store.path)
    restarted.state.competitive_sync.clock=lambda:now[0]
    assert TestClient(restarted).post('/api/v1/competitive/sync').status_code==409
    assert len(calls)==1
    now[0]+=timedelta(hours=1)
    def fail(s,**kwargs):raise ValueError('private importer details must not be returned')
    monkeypatch.setattr(ingest_competitive,'refresh',fail)
    failed=api.post('/api/v1/competitive/sync')
    assert failed.status_code==503 and failed.json()['status']=='failed'
    assert failed.json()['manual_success_at']==success and failed.json()['last_successful_at']==success
    assert 'private' not in failed.text and api.get('/api/v1/competitive/sync').json()['status']=='ready'
    assert store.evidence()[0] and store.cards.path.read_bytes()==before


def test_sync_single_flight_across_instances(store):
    entered=Event();release=Event()
    def runner(s):entered.set();assert release.wait(10)
    sync=ManualCompetitiveSync(store,runner=runner)
    with ThreadPoolExecutor() as pool:
        future=pool.submit(sync.run);assert entered.wait(10)
        other=ManualCompetitiveSync(store,runner=lambda _:(_ for _ in ()).throw(AssertionError('duplicate refresh')))
        assert other.run()['status']=='running'
        release.set();assert future.result()['status']=='complete'


def test_first_manual_failure_after_partial_import_preserves_prior_freshness(store):
    seed(store)
    prior=ManualCompetitiveSync(store).status()['last_successful_at']
    def partial_failure(s):
        with s.connect(True) as db:db.execute("UPDATE competitive_events SET fetched_at='2026-10-10T20:00:00+00:00'")
        raise ValueError('partially imported before failing')
    result=ManualCompetitiveSync(store,runner=partial_failure).run()
    assert result['status']=='failed' and result['last_successful_at']==prior
    assert result['manual_success_at'] is None and result['retry_after_seconds']==0


def test_illustrator_search_filter_and_preferred_printing_cannot_escape_filter(setup):
    db,_,api=setup
    for id,artist in [('sm2-1','Atsushi Furusawa'),('sm2-2','Other Artist'),('sm2-3','Other Artist')]:
        r=db.get(id)['card'];r['illustrator']=artist;db.put(r)
    change(api,id='sm2-1',quantity=1);change(api,id='sm2-2',quantity=2)
    assert api.put('/api/v1/library/sm2-1/preference',json={'printing_id':'sm2-2','variant':'normal'}).status_code==200
    before=db.path.read_bytes()
    filtered=api.get('/api/v1/cards',params={'illustrators':'Atsushi Furusawa'}).json()
    assert [c['id'] for c in filtered['cards']]==['sm2-1']
    assert filtered['cards'][0]['illustrator']=='Atsushi Furusawa'
    assert any(o['parameter']=='illustrators' and 'Atsushi Furusawa' in o['values'] for o in filtered['filter_options'])
    assert api.get('/api/v1/cards',params={'q':'atsushi'}).json()['total']==1
    collection=api.get('/api/v1/collection',params={'illustrators':'Atsushi Furusawa'}).json()
    assert [c['id'] for c in collection['cards']]==['sm2-1']
    assert api.get('/api/v1/collection',params={'q':'atsushi'}).json()['total']==1
    assert api.get('/api/v1/collection').json()['total']==2
    assert api.get('/api/v1/cards',params={'illustrators':"' OR 1=1 --"}).json()['total']==0
    assert api.get('/api/v1/cards',params={'illustrators':'x'*101}).status_code==422
    assert api.get('/api/v1/collection',params={'illustrators':'x'*101}).status_code==422
    assert db.path.read_bytes()==before


def test_illustrator_catalog_keeps_every_printing_across_formats_categories_and_ownership(setup):
    from test_card_data import card,set_record
    db,_,api=setup
    db.put_set(set_record('old'))
    for id in ('sm2-1','sm2-2'):
        r=db.get(id)['card'];r['illustrator']='Mashu';db.put(r)
    old=card('old-1','Same playable card');old['illustrator']='Mashu';db.put(old)
    trainer=card('old-2','Historical trainer');trainer.update(category='Trainer',illustrator='Mashu',trainerType='Item');db.put(trainer)
    energy=card('old-3','Historical energy');energy.update(category='Energy',illustrator='Mashu',energyType='Normal');db.put(energy)
    change(api,id='sm2-1',quantity=1)
    assert api.put('/api/v1/library/sm2-1/preference',json={'printing_id':'sm2-2','variant':'normal'}).status_code==200
    before=db.path.read_bytes()
    # Stale competitive/category/ownership URL constraints cannot narrow artist discovery.
    result=api.get('/api/v1/cards',params={'illustrators':'Mashu','ownership':'owned','category':'Pokemon','regulation_marks':'Z','stages':'Stage2','page_size':2}).json()
    assert result['total']==5 and result['next_page']==2
    ids=[]
    for page in (1,2,3):
        ids.extend(c['id'] for c in api.get('/api/v1/cards',params={'illustrators':'Mashu','page_size':2,'page':page}).json()['cards'])
    assert ids==['old-1','old-2','old-3','sm2-1','sm2-2']
    assert db.path.read_bytes()==before
