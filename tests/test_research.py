from contextlib import closing
from datetime import date, timedelta
import json

import pytest
from fastapi.testclient import TestClient
from pokelab.api import ReadOnlyCards, create_app
from pokelab.collection import Collection, identity
from pokelab.competitive import Competitive
from pokelab.decks import DeckProvider, deck_identity
from pokelab.engine import functional_signature
from pokelab.research import Research
from pokelab.research_identity import archetype_key, evidence_key
from tcg_lab.card_db import SQLiteCards
from tcg_lab.models import Deck, DeckEntry
from tcg_lab.service import Lab
from test_card_data import card, set_record

TODAY=date(2026,9,25)
KEY=archetype_key('/decks/284?variant=3')


@pytest.fixture
def research(tmp_path):
    cards=SQLiteCards(tmp_path/'cards.sqlite3');cards.put_set(set_record())
    for n in (1,2):
        raw=card(f'sm2-{n}',f'Basic {n}');raw['legal']['standard']=True;cards.put(raw)
    energy=dict(id='sm2-3',localId='3',name='Water Energy',category='Energy',energyType='Normal',set={'id':'sm2'},rarity='Common',legal={'standard':True},variants={'normal':True})
    cards.put(energy)
    collection=Collection(ReadOnlyCards(cards.path),tmp_path/'user-state.sqlite3')
    collection.snapshot()
    competitive=Competitive(collection.cards,tmp_path/'competitive.sqlite3')
    return Research(competitive,collection)


def seed(research, quantities=(4,3,1,4), *, day=TODAY, event='1', unmapped=0, archetype='/decks/284?variant=3'):
    decks=[]
    for i,q in enumerate([*quantities,*([1]*unmapped)]):
        cards=[dict(set='GRI',number='1',name='Basic 1',count=q),dict(set='GRI',number='3' if i<len(quantities) else '999',name='Water Energy' if i<len(quantities) else 'Unmapped',count=60-q)]
        decks.append(dict(rank=i+1,player=f'Player {i+1}',archetype_id=archetype,archetype_name='Fixture Archetype',list_url='https://limitlesstcg.com/decks/list/1',cards=cards))
    research.competitive.import_event(dict(id=event,date=day.isoformat(),name=f'Event {event}',format='standard',url=f'https://limitlesstcg.com/tournaments/{event}'),decks,len(decks)+2,{'https://limitlesstcg.com/tournaments/1/decklists':'fixture'})


@pytest.mark.parametrize('n',[1,4,14,15,20])
def test_confidence_is_not_discovery_wall(research,n):
    seed(research,[1]*n)
    header,_,_=research.selected(KEY,today=TODAY)
    assert header['eligible_decks']==n
    assert header['status']==('observed' if n>=15 else 'limited_evidence')
    stats=research.statistics(KEY,today=TODAY)['cards']
    assert all(c['included_decks']==n for c in stats)
    assert all(c['inclusion_percent']==(100 if n>=15 else None) for c in stats)
    evidence=research.evidence_page(KEY,today=TODAY)
    assert evidence['total']==n and len(evidence['decks'])==n
    composite=research.composite(KEY,today=TODAY)
    assert composite['status']=='available' and composite['limited_evidence']==(n<15)


def test_empty_window_and_unavailable_format(research):
    seed(research,day=TODAY-timedelta(days=45))
    for window,status in [('7','no_data'),('30','no_data'),('format','format_unavailable')]:
        header,_,_=research.selected(KEY,window,TODAY)
        assert header['status']==status and header['eligible_decks']==0
        assert research.evidence_page(KEY,window,today=TODAY)['total']==0
        assert research.composite(KEY,window,TODAY)['status']=='unavailable'
    assert research.selected(KEY,'90',TODAY)[0]['eligible_decks']==4


def test_format_and_inclusive_time_boundaries(research):
    seed(research,[1],day=TODAY-timedelta(days=6),event='1')
    seed(research,[1],day=TODAY-timedelta(days=7),event='2')
    assert research.selected(KEY,'7',TODAY)[0]['eligible_decks']==1
    research.competitive.format_start=TODAY-timedelta(days=7)
    assert research.selected(KEY,'format',TODAY)[0]['eligible_decks']==2
    research.competitive.format_start=TODAY+timedelta(days=1)
    assert research.selected(KEY,'format',TODAY)[0]['status']=='format_unavailable'


def test_shared_list_urls_and_stable_result_identity(research):
    seed(research,[1]*24)
    one=research.evidence_page(KEY,page_size=10,today=TODAY)
    two=research.evidence_page(KEY,page=2,page_size=10,today=TODAY)
    assert one['total']==24 and one['next_page']==2 and two['next_page']==3
    assert len({d['id'] for d in one['decks']+two['decks']})==20
    assert len({d['source_url'] for d in one['decks']+two['decks']})==1
    assert evidence_key('1',1)!=evidence_key('2',1)
    assert archetype_key('/decks/284')!=KEY


def test_statistics_full_precision_zero_bucket_and_distribution(research):
    seed(research,[4,3,1,4])
    with closing(research.competitive.connect(True)) as db,db:
        row=db.execute('select cards from competitive_decks where rank=3').fetchone()
        counts=json.loads(row[0]);fid=research.collection.catalog()[0]['sm2-1']['functional_id']
        other=research.collection.catalog()[0]['sm2-2']['functional_id'];counts[other]=counts.pop(fid)
        db.execute('update competitive_decks set cards=? where rank=3',(json.dumps(counts),))
    stats={r['functional_id']:r for r in research.statistics(KEY,today=TODAY)['cards']}
    row=stats[fid]
    assert row['included_decks']==3 and row['total_copies']==11
    assert row['average_when_included']==11/3 and row['average_all_decks']==11/4
    assert row['median_copies']==3.5
    assert row['distribution']==[dict(quantity=0,decks=1),dict(quantity=3,decks=1),dict(quantity=4,decks=2)]


def test_unmapped_accounting_and_faithful_source_detail(research):
    seed(research,[1],unmapped=2)
    header,_,_=research.selected(KEY,today=TODAY)
    assert (header['eligible_decks'],header['published_decks'],header['excluded_unmapped'],header['results_without_lists'])==(1,3,2,2)
    assert research.evidence_page(KEY,today=TODAY)['total']==1
    assert research.evidence_page(KEY,include_excluded=True,today=TODAY)['total']==3
    deck=research.tournament_deck(evidence_key('1',2))
    assert deck['card_count']==60 and deck['mapped_card_count']==1
    assert not deck['observation']['mapped'] and deck['unmapped_cards'][0]['count']==59
    assert deck['published_cards'][1]['number']=='999'
    assert deck['observation']['player']=='Player 2' and deck['observation']['placement']==2
    assert len(deck['pages'][0]['sha256'])==64 and deck['pages'][0]['parser']=='main-html-v1'


def test_composite_determinism_60_observed_only_and_validator(research):
    seed(research)
    first=research.composite(KEY,today=TODAY)
    assert first==research.composite(KEY,today=TODAY)
    assert first['status']=='available' and first['total']==60
    counts={c['functional_id']:c['quantity'] for c in first['cards']}
    rows=research.selected(KEY,today=TODAY)[1]
    assert counts in [d['cards'] for d in rows]
    assert set(counts)<=set().union(*(d['cards'] for d in rows))
    catalog=research.collection.catalog()
    converted={deck_identity(catalog[0][catalog[1][fid][0]]):q for fid,q in counts.items()}
    assert any(key.startswith('deck-basic-energy:') and q>4 for key,q in converted.items())
    deck=Deck.model_construct(name='test',version='test',format='standard',cards=[DeckEntry.model_construct(card_id=k,count=q) for k,q in converted.items()])
    assert Lab(DeckProvider(research.collection),None).validate(deck)['status']=='passes_supported_checks'
    with closing(research.competitive.connect(True)) as db,db:
        # Rank and input enumeration are not composite tie-breakers.
        db.execute('update competitive_decks set rank=rank+100')
    assert first==research.composite(KEY,today=TODAY)


@pytest.mark.parametrize('quantity',[5,60])
def test_composite_unavailable_instead_of_inventing_valid_deck(research,quantity):
    # 5+ same-name Pokémon violate the inherited rule. A list of 60 also contains
    # no Energy, but remains faithfully counted as observed evidence.
    seed(research,[quantity] if quantity<60 else [59])
    result=research.composite(KEY,today=TODAY)
    assert result['status']=='unavailable' and result['cards']==[] and result['total']==0
    assert result['reasons']


def test_invalid_candidate_does_not_hide_valid_candidate(research):
    seed(research,[5,5,1])
    assert research.composite(KEY,today=TODAY)['status']=='available'


def test_unknown_archetype_does_not_claim_prevalence(research):
    seed(research,[1]*15,archetype='unknown')
    assert all(c['inclusion_percent'] is None for c in research.statistics(archetype_key('unknown'),today=TODAY)['cards'])


def test_typed_endpoints_and_read_only_boundaries(research):
    seed(research,day=date.today(),unmapped=1)
    collection=research.collection
    client=TestClient(create_app(collection.cards.path,collection.path,research.competitive.path))
    workspace=client.get('/api/v1/deck-workspace').json()
    before={p:p.read_bytes() for p in (collection.cards.path,collection.path,research.competitive.path)}
    for suffix in ['', '/cards','/decks','/composite']:
        response=client.get(f'/api/v1/research/archetypes/{KEY}{suffix}')
        assert response.status_code==200,response.text
    detail=client.get(f'/api/v1/research/tournament-decks/{evidence_key("1",1)}')
    assert detail.status_code==200 and detail.json()['card_count']==60
    assert sum(detail.json()['categories'].values())==60
    assert all(c['card'].get('ownership') is None for c in detail.json()['cards'])
    assert client.get(f'/api/v1/research/archetypes/{KEY}?window=bad').status_code==422
    assert client.get(f'/api/v1/research/archetypes/{KEY}/decks?page=0').status_code==422
    assert client.get('/api/v1/research/archetypes/nonexistent').status_code==404
    assert client.get('/api/v1/research/tournament-decks/nonexistent').status_code==404
    assert client.get('/api/v1/deck-workspace').json()==workspace
    assert all(p.read_bytes()==data for p,data in before.items())
