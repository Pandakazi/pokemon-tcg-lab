from contextlib import closing
from datetime import date, timedelta
import json
import hashlib
from pathlib import Path
import httpx
import pytest
from fastapi.testclient import TestClient
from pokelab.api import ReadOnlyCards, create_app
from pokelab.competitive import Competitive
from pokelab.collection import identity
from pokelab.engine import functional_signature
from pokelab.limitless_main import parse_index, parse_results, parse_decklists, SourceLayoutError, SOURCE
from pokelab.ingest_competitive import refresh
from tcg_lab.card_db import SQLiteCards
from test_card_data import card, set_record

FIX = Path(__file__).parent/'fixtures'/'limitless'
def fixture(name): return (FIX/(name+'.html')).read_text(encoding='utf-8')


def test_saved_real_markup():
    for page in json.loads((FIX/'provenance.json').read_text())['pages']:
        assert hashlib.sha256((FIX/page['file']).read_bytes()).hexdigest()==page['sha256']
    events, current, maximum = parse_index(fixture('index'))
    assert len(events)==25 and current==1 and maximum==22
    assert events[1]['id']=='577' and events[1]['format']=='standard'
    results = parse_results(fixture('results'))
    decks = parse_decklists(fixture('decklists'),results)
    assert len(results)==len(decks)==8
    assert decks[0]['archetype_name']=='Banette Gardevoir'
    assert decks[0]['list_url']=='https://limitlesstcg.com/decks/list/11798'
    assert decks[0]['cards'][0]==dict(set='SVI',number='87',name='Shuppet',count=4)
    assert all(sum(c['count'] for c in d['cards'])==60 for d in decks)


def test_shared_list_urls_are_distinct_result_entries():
    results=parse_results(fixture('results').replace('/decks/list/11799','/decks/list/11798'))
    assert results[1]['list_url']==results[2]['list_url']
    assert len(parse_decklists(fixture('decklists'),results))==8


def test_same_set_basic_energy_fallback_does_not_merge_identities(store):
    writable=SQLiteCards(store.cards.path)
    writable.put_set(set_record('other'))
    energy=card('sm2-5');energy.update(name='Psychic Energy',category='Energy',energyType='Normal')
    writable.put(energy)
    different={**energy,'id':'other-5','set':{'id':'other'},'effect':'different source wording'}
    writable.put(different)
    exact,names=store.resolver()
    assert len(names['psychic energy'])==2
    assert exact[('SM2','basic:psychic energy')]=={identity(functional_signature(energy))}


def test_remap_retains_fetch_provenance(store):
    seed(store)
    before=store.evidence()[0][0]['fetched_at']
    store.remap_cached()
    assert store.evidence()[0][0]['fetched_at']==before


@pytest.mark.parametrize('old,new', [('data-date=','changed='),('data-format=','changed='),('data-max=','changed='),('data-table','changed')])
def test_index_layout_failure(old,new):
    with pytest.raises(SourceLayoutError): parse_index(fixture('index').replace(old,new))


@pytest.mark.parametrize('old,new', [('data-rank=','changed='),('data-deck=','changed='),('data-table','changed')])
def test_results_layout_failure(old,new):
    with pytest.raises(SourceLayoutError): parse_results(fixture('results').replace(old,new))


@pytest.mark.parametrize('old,new', [('data-set=','changed='),('data-lang="en"','data-lang="jp"'),('card-count','changed'),('decklist-card','changed'),('tournament-decklists','changed'),('decklist-1','decklist-2')])
def test_decklist_layout_failure(old,new):
    with pytest.raises(SourceLayoutError): parse_decklists(fixture('decklists').replace(old,new),parse_results(fixture('results')))


@pytest.fixture
def store(tmp_path):
    cards=SQLiteCards(tmp_path/'cards.sqlite3');cards.put_set(set_record())
    for n in range(3):
        c=card(f'sm2-{n}');c['name']=f'Card {n}';c['legal']['standard']=True;cards.put(c)
    return Competitive(ReadOnlyCards(cards.path),tmp_path/'competitive.sqlite3','2026-01-01')


def seed(store,n=100,a=20,day='2026-09-20',event_id='1',archetype='deck-a',unmapped=0):
    resolver=({('T','1'):{'A'},('T','2'):{'B'},('T','3'):{'C'}},{})
    decks=[]
    for i in range(n+unmapped):
        cs=[dict(set='T',number='2',name='B',count=56),dict(set='T',number='1' if i<a else '3',name='A' if i<a else 'C',count=4)]
        if i>=n: cs[0]['number']='404'
        decks.append(dict(rank=i+1,player=str(i),archetype_id=archetype,archetype_name=archetype,list_url=f'https://limitlesstcg.com/decks/list/{i+1}',cards=cs))
    store.import_event(dict(id=event_id,date=day,format='standard',name='Test',url=f'https://limitlesstcg.com/tournaments/{event_id}'),decks,n+unmapped+10,{'fixture':'html'},resolver)


def test_denominators_and_distribution(store):
    seed(store,unmapped=7)
    result=store.stats('A',today=date(2026,9,24))
    assert result['sample_size']==100 and result['included_decks']==20
    assert result['usage_percent']==20 and result['average_copies']==4
    assert result['copy_distribution'][-1]==dict(copies='4x+',decks=20,percent=100)
    assert result['excluded_unmapped']==7 and result['results_without_lists']==10
    archetype=result['archetypes'][0]
    assert archetype['share_percent']==100 and archetype['prevalence_percent']==20
    partner=result['associated_cards'][0]
    assert partner['cooccurrence_percent']==100 and partner['field_percent']==100 and partner['lift']==1


@pytest.mark.parametrize('n,status,pct',[(14,'insufficient_sample',None),(15,'observed',20)])
def test_archetype_threshold(store,n,status,pct):
    seed(store,n=n,a=3)
    r=store.stats('A',today=date(2026,9,24))
    assert r['archetypes'][0]['status']==status
    assert r['archetypes'][0]['prevalence_percent']==pct
    assert r['usage_percent'] is not None


def test_rare_card_is_observed_not_sample_gated(store):
    seed(store,n=5000,a=14)
    assert store.stats('A',today=date(2026,9,24))['usage_percent']==.28
    seed(store,n=734,a=3)
    assert store.stats('A',today=date(2026,9,24))['usage_percent']==round(300/734,4)


def test_observed_zero_and_no_data_and_mapping_failure(store):
    assert store.stats('A',today=date(2026,9,24))['status']=='no_data'
    seed(store,n=0,a=0,unmapped=2)
    assert store.stats('A',today=date(2026,9,24))['status']=='mapping_failure'
    seed(store)
    r=store.stats('D',today=date(2026,9,24))
    assert r['status']=='observed' and r['usage_percent']==0 and r['average_copies'] is None


def test_source_failure_preserves_evidence(store):
    store.record_status('layout changed')
    assert store.stats('A')['status']=='source_failure'
    seed(store)
    result=store.stats('A',today=date(2026,9,24))
    assert result['status']=='observed' and result['source_error']=='layout changed'


def test_source_separation_and_atomic_idempotence(store):
    seed(store);seed(store)
    with closing(store.connect(True)) as db,db:
        db.execute("INSERT INTO competitive_events SELECT 'play-limitless',id,date,raw,fetched_at,results,published FROM competitive_events")
        db.execute("INSERT INTO competitive_decks SELECT 'play-limitless',event_id,rank,resolved,raw,cards FROM competitive_decks")
    result=store.stats('A',today=date(2026,9,24))
    assert result['sample_size']==100 and result['tournament_count']==1
    with pytest.raises(ValueError): store.import_event(dict(id='1',format='standard',date='2026-09-20'),[dict(rank=1,cards=[dict(count=3)])],1,{})
    assert store.stats('A',today=date(2026,9,24))['sample_size']==100


def test_four_trends_and_calendar_boundaries(store):
    seed(store,n=100,a=20,day='2026-09-18')
    seed(store,n=100,a=80,day='2026-09-11',event_id='2')
    seed(store,n=100,a=0,day='2026-08-25',event_id='3')
    result=store.stats('A','7',today=date(2026,9,24))
    assert result['usage_percent']==20  # inclusive 18th through 24th
    assert [s['window'] for s in result['trend']]==['7','30','90','format']
    assert result['trend']==store.stats('A','90',today=date(2026,9,24))['trend']
    last={s['window']:s['points'][-1] for s in result['trend']}
    assert last['7']['sample_size']==100 and last['30']['sample_size']==300
    store.format_start=date(2026,9,15)
    fmt=store.stats('A','format',today=date(2026,9,24))
    assert fmt['sample_size']==100 and fmt['trend'][-1]['points'][0]['usage_percent']==20
    assert fmt['trend_start']=='2026-09-15' and fmt['trend_end']=='2026-09-24'
    store.format_start=None
    assert store.stats('A','format')['status']=='format_unavailable'
    assert store.stats('A')['trend'][-1]['available'] is False


def test_format_trend_includes_older_evidence_without_synthetic_dates(store):
    seed(store,day='2026-02-01',event_id='old')
    seed(store,day='2026-08-28',event_id='worlds')
    seed(store,day='2026-09-19',event_id='baltimore')
    result=store.stats('A','7',today=date(2026,9,24))
    assert result['trend_start']=='2026-01-01' and result['trend_end']=='2026-09-24'
    assert all([p['date'] for p in s['points']]==['2026-02-01','2026-08-28','2026-09-19'] for s in result['trend'])
    assert result['trend']==store.stats('A','30',today=date(2026,9,24))['trend']
    store.format_start=None
    no_format=store.stats('A',today=date(2026,9,24))
    assert (no_format['trend_start'],no_format['trend_end'])==('2026-08-28','2026-09-19')
    assert all([p['date'] for p in s['points']]==['2026-08-28','2026-09-19'] for s in no_format['trend'])
    assert no_format['trend'][-1]['available'] is False
    store.format_start=date(2027,1,1)
    assert store.stats('A',today=date(2026,9,24))['trend_start']=='2026-08-28'


def test_associated_card_preview_uses_existing_functional_identity_and_safe_image(store,monkeypatch):
    seed(store)
    fid=identity(functional_signature(card_with_name()))
    with closing(store.connect(True)) as db,db:
        for row in db.execute('SELECT rank,cards FROM competitive_decks').fetchall():
            cards=json.loads(row['cards']);cards[fid]=cards.pop('B')
            db.execute('UPDATE competitive_decks SET cards=? WHERE rank=?',(json.dumps(cards),row['rank']))
    monkeypatch.setattr(httpx.HTTPTransport,'handle_request',lambda *a,**k:pytest.fail('Unexpected preview fetch'))
    partner=store.stats('A',today=date(2026,9,24))['associated_cards'][0]
    assert partner['printing_id']=='sm2-0'
    assert partner['image_url']=='https://assets.tcgdex.net/en/sm/sm2/59/high.webp'
    assert partner['lift']==1 and partner['decks']==20
    raw=card_with_name();raw['image']='https://evil.invalid/image';SQLiteCards(store.cards.path).put(raw)
    assert store.stats('A',today=date(2026,9,24))['associated_cards'][0]['image_url'] is None


def test_top_five_and_deterministic_ties(store):
    for i in range(7): seed(store,n=100,a=20,event_id=str(i),archetype=f'deck-{i}')
    assert [a['id'] for a in store.stats('A',today=date(2026,9,24))['top_archetypes']]==[f'deck-{i}' for i in range(5)]


def test_meaningful_association_ranks_above_staple(store):
    seed(store)
    with closing(store.connect(True)) as db, db:
        for row in db.execute('SELECT rank,cards FROM competitive_decks').fetchall():
            cards=json.loads(row['cards'])
            if 'A' in cards: cards.update(C=1,B=55)
            else: cards=dict(B=60)
            db.execute('UPDATE competitive_decks SET cards=? WHERE rank=?',(json.dumps(cards),row['rank']))
    partners=store.stats('A',today=date(2026,9,24))['associated_cards']
    assert [p['functional_id'] for p in partners]==['C','B']
    assert partners[0]['lift']==5 and partners[1]['lift']==1


def test_api_is_local_source_aware_and_reuses_identity(store,monkeypatch):
    monkeypatch.setattr(httpx.HTTPTransport,'handle_request',lambda *a,**k:pytest.fail('upstream request'))
    before=store.cards.path.read_bytes()
    client=TestClient(create_app(store.cards.path,competitive_database=store.path))
    r=client.get('/api/v1/competitive/cards/sm2-0').json()
    assert r['window']=='30' and r['source']==SOURCE and r['status']=='no_data'
    assert r['functional_id']==identity(functional_signature(card_with_name()))
    assert client.get('/api/v1/competitive/cards/sm2-0?source=play-limitless').status_code==422
    assert client.get('/api/v1/competitive/cards/sm2-0?window=60').status_code==422
    assert client.get('/api/v1/competitive/cards/missing').status_code==404
    assert store.cards.path.read_bytes()==before
    assert not store.path.exists()  # GET does not initialize/write evidence


def card_with_name():
    c=card('sm2-0');c['name']='Card 0';c['legal']['standard']=True;return c


def test_refresh_offline_and_failure_keeps_cache(store):
    # Real saved pages with a synthetic recent index date and event ID.
    day=date.today().isoformat()
    index=fixture('index')
    # Keep one structurally representative row, parsed metadata for 441.
    import re
    rows=re.findall(r'<tr data-date=.*?</tr>',index,re.S)
    row=rows[1].replace('577','441')
    row=re.sub(r'data-date="[^"]+"',f'data-date="{day}"',row)
    index=re.sub(r'<tr data-date=.*?</tr>',lambda m:row if m.group()==rows[1] else '',index,flags=re.S)
    pages={'/tournaments':index,'/tournaments/441':fixture('results'),'/tournaments/441/decklists':fixture('decklists')}
    client=httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(200,headers={'content-type':'text/html'},text=pages[request.url.path])))
    report=refresh(store,client=client,delay=0,max_events=1,progress=lambda _:None)
    assert report['published']==8
    pages['/tournaments/441/decklists']='<html>layout changed</html>'
    with pytest.raises(SourceLayoutError): refresh(store,client=client,delay=0,max_events=1,progress=lambda _:None)
    assert len(store.evidence()[1])==8 and store.evidence()[2]['error']
