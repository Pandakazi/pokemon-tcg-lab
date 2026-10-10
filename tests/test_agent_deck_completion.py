"""Pure small deficits: production orchestration with a mocked provider."""
import json
import httpx
import pytest
from pokelab import agent_research as a
from pokelab.agent_providers import Selection
from pokelab.agent_deck_completion import eligible
from test_agent_finalize_repair import deck
from test_agent_deck_proposals import stores
from test_card_pool_research import sources,setup,research,offline

QUESTION='Create a complete legal 60-card Standard deck with Pikachu ex, Recovery Tool, ACE Draw and ACE Recovery.'


def partial(n=58,pika=3,recovery=3,ace=False):
    rows=[('Pikachu ex','qa-pikachu',pika,'core'),('Recovery Tool','qa-recover',recovery,'recovery')]
    if ace:rows.append(('ACE Draw','qa-ace1',1,'draw'))
    rows.append(('Lightning Energy','qa-energy',n-pika-recovery-int(ace),'energy'))
    return deck(rows)


def addition(env,name,n):
    row=next(c for c in env['candidate_sandbox']['candidates'] if c['name']==name)
    return dict(candidate_id=row['candidate_id'],quantity=n)


def delta(adds,removes=None):
    return '<POKELAB_ACTIONS>'+json.dumps(dict(type='generated_deck_completion',adds=adds,removes=removes or []))+'</POKELAB_ACTIONS>'


def service(stores,replies):
    calls=[]
    def handle(req):
        body=json.loads(req.content);env=json.loads(body['messages'][1]['content']);calls.append(env)
        reply=replies[min(len(calls)-1,len(replies)-1)]
        value=reply(env) if callable(reply) else reply
        if isinstance(value,httpx.Response):return value
        return httpx.Response(200,json={'choices':[{'message':{'content':value},'finish_reason':'stop'}]})
    return a.ResearchService(stores.paths,selection=Selection(provider='gemini',model='gemini-3.5-flash-lite'),transport=httpx.MockTransport(handle)),calls


def execute(stores,reply,initial=None):
    svc,calls=service(stores,[initial or partial(),reply])
    before={k:p.read_bytes() for k,p in stores.paths.items()}
    result=svc.run(a.ResearchRequest(scope='conversation',question=QUESTION))
    assert len(calls)==2 and before=={k:p.read_bytes() for k,p in stores.paths.items()}
    return result,calls,svc


def test_pm_58_two_candidates_and_local_recount(stores):
    result,calls,svc=execute(stores,lambda e:delta([addition(e,'Pikachu ex',1),addition(e,'Recovery Tool',1)]))
    request=calls[1]['repair']
    assert request['mode']=='additive_completion' and request['required_delta']==2
    assert request['accounting']==dict(resolved_count=58,unresolved_proposed_count=0,proposed_total=58,true_missing_count=2,excess_proposed_count=0)
    assert request['construction_violations']==[]
    report=result['answer']['proposal']
    assert report['total_cards']==60 and report['validation_status']=='VALIDATED'
    assert result['answer']['completion']['status']=='complete'
    counts={r['canonical_name']:r['quantity'] for r in report['cards']}
    assert counts=={'Pikachu ex':4,'Recovery Tool':4,'Lightning Energy':52}
    again=svc.run(a.ResearchRequest(scope='conversation',question='Recount that deck.',conversation_id=result['conversation_id']))
    assert again['answer']['proposal']['total_cards']==60 and len(calls)==2


@pytest.mark.parametrize('total,missing',[(59,1),(58,2)])
def test_basic_energy_completion(stores,total,missing):
    result,calls,_=execute(stores,lambda e:delta([addition(e,'Lightning Energy',missing)]),partial(total))
    assert result['answer']['proposal']['total_cards']==60
    assert result['answer']['completion']['status']=='complete'


@pytest.mark.parametrize('n',[1,3])
def test_wrong_delta_preserves_58(stores,n):
    result,_,svc=execute(stores,lambda e:delta([addition(e,'Lightning Energy',n)]))
    assert result['answer']['proposal']['completion_debug']['provider_failure']=='repair_delta_wrong_size'
    assert result['answer']['proposal']['total_cards']==60
    assert svc.conversations.get(result['conversation_id'])['artifacts']['generated_deck']['report']['total_cards']==60


@pytest.mark.parametrize('reply,reason',[
    (lambda e:delta([dict(candidate_id='gameplay:outside',quantity=2)]),'repair_candidate_outside_sandbox'),
    (lambda e:delta([dict(quantity=2)]),'repair_candidate_id_invalid'),
    ('not a structured delta','repair_parse_failed'),
    (partial(),'repair_parse_failed'),
    (lambda e:delta([addition(e,'Lightning Energy',2)],[addition(e,'Pikachu ex',1)]),'repair_parse_failed'),
    (httpx.Response(200,json={'choices':[{'message':{'content':'partial'},'finish_reason':'length'}]}),'repair_provider_incomplete'),
])
def test_invalid_repairs_preserve_artifact(stores,reply,reason):
    result,_,_=execute(stores,reply)
    assert result['answer']['proposal']['completion_debug']['provider_failure']==reason
    assert result['answer']['proposal']['total_cards']==60


def test_copy_limit(stores):
    result,_,_=execute(stores,lambda e:delta([addition(e,'Pikachu ex',1),addition(e,'Lightning Energy',1)]),partial(pika=4))
    assert result['answer']['proposal']['completion_debug']['provider_failure']=='repair_copy_limit_violation'
    assert result['answer']['proposal']['total_cards']==60
    assert not result['answer']['proposal']['construction_violations']


def test_ace_spec(stores):
    result,_,_=execute(stores,lambda e:delta([addition(e,'ACE Recovery',1),addition(e,'Lightning Energy',1)]),partial(ace=True))
    assert result['answer']['proposal']['completion_debug']['provider_failure']=='repair_ace_spec_violation'
    assert result['answer']['proposal']['total_cards']==60
    assert not result['answer']['proposal']['construction_violations']


def test_pending_completion_failure_and_success(stores,monkeypatch):
    # Simulate genuinely insufficient safe local options; pending retry remains.
    import pokelab.agent_deck_completion as completion
    monkeypatch.setattr(completion,'final_fill',lambda r:(None,{'reason':'insufficient_safe_completion_candidates'}))
    svc,calls=service(stores,[partial(),lambda e:delta([addition(e,'Lightning Energy',1)]),
        lambda e:delta([addition(e,'Lightning Energy',3)]),lambda e:delta([addition(e,'Lightning Energy',2)])])
    first=svc.run(a.ResearchRequest(scope='conversation',question=QUESTION))
    second=svc.run(a.ResearchRequest(scope='conversation',question='Finish it.',conversation_id=first['conversation_id']))
    assert second['answer']['proposal']['total_cards']==58 and second['answer']['completion']['reason']=='repair_delta_wrong_size'
    assert len(calls)==3
    third=svc.run(a.ResearchRequest(scope='conversation',question='Finish it.',conversation_id=first['conversation_id']))
    assert third['answer']['proposal']['total_cards']==60 and third['answer']['completion']['status']=='complete'
    assert len(calls)==4


def test_not_pure_when_other_validation_errors_exist():
    report=dict(kind='list',resolution_status='RESOLVED',total_cards=58,unresolved=[],construction_violations=[],
        validation_status='NEEDS_REPAIR',candidate_sandbox={'candidates':[{}]},hard_validation=['Deck must contain at least one Basic Pokemon.'])
    assert not eligible(report)


def test_post_apply_failure_retains_original(stores,monkeypatch):
    from pokelab import agent_deck_proposals
    original=agent_deck_proposals.evaluate
    calls=[]
    def checked(*args,**kwargs):
        calls.append(1)
        report,extra,rejected=original(*args,**kwargs)
        if args[4].get('repair',{}).get('mode')=='additive_completion' or len(calls)>=3:
            report['validation_status']='STALE'
        return report,extra,rejected
    monkeypatch.setattr(agent_deck_proposals,'evaluate',checked)
    result,_,_=execute(stores,lambda e:delta([addition(e,'Lightning Energy',2)]))
    assert result['answer']['proposal']['total_cards']==58
    assert result['answer']['completion']['reason']=='local_completion_validation_failed'


def test_provider_failure_retains_original(stores):
    result,_,_=execute(stores,httpx.Response(429,json={'error':{'code':429}}))
    assert result['answer']['proposal']['total_cards']==60
    assert result['answer']['proposal']['completion_debug']['provider_failure']=='repair_provider_failure'
