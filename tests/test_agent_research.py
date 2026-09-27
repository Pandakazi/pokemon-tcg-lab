"""Product research tests use real local fixtures and fake provider transport only."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import json
import socket
import sqlite3
from threading import Event

import httpx
import pytest
from fastapi.testclient import TestClient

from pokelab import agent_research as agent
from pokelab.agent_providers import Selection
from pokelab.api import create_app
from pokelab.rules.models import digest
from test_agent_context import setup
from test_research import research, TODAY


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    original=socket.socket.connect
    def blocked(sock, address):
        # Windows event-loop initialization needs its internal loopback pair.
        if isinstance(address,tuple) and address[0] in ('127.0.0.1','::1'):
            return original(sock,address)
        raise AssertionError('Network forbidden')
    monkeypatch.setattr(socket.socket, 'connect', blocked)
    monkeypatch.setattr(socket.socket, 'connect_ex', blocked)


def query(**changes):
    return agent.ResearchRequest(question='What role could this card play in my deck?', printing='sm2-1', revision=7, **changes)


def good(envelope):
    card = next(e for e in envelope['packet']['evidence'] if e['payload']['kind'] == 'card')
    return dict(version='pokelab-research-answer-v1', outcome='answered',
        facts=[dict(text='Selected card: ' + card['payload']['name'], evidence=[card['id']])],
        interpretation=[dict(text='A plausible role needs the printed effect and deck context.', evidence=[card['id'], 'active-deck'])],
        limitations=['Composition does not establish creator intent.'])


def service(sources, callback=None, provider='openrouter', model='organization/model:free'):
    def handle(request):
        body=json.loads(request.content)
        assert 'authorization' not in request.headers
        assert body['model'] == model and body['max_tokens'] == 4096
        if provider == 'openrouter':
            assert body['provider'] == {'allow_fallbacks':False,'max_price':{'prompt':0,'completion':0,'request':0}}
        envelope=json.loads(body['messages'][1]['content'])
        return callback(envelope) if callback else response(good(envelope))
    return agent.ResearchService(sources.paths, transport=httpx.MockTransport(handle), selection=Selection(provider=provider,model=model))


def response(answer=None, finish='stop'):
    return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(answer)},'finish_reason':finish}],
        'usage':{'prompt_tokens':100,'completion_tokens':50}})


@pytest.mark.parametrize('printing', ['sm2-1','sm2-3'])
def test_generalized_readonly_envelope_and_full_product_path(setup, printing, monkeypatch):
    sources,_=setup
    before={k:p.read_bytes() for k,p in sources.paths.items()}
    q=query().model_copy(update={'printing':printing})
    envelope=agent.make_envelope(q,sources,TODAY)
    assert envelope==agent.make_envelope(q,sources,TODAY)
    assert envelope.content_hash==digest(envelope.model_dump(mode='json',exclude={'content_hash'}))
    assert len(agent.canonical(envelope).encode())<=24576
    assert sum(e.quantity for e in envelope.active_deck.entries)==60
    assert len(envelope.active_deck.entries)==2
    assert all(e.card_content_hash and e.source=='TCGdex' for e in envelope.active_deck.entries)
    assert envelope.packet.schema_version==1
    assert envelope.packet.content_hash==digest(envelope.packet.model_dump(mode='json',exclude={'content_hash'}))
    connect=sqlite3.connect
    def readonly(path,*a,**kw):
        assert kw.get('uri') and '?mode=ro' in str(path)
        return connect(path,*a,**kw)
    monkeypatch.setattr(sqlite3,'connect',readonly)
    result=service(sources).run(q)
    assert result['status']=='answered',result
    assert result['answer']['facts'] and result['execution']['input_tokens']==100
    assert before=={k:p.read_bytes() for k,p in sources.paths.items()}


@pytest.mark.parametrize('provider,model',[('gemini','gemini-3.5-flash-lite'),('ollama','local-test'),('openrouter','another/family:free')])
def test_product_is_provider_neutral(setup,provider,model):
    assert service(setup[0],provider=provider,model=model).run(query())['status']=='answered'


@pytest.mark.parametrize('change,expected',[
    ({'revision':8},'context_changed'),({'printing':'sm2-2'},'selected_card_not_in_active_deck'),
    ({'printing':'missing-card'},'context_unavailable')])
def test_context_guard_never_calls_provider(setup,change,expected):
    def forbidden(_): pytest.fail('Provider must not run')
    assert service(setup[0],forbidden).run(query().model_copy(update=change))['status']==expected


def test_missing_workspace_is_not_initialized(setup):
    sources,_=setup;sources.paths['workspace']=sources.paths['workspace'].with_name('missing.sqlite3')
    assert service(sources).run(query())['status']=='context_unavailable'
    assert not sources.paths['workspace'].exists()


@pytest.mark.parametrize('finish',['length','max_tokens'])
def test_truncation_never_displays_partial_answer(setup,finish):
    result=service(setup[0],lambda e:response(good(e),finish)).run(query())
    assert result['status']=='output_token_limit_reached' and result['answer'] is None
    assert result['execution']['finish_reason']==finish and result['execution']['output_tokens']==50


@pytest.mark.parametrize('kind',['missing','reference','empty','unsupported_with_claims'])
def test_definitive_contract_failures(setup,kind):
    def invalid(e):
        a=good(e)
        if kind=='missing': del a['facts']
        if kind=='reference': a['facts'][0]['evidence']=['invented']
        if kind=='empty': a['facts']=[];a['interpretation']=[]
        if kind=='unsupported_with_claims': a['outcome']='unsupported_question'
        return response(a)
    r=service(setup[0],invalid).run(query())
    assert r['status']=='invalid_answer_contract' and r['answer'] is None
    assert 'raw' not in r and 'text' not in r['execution']


@pytest.mark.parametrize('exception',[RuntimeError,ValueError,TypeError])
def test_internal_assessment_never_becomes_model_failure(setup,monkeypatch,exception):
    def fail(*a): raise exception('SECRET raw model output')
    monkeypatch.setattr(agent,'assess',fail)
    r=service(setup[0]).run(query())
    assert r['status']=='internal_assessment_failure' and r['answer'] is None
    assert r['execution']['output_tokens']==50
    assert 'SECRET' not in json.dumps(r) and 'FAIL' not in json.dumps(r)


@pytest.mark.parametrize('code',[401,404,429,503])
def test_provider_failure_is_not_answer(setup,code):
    r=service(setup[0],lambda e:httpx.Response(code,json={'error':{'message':'arbitrary private data'}})).run(query())
    assert r['status']=='provider_failure' and r['answer'] is None
    assert 'arbitrary' not in json.dumps(r)


@pytest.mark.parametrize('outcome',['unsupported_question','insufficient_evidence'])
def test_nonanswer_outcomes_remain_explicit(setup,outcome):
    def reply(e):
        a=good(e);a.update(outcome=outcome,facts=[],interpretation=[])
        return response(a)
    assert service(setup[0],reply).run(query())['status']==outcome


def test_single_flight_no_queued_provider_call(setup):
    entered,release=Event(),Event()
    def hold(e):
        entered.set();assert release.wait(3)
        return response(good(e))
    s=service(setup[0],hold)
    with ThreadPoolExecutor(2) as pool:
        first=pool.submit(s.run,query());assert entered.wait(3)
        try: assert s.run(query())=={'status':'busy','answer':None}
        finally: release.set()
        assert first.result()['status']=='answered'


def test_secret_quarantine_and_disabled_default(setup,monkeypatch):
    sources,_=setup
    monkeypatch.delenv('POKELAB_RESEARCH_PROVIDER',raising=False)
    assert agent.ResearchService(sources.paths).status()['available'] is False
    monkeypatch.setenv('POKELAB_OPENROUTER_API_KEY','test-secret-value')
    r=service(sources).run(query().model_copy(update={'question':'test-secret-value'}))
    assert r=={'status':'secret_input_rejected','answer':None}
    r=service(sources,lambda e:response({'text':'test-secret-value'})).run(query())
    assert r['status']=='provider_failure' and 'test-secret-value' not in json.dumps(r)


def test_api_contract_and_origin_guard(setup):
    sources,_=setup
    app=create_app(database=sources.paths['cards'],state_database=sources.paths['collection'],
        competitive_database=sources.paths['competitive'],deck_database=sources.paths['workspace'])
    app.state.research_agent=service(sources)
    with TestClient(app) as client:
        assert client.get('/api/v1/agent/status').json()['available'] is True
        r=client.post('/api/v1/agent/research',json=query().model_dump())
        assert r.status_code==200 and r.json()['status']=='answered'
        assert client.post('/api/v1/agent/research',json=query().model_dump(),headers={'Origin':'https://evil.example'}).status_code==403
        assert client.post('/api/v1/agent/research',content='bad secret text',headers={'Content-Type':'application/json'}).json()=={'detail':'Invalid research context or question.'}
        assert client.post('/api/v1/agent/research',content='x'*8193,headers={'Content-Type':'application/json'}).status_code==413
        assert client.post('/api/v1/agent/research',data={'question':'x'}).status_code==415


def test_budget_and_snapshot_change_stop_before_inference(setup,monkeypatch):
    sources,_=setup
    def forbidden(_): pytest.fail('No provider call expected')
    monkeypatch.setattr(agent,'ENVELOPE_BYTES',1000)
    assert service(sources,forbidden).run(query())['status']=='budget_exceeded'
    monkeypatch.setattr(agent,'ENVELOPE_BYTES',24576)
    from pokelab import agent_context_sources
    sequence=iter(range(100))
    monkeypatch.setattr(agent_context_sources,'stamp',lambda path:next(sequence))
    assert service(sources,forbidden).run(query())['status']=='inconsistent_snapshot'


def test_reviewed_trainer_stays_profile_only(setup):
    sources,research=setup
    from pokelab.rules.registry import reviewed_sources
    from pokelab.decks import deck_identity
    printing=next(iter(reviewed_sources()))
    record=research.collection.catalog()[0][printing]
    with sqlite3.connect(sources.paths['workspace']) as db:
        document=json.loads(db.execute('SELECT document FROM workspace WHERE id=1').fetchone()[0])
        document['entries'].append(dict(identity=deck_identity(record),quantity=1,name=record['card']['name'],category=record['card']['category'],
            allocations=[dict(printing_id=printing,variant='normal',quantity=1)]))
        db.execute('UPDATE workspace SET document=?',(json.dumps(document),))
    e=agent.make_envelope(query().model_copy(update={'printing':printing}),sources,TODAY)
    rules=next(i.payload for i in e.packet.evidence if i.payload.kind=='rules')
    assert rules.review_support=='REVIEWED' and rules.status=='INSUFFICIENT_INFORMATION'
    assert rules.result_type=='profile-only' and rules.execution_authorized is False


def test_timeout_retains_single_flight_until_worker_exits(setup,monkeypatch):
    sources,_=setup;entered,release=Event(),Event()
    def hold(e):
        entered.set();assert release.wait(3)
        return response(good(e))
    monkeypatch.setattr(agent,'DEADLINE_SECONDS',0.2)
    app=create_app(database=sources.paths['cards'],state_database=sources.paths['collection'],
        competitive_database=sources.paths['competitive'],deck_database=sources.paths['workspace'])
    app.state.research_agent=service(sources,hold)
    with TestClient(app) as client:
        try:
            result=client.post('/api/v1/agent/research',json=query().model_dump()).json()
            assert entered.is_set() and result=={'status':'request_timeout','answer':None}
            assert client.post('/api/v1/agent/research',json=query().model_dump()).json()['status']=='busy'
        finally: release.set()


@pytest.mark.parametrize('case,condition', [
    ('fenced','json_syntax'), ('malformed','json_syntax'),
    ('missing','schema_validation'), ('wrong_type','schema_validation'),
    ('invalid_enum','schema_validation'), ('unknown_field','schema_validation'),
    ('reference_shape','schema_validation'), ('missing_reference','schema_validation'),
    ('source_reference','invalid_reference'), ('unknown_evidence','invalid_reference'),
    ('empty_limitations','schema_validation'), ('blank_limitation','invalid_limitations'),
    ('empty_statement','empty_statement'), ('empty_answer','empty_answer'),
    ('unsupported_claims','unsupported_with_claims'),
])
def test_bounded_contract_diagnostics_distinguish_rejections(setup,case,condition):
    def reply(e):
        a=good(e)
        if case=='missing': del a['version']
        if case=='wrong_type': a['facts']='PRIVATE_PROVIDER_PROSE'
        if case=='invalid_enum': a['outcome']='PRIVATE_INVALID_ENUM'
        if case=='unknown_field': a['PRIVATE_UNKNOWN_KEY']='PRIVATE_VALUE'
        if case=='reference_shape': a['facts'][0]['evidence']='PRIVATE_REFERENCE'
        if case=='missing_reference': del a['facts'][0]['evidence']
        if case=='source_reference': a['facts'][0]['evidence']=[e['packet']['references'][0]['id']]
        if case=='unknown_evidence': a['facts'][0]['evidence']=['ev-PRIVATE_UNKNOWN_ID']
        if case=='empty_limitations': a['limitations']=[]
        if case=='blank_limitation': a['limitations']=[' ']
        if case=='empty_statement': a['facts'][0]['text']=' '
        if case=='empty_answer': a.update(facts=[],interpretation=[])
        if case=='unsupported_claims': a['outcome']='unsupported_question'
        text=json.dumps(a)
        if case=='fenced': text='```json\n'+text+'\n```'
        if case=='malformed': text='{"PRIVATE_INCOMPLETE":'
        return httpx.Response(200,json={'choices':[{'message':{'content':text},'finish_reason':'stop'}],
            'usage':{'prompt_tokens':100,'completion_tokens':50}})
    result=service(setup[0],reply).run(query())
    assert result['status']=='invalid_answer_contract' and result['answer'] is None
    d=result['contract_diagnostics'];assert d['condition']==condition
    assert 'PRIVATE' not in json.dumps(d) and len(json.dumps(d))<2000
    assert result['execution']['finish_reason']=='stop' and result['execution']['output_tokens']==50
    if case=='fenced': assert d['markdown_fence_prefix'] and d['json_parsed'] is False
    if case=='unknown_field':
        assert d['json_parsed'] and d['statement_text_present'] and not d['schema_valid']
        assert d['errors'][0]=={'path':['<unknown_field>'],'condition':'extra_forbidden'}
    if case=='reference_shape': assert d['errors'][0]['path']==['facts','<item>','evidence']
    if case=='source_reference': assert d['source_reference_id_count']==1
    if condition=='invalid_reference': assert d['json_parsed'] and d['schema_valid']


def test_internal_pydantic_exception_is_not_output_contract_rejection(setup,monkeypatch):
    def internal_error(*args):
        agent.ResearchRequest.model_validate({'PRIVATE_INTERNAL_FIELD':'PRIVATE_INTERNAL_VALUE'})
    monkeypatch.setattr(agent,'assess',internal_error)
    result=service(setup[0]).run(query())
    assert result['status']=='internal_assessment_failure' and result['answer'] is None
    assert result['contract_diagnostics']=={'condition':'internal_assessment_error'}
    assert result['execution']['output_tokens']==50 and 'PRIVATE' not in json.dumps(result)


def test_diagnostic_failure_cannot_escape_or_become_model_rejection(setup,monkeypatch):
    def fail(*args): raise RuntimeError('PRIVATE exception text')
    monkeypatch.setattr(agent,'schema_diagnostics',fail)
    result=service(setup[0],lambda e:response({})).run(query())
    assert result['status']=='internal_assessment_failure' and 'PRIVATE' not in json.dumps(result)


def test_schema_diagnostics_bound_unknown_fields(setup):
    result=service(setup[0],lambda e:response({**good(e),**{f'PRIVATE_{i}':'PRIVATE' for i in range(30)}})).run(query())
    d=result['contract_diagnostics']
    assert d['error_count']==30 and len(d['errors'])==8
    assert 'PRIVATE' not in json.dumps(d)


@pytest.mark.parametrize('case,expected', [
    ('valid','answered'), ('fenced','json_syntax'), ('schema','schema_validation'),
    ('source_reference','invalid_reference'), ('internal','internal_assessment_error'),
])
def test_reconstructed_budew_revision157_regression(setup,monkeypatch,case,expected):
    from pathlib import Path
    envelope=agent.Envelope.model_validate_json((Path(__file__).parent/'fixtures/agent_research_budew_revision157.json').read_text(encoding='utf-8'))
    assert envelope.content_hash=='991a77f9439050275916f1933a169b7a5d886a4b1874c601e3381d9a2eb819f1'
    assert digest(envelope.model_dump(mode='json',exclude={'content_hash'}))==envelope.content_hash
    assert digest(envelope.packet.model_dump(mode='json',exclude={'content_hash'}))==envelope.packet.content_hash
    assert len(agent.canonical(envelope).encode())==17173
    request=envelope.packet.request
    assert (request.printing,request.variant,request.window,str(request.as_of))==('me02.5-221','holo','30','2026-09-26')
    assert envelope.active_deck.revision==157
    assert sum(e.quantity for e in envelope.active_deck.entries if e.name=='Budew')==2
    monkeypatch.setattr(agent,'make_envelope',lambda *a,**k:envelope)
    if case=='internal':
        def broken(*args): agent.ResearchRequest.model_validate({})
        monkeypatch.setattr(agent,'assess',broken)
    def reply(e):
        answer=good(e)
        if case=='schema': del answer['version']
        if case=='source_reference': answer['facts'][0]['evidence']=[e['packet']['references'][0]['id']]
        text=json.dumps(answer)
        if case=='fenced': text='```json\n'+text+'\n```'
        return httpx.Response(200,json={'choices':[{'message':{'content':text},'finish_reason':'stop'}],
            'usage':{'prompt_tokens':100,'completion_tokens':50}})
    result=service(setup[0],reply).run(agent.ResearchRequest(question=request.question,printing=request.printing,variant=request.variant,window=request.window,revision=157))
    if case=='valid': assert result['status']=='answered' and result['answer'] is not None
    else:
        assert result['answer'] is None and result['contract_diagnostics']['condition']==expected
        assert result['status']==('internal_assessment_failure' if case=='internal' else 'invalid_answer_contract')
    assert result['execution']['output_tokens']==50


@pytest.mark.parametrize('name,printing,variant,question',[
    ('Risky Ruins','me01-127','normal','what role does risky ruins play in this deck?'),
    ('Budew','me02.5-221','holo','What kinds of decks would Budew be most useful against?'),
    ('Crispin','sv08.5-171','holo','What would this deck lose if I removed Crispin?'),
])
@pytest.mark.parametrize('outcome',['valid','source_id','schema'])
def test_failed_question_shapes_do_not_determine_contract_acceptance(setup,name,printing,variant,question,outcome):
    # Synthetic local card fixtures, not reconstructed unknown model responses.
    # These verify request/diagnostic plumbing, not strategic answer quality.
    from tcg_lab.card_db import SQLiteCards
    from pokelab.decks import deck_identity
    sources,research=setup
    cards=SQLiteCards(sources.paths['cards']);raw=cards.get('sm2-1')['card']
    raw.update(id=printing,name=name,set={'id':printing.rsplit('-',1)[0]},localId=printing.rsplit('-',1)[1],variants={'normal':True,'holo':True})
    cards.put(raw);record=research.collection.catalog()[0][printing]
    with sqlite3.connect(sources.paths['workspace']) as db:
        document=json.loads(db.execute('SELECT document FROM workspace WHERE id=1').fetchone()[0])
        document['entries']=[dict(identity=deck_identity(record),quantity=2,name=name,category=raw['category'],allocations=[dict(printing_id=printing,variant=variant,quantity=2)])]
        db.execute('UPDATE workspace SET revision=157,document=?',(json.dumps(document),))
    before={k:p.read_bytes() for k,p in sources.paths.items()};calls=[]
    def reply(e):
        calls.append(1)
        assert e['packet']['request']['question']==question
        assert e['active_deck']['revision']==157
        a=good(e)
        if outcome=='source_id': a['facts'][0]['evidence']=[e['packet']['references'][0]['id']]
        if outcome=='schema': del a['facts']
        return response(a)
    result=service(sources,reply).run(agent.ResearchRequest(question=question,printing=printing,variant=variant,revision=157))
    assert len(calls)==1 and before=={k:p.read_bytes() for k,p in sources.paths.items()}
    if outcome=='valid': assert result['status']=='answered'
    else:
        assert result['status']=='invalid_answer_contract' and result['answer'] is None
        assert result['contract_diagnostics']['condition']==('invalid_reference' if outcome=='source_id' else 'schema_validation')
