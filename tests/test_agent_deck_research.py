"""Product integration over real deterministic local fixtures, never live providers."""
from datetime import date
import json
import socket
import httpx
import pytest
from fastapi.testclient import TestClient
from pokelab import agent_research as a, deck_research as d
from pokelab.agent_providers import Selection
from pokelab.agent_qualification_config import INPUT_BYTES
from pokelab.api import create_app
from test_agent_context import setup
from test_research import research, KEY, TODAY, seed


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    original=socket.socket.connect
    def blocked(sock,address):
        if isinstance(address,tuple) and address[0] in ('127.0.0.1','::1'): return original(sock,address)
        raise AssertionError('Network forbidden')
    monkeypatch.setattr(socket.socket,'connect',blocked)
    monkeypatch.setattr(socket.socket,'connect_ex',blocked)
    class FixedDate(date):
        @classmethod
        def today(cls): return TODAY
    monkeypatch.setattr(a,'date',FixedDate)


def query(question='How does this deck differ from typical Dragapult decks?', **kw):
    return a.ResearchRequest(scope='active_deck_research',question=question,revision=7,archetype=KEY,**kw)


def service(sources,case='valid'):
    calls=[]
    def handle(request):
        body=json.loads(request.content); calls.append(body)
        assert 'authorization' not in request.headers
        assert body['response_format']['json_schema']['schema']==a.Answer.model_json_schema()
        system,user=(m['content'] for m in body['messages'])
        assert len((system+user).encode())<=INPUT_BYTES
        assert 'Never propose replacements, deck edits' in system
        assert 'creator intent' in system and 'matchup performance' in system
        e=json.loads(user)
        answer=dict(version='pokelab-research-answer-v1',outcome='answered',
            facts=[dict(text='The supplied snapshot records this active deck.',evidence=['active-deck',e['packet']['evidence'][0]['id']])],
            interpretation=[],limitations=['Creator intent is unavailable.'])
        if case=='unsupported': answer.update(outcome='unsupported_question',facts=[])
        if case=='citation': answer['facts'][0]['evidence']=['ref-invented']
        if case=='schema': del answer['facts']
        text=json.dumps(answer)
        if case=='json': text='PRIVATE_INVALID_PROSE'
        return httpx.Response(200,json={'choices':[{'message':{'content':text},'finish_reason':'length' if case=='truncation' else 'stop'}],
            'usage':{'prompt_tokens':100,'completion_tokens':50}})
    return a.ResearchService(sources.paths,selection=Selection(provider='gemini',model='gemini-3.5-flash-lite'),transport=httpx.MockTransport(handle)),calls


@pytest.mark.parametrize('question',[
    'How does this deck differ from typical Dragapult decks?',
    'What is this deck trying to do?',
    'What cards in this deck are unusual for Dragapult?',
    'What common Dragapult cards is this deck not playing?',
    'Which cards does this deck run more or fewer copies of than usual?',
    'Why might this deck run two Risky Ruins?',
    'Why did Rohit Potti build the deck this way?',
    'Why is this deck built around Charizard ex?',
    'What should I cut to improve this deck?',
])
def test_golden_deck_context_uses_foundation_unchanged(setup,question):
    sources,_=setup;before={k:p.read_bytes() for k,p in sources.paths.items()}
    svc,calls=service(sources,'unsupported' if 'cut' in question else 'valid')
    result=svc.run(query(question))
    assert result['status'] in ('answered','unsupported_question'),result
    assert len(calls)==1
    expected=d.select_evidence(d.build_profile(sources,revision=7,as_of=TODAY,archetype=KEY),question)
    assert result['envelope']['packet']==expected.model_dump(mode='json')
    assert result['snapshot']['eligible_lists']==16 and result['snapshot']['excluded_unmapped']==1
    assert result['snapshot']['packet_hash']==expected.content_hash
    assert result['snapshot']['self_comparison']=='unavailable'
    assert len(result['snapshot']['source_reference_sample'])==10
    assert result['envelope']['active_deck']['total']==60
    assert all(c['name'] not in ('Charizard ex','Risky Ruins') for c in result['envelope']['active_deck']['entries'])
    assert before=={k:p.read_bytes() for k,p in sources.paths.items()}


@pytest.mark.parametrize('case,expected',[
    ('json','invalid_answer_contract'),('schema','invalid_answer_contract'),
    ('citation','invalid_answer_contract'),('truncation','output_token_limit_reached')])
def test_fail_closed_existing_validator_and_metadata(setup,case,expected):
    svc,calls=service(setup[0],case);result=svc.run(query())
    assert result['status']==expected and result['answer'] is None and len(calls)==1
    assert result['execution']['output_tokens']==50
    assert 'PRIVATE_INVALID_PROSE' not in json.dumps(result)
    if case!='truncation':
        assert result['contract_diagnostics']['condition']=={'json':'json_syntax','schema':'schema_validation','citation':'invalid_reference'}[case]


def test_missing_archetype_blocks_comparison_but_not_composition(setup):
    svc,calls=service(setup[0])
    for key in (None,'invented'):
        result=svc.run(query().model_copy(update={'archetype':key}))
        assert result['status']=='comparison_unavailable' and not calls
    result=svc.run(query('What is this deck trying to do?').model_copy(update={'archetype':None}))
    assert result['status']=='answered' and len(calls)==1
    assert result['snapshot']['archetype'] is None


def test_current_sync_changes_population_without_code_or_fixture_changes(setup):
    svc,_=service(setup[0]);before=svc.run(query())
    seed(setup[1],[1,2],event='new-sync')
    after=svc.run(query())
    assert before['snapshot']['eligible_lists']==16 and after['snapshot']['eligible_lists']==18
    assert before['snapshot']['packet_hash']!=after['snapshot']['packet_hash']
    assert before['snapshot']['snapshot_hash']!=after['snapshot']['snapshot_hash']


def test_status_api_context_and_revision_protection(setup):
    sources,_=setup;svc,calls=service(sources)
    status=svc.status()
    assert status['scopes']==['selected_card_research','active_deck_research']
    assert status['archetypes']==[dict(id=KEY,name='Fixture Archetype')]
    app=create_app(database=sources.paths['cards'],state_database=sources.paths['collection'],competitive_database=sources.paths['competitive'],deck_database=sources.paths['workspace'])
    app.state.research_agent=svc
    with TestClient(app) as client:
        assert client.post('/api/v1/agent/research',json=query().model_dump()).json()['status']=='answered'
        assert client.post('/api/v1/agent/research',json=query().model_copy(update={'revision':8}).model_dump()).json()['status']=='context_changed'
        assert client.post('/api/v1/agent/research',json={'scope':'selected_card_research','question':'x','revision':7}).status_code==422
    assert len(calls)==1


def test_deck_prompt_examples_and_contract_reused(setup):
    import re
    envelope,_=a.make_deck_envelope(query(),setup[0],TODAY)
    examples=re.findall(r'^\{.*\}$',a.DECK_SYSTEM,re.M)
    assert examples
    for example in examples: assert a.assess(example,envelope).outcome=='insufficient_evidence'


def test_selected_budew_golden_retains_selected_card_pipeline(setup):
    from copy import deepcopy
    import sqlite3
    from tcg_lab.card_db import SQLiteCards
    from pokelab.decks import deck_identity
    from test_agent_research import service as selected_service
    sources,research=setup
    store=SQLiteCards(sources.paths['cards']);raw=deepcopy(store.get('sm2-1')['card'])
    raw.update(id='me02.5-221',name='Budew',variants={'holo':True},set={'id':'me02.5'},localId='221');store.put(raw)
    record=research.collection.catalog()[0]['me02.5-221']
    with sqlite3.connect(sources.paths['workspace']) as db:
        document=json.loads(db.execute('SELECT document FROM workspace').fetchone()[0])
        document['entries'][0].update(identity=deck_identity(record),name='Budew',allocations=[dict(printing_id='me02.5-221',variant='holo',quantity=4)])
        db.execute('UPDATE workspace SET document=?',(json.dumps(document),))
    result=selected_service(sources,provider='gemini',model='gemini-3.5-flash-lite').run(a.ResearchRequest(
        question="What's the point of running Budew in this deck?",printing='me02.5-221',variant='holo',revision=7))
    assert result['status']=='answered'
    assert result['envelope']['packet']['request']['printing']=='me02.5-221'
    assert result['envelope']['packet']['request']['variant']=='holo'
    assert 'snapshot' not in result


def test_internal_assessment_and_combined_prompt_budget_remain_bounded(setup,monkeypatch):
    svc,calls=service(setup[0])
    def fail(*args): raise RuntimeError('PRIVATE_EXCEPTION')
    monkeypatch.setattr(a,'assess',fail)
    result=svc.run(query())
    assert result['status']=='internal_assessment_failure' and result['answer'] is None
    assert result['execution']['output_tokens']==50 and 'PRIVATE_EXCEPTION' not in json.dumps(result)
    monkeypatch.setattr(a,'DECK_SYSTEM','x'*32768)
    result=svc.run(query())
    assert result['status']=='budget_exceeded' and len(calls)==1


def test_deck_secret_input_does_not_reach_provider(setup,monkeypatch):
    monkeypatch.setenv('POKELAB_GEMINI_API_KEY','fixture-secret-never-send')
    svc,calls=service(setup[0])
    assert svc.run(query('What is this deck trying to do? fixture-secret-never-send'))['status']=='secret_input_rejected'
    assert not calls
