"""Production hybrid/parser/resolver path, fake provider only."""
import json
import httpx
import pytest
from pokelab import agent_research as a
from pokelab.agent_deck_sandbox import build
from pokelab.agent_artifacts import repair_requirements
from pokelab.agent_providers import Selection
from test_agent_deck_proposals import stores
from test_agent_resolution_reprints import install
from test_card_pool_research import sources,setup,research,offline


@pytest.fixture
def candidates(stores):
    raws=[]
    for name in ('Milcery','Patrat'):
        for n in (1,2):
            raws.append(dict(id=name.lower()+str(n),name=name,category='Pokemon',stage='Basic',regulationMark='H',
                legal={'standard':True},variants={'normal':True},attacks=[dict(name='Hit',cost=['Colorless'],damage=n*10)]))
    for id,name in [('tree','Grand Tree'),('rod','Max Rod')]:
        raws.append(dict(id=id,name=name,category='Trainer',trainerType='Item',regulationMark='H',
            legal={'standard':True},variants={'normal':True},effect='Draw 2 cards.'))
    # install supplies ordinary rarity; update the two cards through supported ingestion.
    install(stores,raws)
    from tcg_lab.card_db import SQLiteCards
    db=SQLiteCards(stores.paths['cards'])
    for raw in raws[-2:]:db.put(dict(raw,rarity='ACE SPEC',set={'id':'qa'},localId=raw['id']))
    return stores


QUESTION='Create a complete legal 60-card deck with Milcery, Patrat, Pikachu ex, Grand Tree and Max Rod.'


def run(stores,replies):
    calls=[]
    def handle(req):
        env=json.loads(json.loads(req.content)['messages'][1]['content']);calls.append(env)
        cards=replies[min(len(calls)-1,len(replies)-1)](env['candidate_sandbox']['candidates'])
        answer='<POKELAB_ACTIONS>'+json.dumps(dict(type='generated_deck',name='Fixture',cards=cards))+'</POKELAB_ACTIONS>'
        return httpx.Response(200,json={'choices':[{'message':{'content':answer},'finish_reason':'stop'}]})
    svc=a.ResearchService(stores.paths,selection=Selection(provider='gemini',model='gemini-3.5-flash-lite'),transport=httpx.MockTransport(handle))
    result=svc.run(a.ResearchRequest(scope='conversation',question=QUESTION))
    return result,calls


def choose(packet,name,n,ordinal=0,**extra):
    c=[c for c in packet if c['name']==name][ordinal]
    return dict(candidate_id=c['candidate_id'],quantity=n,**extra)


def test_id_round_trip_and_canonical_not_printing_authority(candidates):
    def cards(p):return [choose(p,'Milcery',3,1,printing_id='wrong'),choose(p,'Pikachu ex',4),choose(p,'Lightning Energy',53)]
    result,calls=run(candidates,[cards]);p=calls[0]['candidate_sandbox']['candidates']
    options=[c for c in p if c['name']=='Milcery']
    assert len(options)==2 and len({c['candidate_id'] for c in options})==2
    report=result['answer']['proposal']
    assert report['validation_status']=='VALIDATED' and not report['unresolved'] and len(calls)==1
    row=next(r for r in report['cards'] if r['canonical_name']=='Milcery')
    assert row['candidate_id']==options[1]['candidate_id'] and row['printing_id']==options[1]['printing_id']
    assert row['card_id']==row['candidate_id']


@pytest.mark.parametrize('mode,state',[('bare','ambiguous'),('mismatch','candidate_name_mismatch'),('outside','outside_candidate_sandbox')])
def test_identity_rejections(candidates,mode,state):
    def cards(p):
        bad={'card_name':'Milcery','quantity':3}
        if mode=='mismatch':bad.update(candidate_id=choose(p,'Patrat',1)['candidate_id'])
        if mode=='outside':bad.update(candidate_id='gameplay:unknown')
        return [choose(p,'Pikachu ex',4),choose(p,'Lightning Energy',53),bad]
    result,calls=run(candidates,[cards]);report=result['answer']['proposal']
    assert report['total_cards']==57 and report['unresolved'][0]['state']==state
    assert report['validation_status']!='VALIDATED'


def test_unambiguous_name_compatibility(candidates):
    result,calls=run(candidates,[lambda p:[{'card_name':'Pikachu ex','quantity':4},{'card_name':'Lightning Energy','quantity':56}]])
    assert result['answer']['proposal']['validation_status']=='VALIDATED' and len(calls)==1


def initial(p):
    return [choose(p,'Pikachu ex',4),choose(p,'Grand Tree',1),choose(p,'Max Rod',1),choose(p,'Lightning Energy',46),
            {'card_name':'Milcery','quantity':3},{'card_name':'Patrat','quantity':1}]


def test_pm_accounting_ace_and_single_small_repair(candidates):
    def fixed(p):return [choose(p,'Pikachu ex',4),choose(p,'Grand Tree',1),choose(p,'Lightning Energy',51),choose(p,'Milcery',3),choose(p,'Patrat',1)]
    result,calls=run(candidates,[initial,fixed]);assert len(calls)==2
    repair=calls[1]['repair']
    assert repair['accounting']==dict(resolved_count=52,unresolved_proposed_count=4,proposed_total=56,true_missing_count=4,excess_proposed_count=0)
    assert repair['missing_copies']==4 and sum(r['quantity'] for r in repair['unresolved'])==4
    assert dict(kind='ace_spec',count=2,maximum=1,excess=1) in repair['construction_violations']
    assert 'accounting.true_missing_count' in calls[1]['repair_instruction']
    report=result['answer']['proposal']
    assert report['total_cards']==60 and report['validation_status']=='VALIDATED' and not report['unresolved']
    assert report['accounting']['true_missing_count']==0
    packet=calls[0]['candidate_sandbox']['candidates']
    assert all(c['ace_spec'] for c in packet if c['name'] in ('Grand Tree','Max Rod'))
    assert all(c['basic_energy'] for c in packet if c['name']=='Lightning Energy')
    assert all(c['copy_limit_name']=='milcery' for c in packet if c['name']=='Milcery')


def test_two_ace_specs_still_invalid(candidates):
    result,calls=run(candidates,[lambda p:[choose(p,'Pikachu ex',4),choose(p,'Grand Tree',1),choose(p,'Max Rod',1),choose(p,'Lightning Energy',54)]])
    report=result['answer']['proposal']
    assert report['total_cards']==60 and report['validation_status']=='NEEDS_REPAIR'
    assert any('ACE SPEC' in s for s in report['hard_validation'])


def test_evolution_links_reference_supplied_candidates(candidates):
    install(candidates,[dict(id='cream',name='Alcremie ex',category='Pokemon',stage='Stage1',evolveFrom='Milcery',
        legal={'standard':True},regulationMark='H',variants={'normal':True},attacks=[dict(name='Cream',cost=['Psychic'],damage=50)])])
    packet=build(candidates.paths['cards'],'Build a Standard Alcremie ex deck')
    rows=packet['candidates'];child=next(c for c in rows if c['name']=='Alcremie ex')
    assert child['requested_core'] is True
    assert set(child['predecessor_candidate_ids'])=={c['candidate_id'] for c in rows if c['name']=='Milcery'}
    assert len(child['predecessor_candidate_ids'])==2


def test_legacy_name_alias_cannot_disagree_with_candidate(candidates):
    result,calls=run(candidates,[lambda p:[choose(p,'Pikachu ex',4),choose(p,'Lightning Energy',53),dict(choose(p,'Milcery',3),name='Patrat')]])
    assert result['answer']['proposal']['unresolved'][0]['state']=='candidate_name_mismatch'


def test_known_legal_id_outside_supplied_set_cannot_fall_back(candidates):
    from pokelab.agent_conversation import context
    from pokelab.agent_deck_proposals import evaluate,Proposal,Candidate
    request=a.ResearchRequest(scope='conversation',question=QUESTION)
    env=context(request,candidates,dict(turns=[],printings=[]))
    rows=env['candidate_sandbox']['candidates']
    target=next(c for c in rows if c['name']=='Milcery')
    rows.remove(target)
    report,_,_=evaluate(Proposal(kind='list',cards=(Candidate(candidate_id=target['candidate_id'],name='Milcery',quantity=3),)),(),candidates,request,env)
    assert report['total_cards']==0 and report['unresolved'][0]['state']=='outside_candidate_sandbox'
