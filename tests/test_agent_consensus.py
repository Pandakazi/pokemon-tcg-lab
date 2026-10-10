"""Deterministic recent-cohort allocation and production baseline consumption."""
from collections import Counter
from fractions import Fraction as F
import json
import sqlite3
import pytest
from pokelab.agent_consensus import select,weight,construct,baseline,proposal_for,permitted_deviation
from pokelab.agent_deck_sandbox import legal_pool
from test_agent_candidate_quality import quality,TODAY
from test_agent_deck_proposals import stores
from test_card_pool_research import sources,setup,research,offline


def rows(event,ranks,variant='Dragapult'):
    return [dict(event=str(event),date=f'2026-10-0{event}',placement=n,variant=variant,label=variant,cards={}) for n in ranks]


def test_depth_before_age_and_all_nine():
    data=rows(3,[1,8,16,24,30])+rows(2,[2,12,20,32])+rows(1,range(1,12))
    result=select(data,'Build me a Dragapult deck')
    assert result['event_ids']==['3','2'] and result['placement_band']==32
    assert len(result['sample'])==9


def test_age_only_after_deepest_and_restart():
    result=select(rows(3,[1,3,80])+rows(2,[2,4,90])+rows(1,[1,2,3,4]),'Build me a Dragapult deck')
    assert result['event_ids']==['3','2','1'] and result['placement_band']==8 and len(result['sample'])==8


def test_variant_and_explicit_priority():
    data=rows(3,range(1,6))+rows(2,range(1,5))+rows(3,[1,2],'Dragapult Dusknoir')+rows(2,[1,2],'Dragapult Dusknoir')+rows(3,[3,4],'Dragapult Blaziken')
    generic=select(data,'Build me a Dragapult deck')
    assert generic['variant']=='Dragapult' and all(r['variant']=='Dragapult' for r in generic['sample'])
    explicit=select(data,'Build me Dragapult Dusknoir')
    assert explicit['explicit_variant'] and explicit['variant']=='Dragapult Dusknoir'
    assert select(data,'Build me a control Dragapult deck')['constrained']
    assert select(data,'Build me a Dragapult deck with Alcremie ex')['constrained']
    assert not generic['constrained']


def shell():
    cards={f'p{i}':dict(name=f'Basic {i}',category='Pokemon',stage='Basic') for i in range(5)}
    cards.update({f't{i}':dict(name=f'Trainer {i}',category='Trainer') for i in range(9)})
    cards.update({f'deck-basic-energy:{t}':dict(name=t+' Energy',category='Energy') for t in ('Fire','Psychic','Darkness')})
    expected={k:F(19,5) if k.startswith('p') else F(11,3) for k in cards if not k.startswith('deck-')}
    expected.update({'deck-basic-energy:Fire':F(3),'deck-basic-energy:Psychic':F(3),'deck-basic-energy:Darkness':F(2)})
    return cards,expected


def test_fractional_shape_and_energy():
    cards,expected=shell();result=construct(expected,cards,cards)
    assert sum(result.values())==60
    assert {c:sum(n for k,n in result.items() if cards[k]['category']==c) for c in ('Pokemon','Trainer','Energy')}==dict(Pokemon=19,Trainer=33,Energy=8)
    assert all(result[k]==n for k,n in expected.items() if k.startswith('deck-'))
    assert weight(1)>weight(8)>weight(16)>weight(32) and weight(1)<2*weight(32)


def test_fractional_last_slots_and_stranded():
    cards,expected=shell()
    # Two strongest fractional Trainer entries win the final Trainer slots.
    expected.update({f't{i}':F(4) for i in range(8)})
    expected['t8']=F(47,100);cards['t9']=dict(name='Other',category='Trainer');expected['t9']=F(53,100)
    result=construct(expected,cards,cards)
    assert result.get('t9')==1 and not result.get('t8')
    cards['p0'].update(stage='Stage1',evolveFrom='Absent')
    assert construct(expected,cards,cards) is None


def test_rare_candy_route_without_middle_stage():
    cards,expected=shell()
    cards['p0'].update(name='Basic')
    cards['p1'].update(name='Final',stage='Stage2',evolveFrom='Middle')
    cards['t0'].update(name='Rare Candy',effect='Evolve your Basic Pokémon into a Stage 2 Pokémon.')
    universe=dict(cards,middle=dict(name='Middle',stage='Stage1',evolveFrom='Basic',category='Pokemon'))
    result=construct(expected,cards,universe)
    assert result['p0'] and result['p1'] and result['t0'] and sum(result.values())==60


@pytest.fixture
def cohort(quality):
    from pokelab.competitive import Competitive
    from pokelab.api import ReadOnlyCards
    stores,cards=quality
    comp=Competitive(ReadOnlyCards(stores.paths['cards']),stores.paths['competitive']);comp.initialize()
    with sqlite3.connect(stores.paths['cards']) as db:
        ids=dict(db.execute('SELECT printing_id,legacy_id FROM gameplay_printings'))
    trainer=[r for r in cards if r['category']=='Trainer'][:10]
    vector={ids[r['id']]:4 for r in trainer}
    vector.update({ids[k]:4 for k in ('dreepy','drakloak','dragapult','fire','psychic')})
    with sqlite3.connect(stores.paths['competitive']) as db:
        for event,day in [('one','2026-10-08'),('two','2026-10-09')]:
            db.execute('INSERT INTO competitive_events VALUES (?,?,?,?,?,?,?)',('limitless-main',event,day,json.dumps(dict(format='standard',date=day)),day,5,5))
            for rank in range(1,6):
                raw=dict(archetype_id='dragapult',archetype_name='Dragapult',cards=[],player='Fixture')
                db.execute('INSERT INTO competitive_decks VALUES (?,?,?,?,?,?)',('limitless-main',event,rank,1,json.dumps(raw),json.dumps(vector)))
    return stores


def test_production_baseline_and_readonly_state(cohort):
    from test_agent_deck_completion import service
    from pokelab.agent_research import ResearchRequest
    svc,calls=service(cohort,['The recent shell is a useful starting point.'])
    before={k:p.read_bytes() for k,p in cohort.paths.items()}
    result=svc.run(ResearchRequest(scope='conversation',question='Build me a Dragapult deck'))
    assert result['status']=='answered',result
    report=result['answer']['proposal']
    assert report['validation_status']=='VALIDATED' and report['total_cards']==60
    assert report['category_subtotals']['Energy']==8
    assert len(calls)==0 and result['envelope']['candidate_sandbox']['consensus']['sample_size']==10
    assert before=={k:p.read_bytes() for k,p in cohort.paths.items()}
    recount=svc.run(ResearchRequest(scope='conversation',question='Recount that deck',conversation_id=result['conversation_id']))
    assert recount['answer']['proposal']['total_cards']==60 and len(calls)==0


def test_bounded_deviation(cohort):
    from pokelab.agent_deck_sandbox import build
    p=build(cohort.paths['cards'],'Build me a Dragapult deck',competitive_path=cohort.paths['competitive'],today=TODAY)
    c=p['consensus'];proposal=proposal_for(c)
    assert permitted_deviation(proposal,c,p['candidates'])
    cards=list(proposal.cards);energy=next(i for i,r in enumerate(cards) if r.candidate_id.startswith('deck-basic-energy:'))
    other=next(i for i,r in enumerate(cards) if not r.candidate_id.startswith('deck-basic-energy:'))
    cards[energy]=cards[energy].model_copy(update={'quantity':cards[energy].quantity+1})
    cards[other]=cards[other].model_copy(update={'quantity':cards[other].quantity-1})
    changed=proposal.model_copy(update={'cards':tuple(cards),'rationale':'Testing one extra Energy for setup.'})
    assert permitted_deviation(changed,c,p['candidates'])
    assert not permitted_deviation(changed.model_copy(update={'rationale':''}),c,p['candidates'])


def test_large_padding_is_replaced_by_baseline(cohort):
    from test_agent_deck_completion import service
    from pokelab.agent_research import ResearchRequest
    def answer(e):
        energy=next(r for r in e['candidate_sandbox']['candidates'] if r['basic_energy'])
        return '<POKELAB_ACTIONS>'+json.dumps(dict(type='generated_deck',cards=[dict(candidate_id=energy['candidate_id'],quantity=60)],rationale='Filler'))+'</POKELAB_ACTIONS>'
    svc,calls=service(cohort,[answer]);result=svc.run(ResearchRequest(scope='conversation',question='Build me a Dragapult deck'))
    assert result['answer']['proposal']['category_subtotals']['Energy']==8 and len(calls)==0


def test_explicit_constraint_allows_deliberate_larger_deviation(cohort):
    from test_agent_deck_completion import service
    from pokelab.agent_research import ResearchRequest
    def answer(e):
        assert e['candidate_sandbox']['consensus']['constrained']
        rows={r['name']:r for r in e['candidate_sandbox']['candidates']}
        counts={'Dreepy':4,'Drakloak':4,'Dragapult ex':4,'Milcery':2,'Alcremie ex':2,'Fire Energy':44}
        return '<POKELAB_ACTIONS>'+json.dumps(dict(type='generated_deck',cards=[dict(candidate_id=rows[n]['candidate_id'],quantity=q) for n,q in counts.items()],rationale='Explicit experimental constraint'))+'</POKELAB_ACTIONS>'
    svc,calls=service(cohort,[answer]);result=svc.run(ResearchRequest(scope='conversation',question='Build me a Dragapult deck with Alcremie ex'))
    assert result['answer']['proposal']['validation_status']=='VALIDATED'
    assert result['answer']['proposal']['category_subtotals']['Energy']==44 and len(calls)==1


def test_functional_reprints_merge_and_no_variant_bleed(cohort):
    from test_agent_resolution_reprints import install
    with sqlite3.connect(cohort.paths['cards']) as db:
        raw=json.loads(db.execute("SELECT raw FROM cards WHERE id='dreepy'").fetchone()[0])
    raw.pop('rarity',None);raw.pop('set',None);raw.pop('localId',None)
    raw['id']='reprint';raw['attacks'][0]['effect']=' '+raw['attacks'][0]['effect']+' '
    install(cohort,[raw])
    pool=legal_pool(cohort.paths['cards'])
    with sqlite3.connect(cohort.paths['cards']) as db:
        ids=dict(db.execute('SELECT printing_id,legacy_id FROM gameplay_printings'))
    with sqlite3.connect(cohort.paths['competitive']) as db:
        row=db.execute("SELECT * FROM competitive_decks WHERE event_id='one' AND rank=1").fetchone()
        vector=json.loads(row[-1]);vector[ids['reprint']]=vector.pop(ids['dreepy'])
        # The schema's last field stores the functional vector.
        columns=[r[1] for r in db.execute('PRAGMA table_info(competitive_decks)')]
        db.execute(f'UPDATE competitive_decks SET {columns[-1]}=? WHERE event_id=? AND rank=?',(json.dumps(vector),'one',1))
    c=baseline(cohort.paths['cards'],cohort.paths['competitive'],pool,'Build me a Dragapult deck',today=TODAY)
    dreepy=[r for r in c['cards'] if r['name']=='Dreepy']
    assert len(dreepy)==1 and dreepy[0]['expected_copies']==4
    assert not {'Alcremie ex','Milcery'} & {r['name'] for r in c['cards']}
