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
from pokelab.agent_qualification_config import configuration, configuration_hash, V2_CANDIDATES


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


@pytest.mark.parametrize('mutation,path,condition',[
    ('missing_summary',['summary'],'missing'),
    ('wrong_count',['facts','sample_size'],'int_type'),
    ('wrong_boolean',['rules','execution_authorized'],'bool_type'),
    ('short_summary',['summary'],'string_too_short'),
    ('bad_citations',['citations','rules'],'tuple_type'),
    ('extra',['<unrecognized_key>'],'extra_forbidden'),
])
def test_contract_failure_structural_diagnostics(mutation,path,condition):
    packet=q.load_case()
    data=json.loads(p.complete(selection(),'s','u',transport=q.mock_transport(packet,'gemini')).text)
    if mutation=='missing_summary': del data['summary']
    elif mutation=='wrong_count': data['facts']['sample_size']='734'
    elif mutation=='wrong_boolean': data['rules']['execution_authorized']='false'
    elif mutation=='short_summary': data['summary']=''
    elif mutation=='bad_citations': data['citations']['rules']='private-citation-value'
    else: data['private-extra-key']='private-extra-value'
    result=q.assess(json.dumps(data),packet)
    diag=result['contract_diagnostics']
    assert result['qualification']=='FAIL' and result['answer'] is None
    assert diag['json_parsed'] is True and diag['schema_valid'] is False
    assert {'path':path,'condition':condition} in diag['errors']
    assert 'private' not in json.dumps(diag)


@pytest.mark.parametrize('text,parsed,condition',[
    ('```json\n{}\n```',False,'json_syntax'),
    ('A prose answer',False,'json_syntax'),
    ('{"summary":"first","summary":"second"}',True,'duplicate_json_key'),
    ('[]',True,'schema_validation'),
    ('{"answer":{"summary":"private prose"}}',True,'schema_validation'),
])
def test_wrapper_json_diagnostics(text,parsed,condition):
    result=q.assess(text,q.load_case())
    assert result['contract_diagnostics']['json_parsed'] is parsed
    assert result['contract_diagnostics']['condition']==condition
    assert result['answer'] is None and 'private prose' not in json.dumps(result)


def test_assessment_internal_failure_distinguishable(monkeypatch):
    packet=q.load_case()
    text=p.complete(selection(),'s','u',transport=q.mock_transport(packet,'gemini')).text
    def broken(*a): raise RuntimeError('private internal exception')
    monkeypatch.setattr(q,'expected',broken)
    result=q.assess(text,packet)
    assert result['contract_diagnostics']['schema_valid'] is True
    assert result['contract_diagnostics']['condition']=='schema_valid_assessment_failed'
    assert 'private internal' not in json.dumps(result)


def test_contract_diagnostics_secret_and_bounds(monkeypatch):
    marker='synthetic-contract-secret'
    monkeypatch.setenv('POKELAB_GEMINI_API_KEY',marker)
    assert q.contract_diagnostics(json.dumps({marker:'value'}))['condition']=='secret_quarantined'
    diag=q.contract_diagnostics(json.dumps({'untrusted-key-'+str(i):'private value' for i in range(100)}))
    assert len(diag['errors'])==12 and diag['error_count']>12
    assert 'untrusted-key' not in json.dumps(diag) and 'private value' not in json.dumps(diag)


@pytest.mark.parametrize('suite,limit',[('v1',1200),('v2',4096)])
def test_suite_global_budget_and_identical_inputs_all_providers(suite,limit):
    packet=q.load_case(); seen=[]
    def factory(s):
        delegate=q.mock_transport(packet,s.provider)
        def respond(request):
            body=json.loads(request.content)
            assert body.get('max_completion_tokens',body.get('max_tokens'))==limit
            messages=body['messages']
            seen.append((body.get('system',messages[0]['content']),messages[-1]['content']))
            return delegate.handle_request(request)
        return httpx.MockTransport(respond)
    report=q.run([selection(provider,'fixture-model') for provider in p.PROVIDERS],suite=suite,transport_factory=factory)
    assert len(seen)==8 and len(set(seen))==1 and seen[0]==q.inputs(packet)[:2]
    assert report['configuration_hash']==configuration_hash(suite)
    assert report['harness']=='pokelab-qualification-'+suite
    assert all(r['max_output_tokens']==limit and r['suite_hash']==report['suite_hash'] for r in report['records'])


def test_configuration_version_is_separate_from_frozen_inputs():
    assert configuration_hash('v1')=='4a10d3b66b6d264bb89f3e85cd64531d30d4351f61a1a4fdeaed3b7b373ff850'
    assert configuration_hash('v2')=='89dc98941ecc34d707cb9e63e8079e9ae2b3325ca5d14ca7d5dfb0b5b0e14323'
    before=configuration('v1'); after=configuration('v2')
    assert {k for k in before if before[k]!=after[k]}=={'suite','dimension','max_output_tokens'}
    before['max_output_tokens']=999
    assert configuration('v1')['max_output_tokens']==1200
    reports=[q.run([selection()],suite=v) for v in ('v1','v2')]
    assert reports[0]['input_hash']==reports[1]['input_hash']==q.INPUT_HASH
    assert reports[0]['packet_hash']==reports[1]['packet_hash']==q.PACKET_HASH
    assert reports[0]['configuration_hash']!=reports[1]['configuration_hash']
    assert reports[0]['suite_hash']!=reports[1]['suite_hash']
    assert reports[1]['suite_hash']=='ccb078a574f14c42b74ff07ea9993412009cf4866214c1be02b4bf8e621c4ee2'
    with pytest.raises(ValueError,match='unknown_suite'): q.run([selection()],suite='v3')


@pytest.mark.parametrize('provider,model',V2_CANDIDATES)
def test_v2_length_is_not_evaluated(provider,model,monkeypatch):
    body=wire('ungraded partial answer',model=model,usage={'prompt_tokens':4824,'completion_tokens':4096})
    body['choices'][0]['finish_reason']='length'
    def forbidden(*a,**k): raise AssertionError('No partial grading')
    monkeypatch.setattr(q,'assess',forbidden)
    report=q.run([selection(provider,model)],suite='v2',transport_factory=lambda s:httpx.MockTransport(lambda r:httpx.Response(200,json=body)))
    record=report['records'][0]
    assert record['qualification']=='NOT_EVALUATED' and record['failure_category']=='OUTPUT_TOKEN_LIMIT_REACHED'
    assert record['output_tokens']==4096 and record['finish_reason']=='length' and record['answer'] is None


def test_v2_prepared_candidates_only_and_live_gate(monkeypatch):
    for provider,model in V2_CANDIDATES:
        record=q.run([selection(provider,model)],suite='v2',live=True)['records'][0]
        assert record['status']=='live_not_authorized'
    with pytest.raises(ValueError,match='v2_candidate_not_prepared'):
        q.run([selection('openrouter','qwen/qwen3.8-27b:free')],suite='v2',live=True)
    with pytest.raises(ValueError,match='v2_candidate_not_prepared'):
        q.run([selection(),selection()],suite='v2',live=True)


def test_v2_mock_cli_prepares_exactly_two(monkeypatch,capsys):
    monkeypatch.setattr(sys,'argv',['qualification','--suite','v2'])
    assert q.main()==0
    report=json.loads(capsys.readouterr().out)
    assert [(r['provider'],r['model']) for r in report['records']]==list(V2_CANDIDATES)
    assert report['harness']=='pokelab-qualification-v2'
    assert report['configuration']['max_output_tokens']==4096


def test_transport_rejects_output_budget_above_v2():
    assert p.complete(selection(),'s','u',max_output=4097).status=='request_budget_exceeded'


@pytest.mark.parametrize('finish',['length','content_filter','error','unexpected-private-value'])
@pytest.mark.parametrize('content',[None,'','partial private response'])
def test_termination_diagnostics_without_partial_content(finish,content):
    model='nvidia/nemotron-3-super-120b-a12b:free'
    body=wire(content,model=model,provider='Nvidia',usage={'prompt_tokens':4700,'completion_tokens':1200,
        'completion_tokens_details':{'reasoning_tokens':1190}})
    body['choices'][0]['finish_reason']=finish
    report=q.run([selection('openrouter',model)],transport_factory=lambda s:httpx.MockTransport(lambda r:httpx.Response(200,json=body)))
    record=report['records'][0]
    assert record['status']=='incomplete_or_blocked_output' and record['qualification']=='NOT_EVALUATED'
    assert record['failure_category']==('OUTPUT_TOKEN_LIMIT_REACHED' if finish=='length' else 'RESPONSE_UNAVAILABLE_OR_EXECUTION_BLOCKED')
    assert record['diagnostics']['http_status']==200
    assert record['diagnostics']['finish_reason']==('other' if finish=='unexpected-private-value' else finish)
    assert record['input_tokens']==4700 and record['output_tokens']==1200 and record['reasoning_tokens']==1190
    assert record['reported_model']==model and record['diagnostics']['provider']=='Nvidia'
    assert record['answer'] is None
    assert 'partial private response' not in json.dumps(report) and 'unexpected-private-value' not in json.dumps(report)


def test_pm_nemotron_length_metadata_never_grades_partial_answer(monkeypatch):
    model='nvidia/nemotron-3-super-120b-a12b:free'
    body=wire('partial output must not be graded',model=model,provider='Nvidia',
        usage={'prompt_tokens':4824,'completion_tokens':1200})
    body['choices'][0]['finish_reason']='length'
    def forbidden(*args,**kwargs): raise AssertionError('Partial answer must not reach scoring')
    monkeypatch.setattr(q,'assess',forbidden)
    report=q.run([selection('openrouter',model)],transport_factory=lambda s:httpx.MockTransport(lambda r:httpx.Response(200,json=body)))
    record=report['records'][0]
    assert record['failure_category']=='OUTPUT_TOKEN_LIMIT_REACHED'
    assert record['qualification']=='NOT_EVALUATED'
    assert record['finish_reason']=='length' and record['input_tokens']==4824 and record['output_tokens']==1200
    assert record['reasoning_tokens'] is None and record['diagnostics']['http_status']==200
    assert record['answer'] is None and record['output_valid'] is None
    assert record['grounding_correct'] is None and record['rules_boundary_compliant'] is None
    assert record['evidence_references_valid'] is None
    assert report['input_hash']=='389165b46a93ce34ea62853b5d49beeaf7c45c4875a16bbcfb8fb46631719432'
    assert 'partial output must not be graded' not in json.dumps(report)


def test_empty_refusal_shape_and_absent_usage():
    body={'choices':[{'message':{'refusal':'private refusal prose'},'finish_reason':'stop'}]}
    response=p.complete(selection('openrouter'),'s','u',transport=httpx.MockTransport(lambda r:httpx.Response(200,json=body)))
    assert response.status=='empty_output'
    assert response.diagnostics['refusal_present']==1 and response.diagnostics['content_state']=='missing'
    assert response.diagnostics['usage_state']=='missing_or_null'
    assert response.input_tokens is None and 'private refusal' not in response.model_dump_json()


def test_termination_secret_still_quarantined(monkeypatch):
    marker='synthetic-sensitive-partial-output'
    monkeypatch.setenv('POKELAB_OPENROUTER_API_KEY',marker)
    body=wire(marker); body['choices'][0]['finish_reason']='length'
    response=p.complete(selection('openrouter'),'s','u',transport=httpx.MockTransport(lambda r:httpx.Response(200,json=body)))
    assert response.status=='secret_response_quarantined' and marker not in response.model_dump_json()


@pytest.mark.parametrize('nested',[False,True])
def test_openrouter_http200_error_not_generic(nested):
    error={'code':502,'message':'private upstream message','metadata':{'error_type':'provider_unavailable'}}
    body={'choices':[{'message':{'content':'partial'},'error':error}]} if nested else {'error':error}
    report=q.run([selection('openrouter','nvidia/nemotron-3-super-120b-a12b:free')],
        transport_factory=lambda s:httpx.MockTransport(lambda r:httpx.Response(200,json=body)))
    record=report['records'][0]
    assert record['status']=='provider_error' and record['qualification']=='NOT_EVALUATED'
    assert record['diagnostics']=={'error_code':502,'error_type':'provider_unavailable','stage':'response_envelope','http_status':200}
    assert 'private upstream' not in json.dumps(report)


@pytest.mark.parametrize('body,kind,stage',[(b'not json','invalid_json','parse_json'),
    (b'{}','invalid_response_shape','response_envelope'),(b'\xff','text_decode_error','decode_body')])
def test_response_stage_diagnostics(body,kind,stage):
    response=p.complete(selection('openrouter'),'s','u',transport=httpx.MockTransport(lambda r:httpx.Response(200,content=body)))
    assert response.diagnostics=={'stage':stage,'error_kind':kind,'http_status':200}


@pytest.mark.parametrize('error,kind',[(httpx.ConnectError,'connection_error'),(httpx.ReadTimeout,'timeout'),
    (httpx.RemoteProtocolError,'protocol_error')])
def test_transport_stage_diagnostics(error,kind):
    def respond(request): raise error('private exception text',request=request)
    response=p.complete(selection('openrouter'),'s','u',transport=httpx.MockTransport(respond))
    assert response.diagnostics=={'stage':'request','error_kind':kind}
    assert 'private' not in response.model_dump_json()


def test_openrouter_environment_auth_and_client_options_with_mock_client(monkeypatch):
    marker='synthetic-auth-marker-only'
    monkeypatch.setenv('POKELAB_OPENROUTER_API_KEY',marker)
    monkeypatch.setenv('OPENROUTER_API_KEY','wrong-variable-marker')
    monkeypatch.setenv('POKELAB_7B_LIVE_AUTHORIZATION','PM_APPROVED_ZERO_COST')
    original=httpx.Client; seen=[]
    def respond(request):
        seen.append(1)
        assert request.headers['authorization']=='Bearer '+marker
        assert request.headers['content-type']=='application/json'
        assert str(request.url)=='https://openrouter.ai/api/v1/chat/completions'
        return httpx.Response(200,json=wire())
    def client(**kwargs):
        assert kwargs=={'transport':None,'timeout':90,'follow_redirects':False,'trust_env':False}
        kwargs['transport']=httpx.MockTransport(respond)
        return original(**kwargs)
    monkeypatch.setattr(p.httpx,'Client',client)
    response=p.complete(selection('openrouter','nvidia/nemotron-3-super-120b-a12b:free'),'s','u')
    assert response.status=='ok' and seen==[1]
    assert marker not in response.model_dump_json()


@pytest.mark.parametrize('status',['http_400','http_401','http_402','http_403','http_404','http_429',
    'http_500','http_502','http_503','transport_or_response_error','secret_response_quarantined',
    'missing_credential','live_not_authorized','empty_output','incomplete_or_blocked_output','nonzero_cost_reported_stop'])
def test_unavailable_answers_never_scored(status,monkeypatch):
    monkeypatch.setattr(q,'complete',lambda *a,**k:p.Response(status=status,latency_ms=515))
    def forbidden(*a,**k): raise AssertionError('No answer to assess')
    monkeypatch.setattr(q,'assess',forbidden)
    report=q.run([selection('openrouter','qwen/qwen3.8-27b:free')])
    record=report['records'][0]
    assert record['qualification']=='NOT_EVALUATED'
    for key in ('output_valid','grounding_correct','evidence_references_valid','rules_boundary_compliant','answer'):
        assert record[key] is None
    assert record['unsupported_claims']==[] and record['hallucinations']=='NOT_EVALUATED'
    assert 'invalid_output_contract' not in json.dumps(record)
    if status=='http_429': assert record['failure_category']=='PRE_INFERENCE_PROVIDER_RATE_LIMIT_OR_CAPACITY'


def test_openrouter_allowlisted_error_diagnostics():
    body={'error':{'code':429,'message':'private error prose','metadata':{
        'error_type':'rate_limit_exceeded','provider_code':429,'raw':'private raw',
        'provider_name':'do not retain arbitrary strings'}}}
    transport=httpx.MockTransport(lambda r:httpx.Response(429,json=body,headers={
        'Retry-After':'30','X-RateLimit-Limit':'20','X-RateLimit-Remaining':'0',
        'X-RateLimit-Reset':'1790000000','x-private':'do not retain'}))
    report=q.run([selection('openrouter','qwen/qwen3.8-27b:free')],transport_factory=lambda s:transport)
    record=report['records'][0]
    assert record['diagnostics']=={'error_code':429,'provider_code':429,'error_type':'rate_limit_exceeded',
        'retry-after':30,'x-ratelimit-limit':20,'x-ratelimit-remaining':0,'x-ratelimit-reset':1790000000}
    assert record['qualification']=='NOT_EVALUATED' and 'private' not in json.dumps(report)


@pytest.mark.parametrize('where',['body','header','unicode'])
def test_error_diagnostics_quarantine(monkeypatch,where):
    secret='synthetic-secret-error-marker'
    monkeypatch.setenv('POKELAB_OPENROUTER_API_KEY',secret)
    raw=json.dumps({'error':{'code':429,'message':secret if where!='header' else 'limited'}})
    if where=='unicode': raw=raw.replace(secret,''.join('\\u%04x'%ord(c) for c in secret))
    transport=httpx.MockTransport(lambda r:httpx.Response(429,text=raw,headers={'Retry-After':secret if where=='header' else '30'}))
    response=p.complete(selection('openrouter'),'s','u',transport=transport)
    assert response.status=='http_429' and response.diagnostics=={'capture':'secret_quarantined'}
    assert secret not in response.model_dump_json()


@pytest.mark.parametrize('raw',['not json','x'*16385])
def test_bad_error_diagnostics_preserve_http_status(raw):
    response=p.complete(selection('openrouter'),'s','u',transport=httpx.MockTransport(lambda r:httpx.Response(429,text=raw)))
    assert response.status=='http_429' and response.diagnostics['capture'] in ('unavailable','oversized_discarded')


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


def test_openrouter_attempt2_exact_request_preserves_frozen_contract():
    packet=q.load_case(); calls=[]
    delegate=q.mock_transport(packet,'openrouter')
    def respond(request):
        calls.append(1)
        assert request.method=='POST'
        assert str(request.url)=='https://openrouter.ai/api/v1/chat/completions'
        data=json.loads(request.content)
        assert data['model']=='qwen/qwen3.8-27b:free'
        assert data['provider']=={'allow_fallbacks':False,'max_price':{'prompt':0,'completion':0,'request':0}}
        assert data['max_tokens']==1200 and data['stream'] is False
        assert set(data)=={'model','messages','provider','max_tokens','stream'}
        system,user,hashed=q.inputs(packet)
        assert hashed=='389165b46a93ce34ea62853b5d49beeaf7c45c4875a16bbcfb8fb46631719432'
        assert data['messages']==[{'role':'system','content':system},{'role':'user','content':user}]
        return delegate.handle_request(request)
    report=q.run([selection('openrouter','qwen/qwen3.8-27b:free')],
        transport_factory=lambda s:httpx.MockTransport(respond))
    assert len(calls)==1 and report['records'][0]['status']=='ok'


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
