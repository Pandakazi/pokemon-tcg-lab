"""One-call v2 ownership/degradation tests, real frozen evidence and fake transport."""
import json
import httpx
import pytest
from pokelab import agent_research as a, card_pool_research as p, card_pool_answer as c
from pokelab.agent_providers import Selection
from pokelab.research_grounding import fields
from test_card_pool_remediation import envelope
from test_card_pool_research import offline, sources, setup, research, query


def response():
    e=envelope();ids={fields(i.model_dump()['fields'])['name']:i.id for i in e.packet.evidence}
    return dict(version='pokelab-card-pool-answer-v2',outcome='answered',
        candidates=list(ids.values()),synthesis=[dict(text='Centiskorch mills 2 cards while Deino mills 1.',
            evidence=[ids['Centiskorch'],ids['Deino']],required=False)],limitations=[])


def run(sources,monkeypatch,body):
    calls=[];e=envelope();monkeypatch.setattr(p,'build',lambda *args,**kw:e)
    def handle(request):
        calls.append(json.loads(request.content))
        assert calls[-1]['provider']=={'allow_fallbacks':False,'max_price':{'prompt':0,'completion':0,'request':0}}
        assert calls[-1]['max_tokens']==4096
        assert calls[-1]['messages'][0]['content']==c.SYSTEM
        assert json.loads(calls[-1]['messages'][1]['content'])['content_hash']==e.content_hash
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(body)},'finish_reason':'stop'}]})
    service=a.ResearchService(sources.paths,selection=Selection(provider='openrouter',model='fixture/model:free'),transport=httpx.MockTransport(handle))
    return service.run(query()),calls


def test_five_factual_cards_come_only_from_evidence(sources,monkeypatch):
    result,calls=run(sources,monkeypatch,response())
    assert len(calls)==1 and result['status']=='answered'
    answer=result['answer'];assert answer['facts']==[] and len(answer['card_facts'])==5
    assert len(answer['interpretation'])==1
    for card,item in zip(answer['card_facts'],envelope().packet.evidence):
        source=fields(item.model_dump()['fields'])
        assert card['name']==source['name'] and card['printing']==source['printing']
        assert card['evidence_id']==item.id and card['standard'] is True
        for component,original in zip(card['components'],source['components']):
            assert component['text']==original['text']
            assert component['cost']==original['structured'].get('cost')
            assert component['damage']==original['structured'].get('damage')
    assert answer['card_facts'][0]['components'][0]['damage'] is None
    assert result['envelope']['content_hash']=='e12ca2b923f1b1b1523b9e8d92c8df6b8c12ccbf14ab890cd8b075ade0f0afa9'


@pytest.mark.parametrize('text,condition',[
    ('Mega Venusaur ex is a mill engine.','candidate_outside_evidence'),
    ('Centiskorch has 999 HP.','unsupported_numeric_card_claim'),
    ('Centiskorch is a proven tournament staple.','unsupported_competitive_claim'),
])
@pytest.mark.parametrize('required',[False,True])
def test_bad_synthesis_cannot_leak(sources,monkeypatch,text,condition,required):
    body=response();body['synthesis'].append(dict(text=text,evidence=[body['candidates'][0]],required=required))
    result,calls=run(sources,monkeypatch,body)
    assert len(calls)==1 and text not in json.dumps(result)
    if required:
        assert result['status']=='invalid_answer_contract' and result['answer'] is None
        assert result['contract_diagnostics']['condition']==condition
    else:
        assert result['status']=='answered' and len(result['answer']['card_facts'])==5
        assert len(result['answer']['interpretation'])==1
        assert result['synthesis_diagnostics']['omitted']==[dict(field='synthesis',index=1,condition=condition)]


@pytest.mark.parametrize('text',[
    'Centiskorch uses Controlled Burn to discard cards.',
    'Centiskorch is a proven tournament staple.',
])
def test_bad_optional_limitation_does_not_hide_printed_cards(sources,monkeypatch,text):
    body=response();body['limitations']=[text]
    result,calls=run(sources,monkeypatch,body)
    assert result['status']=='answered' and len(calls)==1
    assert text not in json.dumps(result) and result['synthesis_diagnostics']['omitted']
    assert result['answer']['limitations']==[c.BOUNDARY]


@pytest.mark.parametrize('change',[
    lambda b:b.update(candidates=['ev-unknown']),
    lambda b:b['synthesis'][0].update(evidence=['ref-unknown']),
    lambda b:b['synthesis'][0].update(evidence=[]),
    lambda b:b.update(facts=[{'text':'UNSAFE FACT','evidence':[]}]),
    lambda b:b.update(version='pokelab-research-answer-v1'),
    lambda b:b.update(candidates=[]),
])
def test_core_integrity_hard_fails(sources,monkeypatch,change):
    body=response();change(body)
    result,calls=run(sources,monkeypatch,body)
    assert result['status']=='invalid_answer_contract' and result['answer'] is None and len(calls)==1
    assert 'UNSAFE FACT' not in json.dumps(result)


def test_all_optional_synthesis_can_be_omitted():
    body=response();body['synthesis'][0]['text']='Centiskorch has 999 HP.'
    answer,omitted=c.assess(json.dumps(body),envelope())
    assert answer['interpretation']==[] and len(answer['card_facts'])==5 and len(omitted)==1


def test_unusable_factual_evidence_hard_fails_before_inference(sources,monkeypatch):
    e=envelope();item=e.packet.evidence[0].model_copy(update={'references':('ref-absent',)})
    e=e.model_copy(update={'packet':e.packet.model_copy(update={'evidence':(item,*e.packet.evidence[1:])})})
    monkeypatch.setattr(p,'build',lambda *args,**kw:e)
    def forbidden(request): pytest.fail('Bad facts must fail before provider call')
    service=a.ResearchService(sources.paths,selection=Selection(provider='openrouter',model='fixture/model:free'),transport=httpx.MockTransport(forbidden))
    result=service.run(query())
    assert result['status']=='context_unavailable' and result['answer'] is None


def test_internal_error_never_becomes_optional_degradation(sources,monkeypatch):
    def broken(*args): raise RuntimeError('PRIVATE_EXCEPTION')
    monkeypatch.setattr(a,'assess',broken)
    result,calls=run(sources,monkeypatch,response())
    assert result['status']=='internal_assessment_failure' and result['answer'] is None and len(calls)==1
    assert 'PRIVATE_EXCEPTION' not in json.dumps(result)


def test_gemini_uses_pool_only_schema(sources,monkeypatch):
    from pokelab import agent_providers
    calls=[]
    def complete(*args,**kw):
        calls.append(kw)
        return agent_providers.Response(status='ok',text=json.dumps(response()),finish_reason='stop',latency_ms=1)
    monkeypatch.setattr(p,'build',lambda *args,**kw:envelope())
    monkeypatch.setattr(agent_providers,'complete',complete)
    service=a.ResearchService(sources.paths,selection=Selection(provider='gemini',model='fixture'),transport=httpx.MockTransport(lambda r:None))
    result=service.run(query())
    assert calls[0]['response_schema']==c.PoolResponse.model_json_schema()
    assert result['status']=='answered'
