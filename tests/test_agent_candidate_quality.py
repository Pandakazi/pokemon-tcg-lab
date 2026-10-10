"""Offline ranking/role fixtures. No tournament template or live model required."""
from datetime import date,timedelta
import json
import sqlite3
import pytest
from pokelab.agent_deck_sandbox import build,legal_pool,retrieval
from pokelab.agent_candidate_quality import prior,rank
from pokelab.competitive import Competitive
from pokelab.api import ReadOnlyCards
from test_agent_resolution_reprints import install
from test_agent_deck_proposals import stores
from test_card_pool_research import sources,setup,research,offline

TODAY=date(2026,10,10)


@pytest.fixture
def quality(stores):
    cards=[]
    def pokemon(id,name,parent=None,effect=None):
        r=dict(id=id,name=name,category='Pokemon',stage='Stage2' if name=='Dragapult ex' else 'Stage1' if parent else 'Basic',types=['Dragon'],attacks=[dict(name='Plan',cost=['Fire','Psychic'],damage=200,effect=effect or 'Put 6 damage counters on your opponent\'s Benched Pokémon.')])
        if parent:r['evolveFrom']=parent
        cards.append(r)
    pokemon('dreepy','Dreepy');pokemon('drakloak','Drakloak','Dreepy');pokemon('dragapult','Dragapult ex','Drakloak')
    cards[-2]['abilities']=[dict(name='Filter',effect='Look at the top 2 cards of your deck. Put 1 into your hand.')]
    pokemon('milcery','Milcery');pokemon('alcremie','Alcremie ex','Milcery','Heal 30 damage from your Pokémon.')
    cards[-1]['types']=['Fairy']
    cards.append(dict(id='scout',name='Scout',category='Pokemon',stage='Basic',abilities=[dict(name='Scout',effect='Draw 2 cards.')]))
    cards.append(dict(id='tech',name='Counter Tech',category='Pokemon',stage='Basic',abilities=[dict(name='Counters',effect="Put 1 damage counter on your opponent's Benched Pokémon.")]))
    effects={
        'Modern Search':('Item','Search your deck for 2 Basic Pokémon and put them into your hand.'),
        'Alternate Search':('Item','Search your deck for a Pokémon and put it into your hand.'),
        'Old Search':('Supporter','Search your deck for a Pokémon and put it into your hand.'),
        'Draw Support':('Supporter','Draw 3 cards.'),
        'Flow Support':('Item','Draw 2 cards.'),
        'Evolution Support':('Item','Search your deck for a Stage 2 Pokémon. Evolve your Basic Pokémon this turn.'),
        'Recovery Support':('Item','Put 2 Pokémon from your discard pile into your hand.'),
        'Gust Support':('Supporter',"Switch 1 of your opponent's Benched Pokémon with their Active Pokémon."),
        'Disrupt Support':('Supporter',"Your opponent shuffles their hand into their deck."),
        'Switch Support':('Item','Switch your Active Pokémon with 1 of your Benched Pokémon.'),
        'Evolution Stadium':('Stadium','Evolve your Pokémon this turn.'),
        'Tempo Tool':('Tool',"This Pokémon has no retreat cost."),
        'Energy Support':('Item','Attach a Basic Energy from your hand to your Pokémon.'),
    }
    for n,(kind,effect) in effects.items():cards.append(dict(id=n.lower().replace(' ','-'),name=n,category='Trainer',trainerType=kind,effect=effect))
    for t in ('Fire','Psychic','Grass','Water','Fighting','Metal','Fairy'):
        cards.append(dict(id=t.lower(),name=t+' Energy',category='Energy',energyType='Normal',types=[t]))
    for r in cards:r.update(legal={'standard':True},regulationMark='H',variants={'normal':True})
    install(stores,cards)
    return stores,cards


def seed(stores,cards,days,names,event):
    comp=Competitive(ReadOnlyCards(stores.paths['cards']),stores.paths['competitive']);comp.initialize()
    with sqlite3.connect(stores.paths['cards']) as db:
        ids=dict(db.execute('SELECT printing_id,legacy_id FROM gameplay_printings'))
    mapping={r['name']:ids[r['id']] for r in cards}
    counts={mapping[n]:4 for n in ['Dragapult ex',*names]}
    counts[mapping['Fire Energy']]=60-sum(counts.values())
    day=(TODAY-timedelta(days=days)).isoformat()
    raw=dict(archetype_id='dragapult',archetype_name='Dragapult ex',cards=[],player='Fixture')
    with sqlite3.connect(stores.paths['competitive']) as db:
        db.execute('INSERT INTO competitive_events VALUES (?,?,?,?,?,?,?)',('limitless-main',event,day,json.dumps(dict(format='standard',date=day)),day,1,1))
        db.execute('INSERT INTO competitive_decks VALUES (?,?,?,?,?,?)',('limitless-main',event,1,1,json.dumps(raw),json.dumps(counts)))


def packet(quality):
    stores,_=quality
    return build(stores.paths['cards'],'Build a Standard Dragapult ex deck',competitive_path=stores.paths['competitive'],today=TODAY)


def test_recent_prior_and_core_burden(quality):
    stores,cards=quality
    seed(stores,cards,2,['Modern Search','Scout'],'new')
    seed(stores,cards,80,['Old Search','Alcremie ex'],'old')
    pool=legal_pool(stores.paths['cards']);core=[r for r in pool if r['card']['name']=='Dragapult ex']
    usage,field,meta=prior(stores.paths['cards'],stores.paths['competitive'],pool,core,'Dragapult ex',today=TODAY)
    scores=rank(pool,retrieval(pool),core,usage,field)
    by_name={r['card']['name']:scores[r['functional_id']] for r in pool}
    assert by_name['Modern Search']['score']>by_name['Old Search']['score']
    assert by_name['Evolution Support']['score']>by_name['Alcremie ex']['score']
    assert by_name['Alcremie ex']['setup_burden']>0
    side=next(r['functional_id'] for r in pool if r['card']['name']=='Alcremie ex')
    supported=rank(pool,retrieval(pool),core,{side:1},{})
    assert supported[side]['score']>by_name['Evolution Support']['score']
    assert meta['latest_event']=='2026-10-08' and meta['limited_evidence'] and meta['half_life_days']==30


def test_roles_energy_creativity_and_budget(quality):
    stores,cards=quality;seed(stores,cards,2,['Modern Search','Scout'],'new')
    p=packet(quality);names={r['name'] for r in p['candidates']}
    assert {'Dreepy','Drakloak','Dragapult ex','Modern Search','Draw Support','Recovery Support','Gust Support','Disrupt Support','Evolution Stadium','Scout'}<=names
    assert names & {'Rescue Board','Tempo Tool','Switch Support'}
    assert {r['name'] for r in p['candidates'] if r['basic_energy']}=={'Fire Energy','Psychic Energy'}
    assert any(r['role']=='creative' for r in p['candidates'])
    assert len(p['candidates'])<=48 and len(json.dumps(p['candidates'],ensure_ascii=False).encode())<=14000
    assert next(r for r in p['candidates'] if r['name']=='Modern Search')['ranking']['recent_prior']==1


def test_no_cache_and_explicit_energy(quality):
    stores,_=quality
    p=build(stores.paths['cards'],'Build a Standard Dragapult ex deck with Water Energy')
    assert p['competitive_prior']['status']=='unavailable'
    assert {'Fire Energy','Psychic Energy','Water Energy'}=={r['name'] for r in p['candidates'] if r['basic_energy']}


def test_draw_abundance_cannot_crowd_out_roles(quality):
    stores,cards=quality
    extra=[dict(id=f'draw-{i}',name=f'Draw Option {i}',category='Trainer',trainerType='Item',effect='Draw 3 cards.',legal={'standard':True},regulationMark='H',variants={'normal':True}) for i in range(20)]
    install(stores,extra)
    seed(stores,cards+extra,2,[r['name'] for r in extra[:10]],'draw-event')
    p=packet(quality);names={r['name'] for r in p['candidates']}
    assert {'Dragapult ex','Gust Support','Disrupt Support','Evolution Stadium'}<=names
    assert {'setup-search','recovery'}<={r['role'] for r in p['candidates']}


def test_full_build_without_padding(quality):
    from test_agent_deck_completion import service
    from pokelab.agent_research import ResearchRequest
    stores,cards=quality;seed(stores,cards,2,['Modern Search','Scout'],'new')
    def answer(e):
        rows={r['name']:r for r in e['candidate_sandbox']['candidates']}
        support=[r['name'] for r in rows.values() if r['category']=='Trainer' and not r['ace_spec']][:10]
        assert len(support)==10
        names=['Dreepy','Drakloak','Dragapult ex',*support]
        selected=[dict(candidate_id=rows[n]['candidate_id'],quantity=4) for n in names+['Fire Energy','Psychic Energy']]
        return '<POKELAB_ACTIONS>'+json.dumps(dict(type='generated_deck',cards=selected))+'</POKELAB_ACTIONS>'
    svc,calls=service(stores,[answer])
    before={k:p.read_bytes() for k,p in stores.paths.items()}
    result=svc.run(ResearchRequest(scope='conversation',question='Build a Standard Dragapult ex deck'))
    assert result['status']=='answered',result
    report=result['answer']['proposal']
    assert report['validation_status']=='VALIDATED' and report['total_cards']==60
    assert report['category_subtotals']['Energy']==8 and len(calls)==1
    assert before=={k:p.read_bytes() for k,p in stores.paths.items()}
