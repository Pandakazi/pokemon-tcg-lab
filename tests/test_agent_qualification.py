import base64
import json
import socket
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import time

import httpx
import pytest

from pokelab import agent_providers as p
from pokelab import agent_qualification as q


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def reject(*args, **kwargs): raise AssertionError('Live sockets forbidden in tests')
    monkeypatch.setattr(socket.socket, 'connect', reject)
    for provider in p.PROVIDERS.values():
        if provider.variable: monkeypatch.delenv(provider.variable, raising=False)
    monkeypatch.delenv('POKELAB_7B_LIVE_AUTHORIZATION', raising=False)


def selection(provider='gemini', model='gemini-3.5-flash-lite'):
    return p.Selection(provider=provider, model=model)


def wire(text='hello', **extra):
    return {'choices':[{'message':{'content':text},'finish_reason':'stop'}], **extra}


@pytest.mark.parametrize('provider', list(p.PROVIDERS))
def test_all_providers_mock_without_credentials(provider, monkeypatch):
    config=p.PROVIDERS[provider]
    if config.variable: monkeypatch.setenv(config.variable, 'fixture-credential-never-transmitted')
    seen=[]
    def respond(request):
        seen.append(request)
        assert 'authorization' not in request.headers and 'x-api-key' not in request.headers
        data=json.loads(request.content)
        assert data['stream'] is False and not any(k in data for k in ('tools','tool_choice'))
        if config.anthropic:
            assert data['system']=='contract' and data['messages']==[{'role':'user','content':'case'}]
            return httpx.Response(200,json={'content':[{'type':'text','text':'answer'}], 'usage':{'input_tokens':10,'output_tokens':5}})
        assert data['messages']==[{'role':'system','content':'contract'},{'role':'user','content':'case'}]
        if provider=='openrouter': assert data['provider']['max_price']==dict(prompt=0,completion=0,request=0)
        return httpx.Response(200,json=wire('answer',usage={'prompt_tokens':10,'completion_tokens':5,'completion_tokens_details':{'reasoning_tokens':2}}))
    result=p.complete(selection(provider,'fixture-model'),'contract','case',transport=httpx.MockTransport(respond))
    assert result.status=='ok' and result.input_tokens==10 and result.output_tokens==5
    assert str(seen[0].url)==config.endpoint and len(seen)==1
    assert result.actual_cost_usd is None


@pytest.mark.parametrize('provider', list(p.PROVIDERS))
def test_real_calls_blocked_without_pm_authorization(provider):
    assert p.complete(selection(provider),'contract','case').status=='live_not_authorized'


@pytest.mark.parametrize('provider', ['openai','anthropic','xai','mistral','deepseek'])
def test_paid_providers_stay_disabled(provider, monkeypatch):
    monkeypatch.setenv('POKELAB_7B_LIVE_AUTHORIZATION','PM_APPROVED_ZERO_COST')
    assert p.complete(selection(provider),'contract','case').status=='paid_provider_disabled'


def test_free_gates(monkeypatch):
    monkeypatch.setenv('POKELAB_7B_LIVE_AUTHORIZATION','PM_APPROVED_ZERO_COST')
    assert p.live_gate(selection())=='free_tier_not_confirmed'
    monkeypatch.setenv('POKELAB_GEMINI_FREE_TIER_CONFIRMED','NO_BILLING')
    assert p.live_gate(selection()) is None
    assert p.live_gate(selection(model='arbitrary-paid-model'))=='model_not_free_qualified'
    assert p.live_gate(selection(model='gemini-2.5-flash-lite'))=='model_not_free_qualified'
    assert p.live_gate(selection(model='gemini-2.5-flash'))=='model_not_free_qualified'
    assert p.live_gate(selection('openrouter','openrouter/free'))=='explicit_free_model_required'
    assert p.live_gate(selection('openrouter','org/name'))=='explicit_free_model_required'
    assert p.live_gate(selection('openrouter','org/name:free')) is None
    monkeypatch.setenv('POKELAB_OLLAMA_LOCAL_CONFIRMED','LOCAL_ONLY')
    assert p.live_gate(selection('ollama','local:8b')) is None
    assert p.live_gate(selection('ollama','local-cloud'))=='local_model_required'
    assert p.live_gate(selection('ollama','org/name'))=='local_model_required'


@pytest.mark.parametrize('code',[301,401,429,500])
def test_http_errors_are_not_captured_or_retried(code):
    calls=[]
    def respond(request):
        calls.append(request)
        return httpx.Response(code,text='private error body',headers={'location':'https://other.invalid'})
    result=p.complete(selection(),'s','u',transport=httpx.MockTransport(respond))
    assert result.status==f'http_{code}' and len(calls)==1
    assert 'private' not in result.model_dump_json()


@pytest.mark.parametrize('payload,status',[
    ({},'transport_or_response_error'), (wire(None),'empty_output'),
    (wire('x'*17000),'output_too_large'),
    ({'choices':[{'message':{'tool_calls':[{}]}}]},'tool_output_rejected'),
])
def test_bad_outputs(payload,status):
    result=p.complete(selection(),'s','u',transport=httpx.MockTransport(lambda r:httpx.Response(200,json=payload)))
    assert result.status==status


def test_timeout_size_and_budget():
    def timeout(request): raise httpx.ReadTimeout('private exception detail',request=request)
    assert p.complete(selection(),'s','u',transport=httpx.MockTransport(timeout)).status=='transport_or_response_error'
    assert p.complete(selection(),'s','u',transport=httpx.MockTransport(lambda r:httpx.Response(200,content=b'x'*131073))).status=='response_too_large'
    assert p.complete(selection(),'s'*32769,'u').status=='request_budget_exceeded'
    assert p.complete(selection(),'s','u',transport=object()).status=='unsupported_transport'


@pytest.mark.parametrize('encoded',[False,True])
def test_secret_quarantine_in_any_response_field(monkeypatch,caplog,encoded):
    secret='synthetic-sensitive-marker-987654'
    monkeypatch.setenv('POKELAB_GEMINI_API_KEY',secret)
    value=base64.b64encode(secret.encode()).decode() if encoded else secret
    result=p.complete(selection(),'s','u',transport=httpx.MockTransport(lambda r:httpx.Response(200,json=wire('safe',unused={'hidden':value}))))
    assert result.status=='secret_response_quarantined'
    assert value not in result.model_dump_json()+caplog.text
    assert p.complete(selection(),'s',value).status=='secret_input_rejected'


def test_frozen_hash_and_tamper(tmp_path):
    packet=q.load_case()
    data=packet.model_dump(mode='json'); data['request']['question']='changed'
    path=tmp_path/'case.json'; path.write_text(json.dumps(data),encoding='utf-8')
    with pytest.raises(ValueError,match='frozen_case_mismatch'): q.load_case(path)


def test_serial_identical_inputs_and_pending_review():
    requests=[]; packet=q.load_case()
    def factory(s):
        delegate=q.mock_transport(packet,s.provider)
        def respond(request):
            data=json.loads(request.content)
            messages=data['messages']
            system=data.get('system') or messages[0]['content']
            user=messages[-1]['content']
            requests.append((system,user))
            return delegate.handle_request(request)
        return httpx.MockTransport(respond)
    report=q.run([selection(p,'fixture-model') for p in p.PROVIDERS],transport_factory=factory)
    assert len(requests)==8 and len(set(requests))==1
    assert all(r['grounding_correct'] and r['rules_boundary_compliant'] and r['evidence_references_valid'] for r in report['records'])
    assert all(r['qualification']=='PENDING_PM_REVIEW' and r['usefulness']=='PM_REVIEW_REQUIRED' for r in report['records'])
    assert report['mode']=='MOCK_NOT_QUALIFICATION'
    assert 'text' not in report['records'][0]


def test_concurrent_runs_are_serialized():
    active=0; peak=0; lock=Lock(); packet=q.load_case()
    def factory(s):
        delegate=q.mock_transport(packet,s.provider)
        def respond(request):
            nonlocal active,peak
            with lock: active+=1; peak=max(peak,active)
            time.sleep(.01)
            try: return delegate.handle_request(request)
            finally:
                with lock: active-=1
        return httpx.MockTransport(respond)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:q.run([selection()],transport_factory=factory),range(2)))
    assert len(results)==2 and peak==1


@pytest.mark.parametrize('mutation',['rules','facts','citations','duplicate','invalid','prose'])
def test_assessment_boundaries(mutation):
    packet=q.load_case()
    response=p.complete(selection(),'s','u',transport=q.mock_transport(packet,'gemini'))
    data=json.loads(response.text)
    if mutation=='rules': data['rules']['gameplay_status']='REVIEWED'
    if mutation=='facts': data['facts']['active_quantity']=3
    if mutation=='citations': data['citations']['rules']=data['citations']['deck']
    if mutation=='prose': data['summary']='An unsupported prose claim requires human review.'
    text=json.dumps(data)
    if mutation=='duplicate': text=text[:-1]+',"summary":"duplicate"}'
    if mutation=='invalid': text='not json'
    assessment=q.assess(text,packet)
    assert assessment['qualification']==('PENDING_PM_REVIEW' if mutation=='prose' else 'FAIL')
    assert assessment['hallucinations']=='PM_REVIEW_REQUIRED'


def test_no_live_transport_override_and_stop(monkeypatch):
    with pytest.raises(ValueError,match='live_transport_override_forbidden'):
        q.run([selection()],live=True,transport_factory=lambda s:None)
    calls=[]
    def fake_complete(*args,**kwargs):
        calls.append(1)
        return p.Response(status='nonzero_cost_reported_stop',latency_ms=0,actual_cost_usd=.01)
    monkeypatch.setattr(q,'complete',fake_complete)
    report=q.run([selection(),selection()],live=True)
    assert len(calls)==1 and report['records'][0]['actual_cost_usd']==.01


def test_unknown_usage_is_not_zero():
    response=p.complete(selection(),'s','u',transport=httpx.MockTransport(lambda r:httpx.Response(200,json=wire())))
    assert response.input_tokens is None and response.output_tokens is None and response.reasoning_tokens is None


def test_json_unicode_secret_and_truncation(monkeypatch):
    secret='synthetic-sensitive-marker-987654'
    monkeypatch.setenv('POKELAB_GEMINI_API_KEY',secret)
    encoded=''.join('\\u%04x'%ord(c) for c in secret)
    raw=json.dumps(wire('PLACEHOLDER')).replace('PLACEHOLDER',encoded)
    response=p.complete(selection(),'s','u',transport=httpx.MockTransport(lambda r:httpx.Response(200,text=raw)))
    assert response.status=='secret_response_quarantined'
    body=wire(); body['choices'][0]['finish_reason']='length'
    assert p.complete(selection(),'s','u',transport=httpx.MockTransport(lambda r:httpx.Response(200,json=body))).status=='incomplete_or_blocked_output'


def test_contract_tamper(monkeypatch):
    monkeypatch.setattr(q,'SYSTEM',q.SYSTEM+' changed')
    with pytest.raises(ValueError,match='frozen_contract_mismatch'): q.run([selection()])


def test_gemini_corrected_wire_contract_and_frozen_input():
    packet=q.load_case()
    delegate=q.mock_transport(packet,'gemini')
    def respond(request):
        assert request.method=='POST'
        assert str(request.url)=='https://generativelanguage.googleapis.com/v1beta/openai/chat/completions'
        data=json.loads(request.content)
        assert data['model']=='gemini-3.5-flash-lite'
        system,user,hashed=q.inputs(packet)
        assert hashed=='389165b46a93ce34ea62853b5d49beeaf7c45c4875a16bbcfb8fb46631719432'
        assert data['messages']==[{'role':'system','content':system},{'role':'user','content':user}]
        return delegate.handle_request(request)
    report=q.run([selection()],transport_factory=lambda s:httpx.MockTransport(respond))
    assert report['records'][0]['status']=='ok'


def test_404_not_a_model_qualification_failure():
    report=q.run([selection()],transport_factory=lambda s:httpx.MockTransport(
        lambda r:httpx.Response(404,text='private provider error must not be retained')))
    record=report['records'][0]
    assert record['status']=='http_404'
    assert record['qualification']=='NOT_EVALUATED'
    assert record['failure_category']=='PRE_INFERENCE_TRANSPORT_CONFIGURATION'
    for key in ('grounding_correct','rules_boundary_compliant','evidence_references_valid',
                'input_tokens','output_tokens','actual_cost_usd','reported_model','answer'):
        assert record[key] is None
    assert 'private provider error' not in json.dumps(report)


def test_cli_mock_and_secret_configuration(monkeypatch,capsys):
    monkeypatch.setattr(sys,'argv',['qualification'])
    assert q.main()==0
    report=json.loads(capsys.readouterr().out)
    assert len(report['records'])==8 and report['mode']=='MOCK_NOT_QUALIFICATION'
    secret='synthetic-marker-not-a-model'
    monkeypatch.setenv('POKELAB_GEMINI_API_KEY',secret)
    monkeypatch.setenv('POKELAB_GEMINI_MODEL',secret)
    monkeypatch.setattr(sys,'argv',['qualification','--live','--provider','gemini'])
    assert q.main()==1
    assert secret not in capsys.readouterr().out
