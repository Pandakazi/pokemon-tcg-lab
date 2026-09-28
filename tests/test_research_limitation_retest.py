"""Exact PM sentences through assessment and the real product API, offline."""
from datetime import date
import json
from pathlib import Path
import socket

import httpx
import pytest
from fastapi.testclient import TestClient

from pokelab import agent_research as a, research_grounding as grounding
from pokelab.agent_providers import Selection
from pokelab.api import create_app
from test_agent_context import setup
from test_research import research, KEY, TODAY

COMPOSITION = 'The active deck contains no Charizard ex cards, as its featured primary Pokémon is Dragapult ex.'
CONTRADICTION = 'The question assumes a premise about Charizard ex that contradicts the supplied deck composition and evidence.'
EPISTEMIC = 'Creator intent cannot be established from the supplied evidence.'
CASES = [(COMPOSITION, False), (CONTRADICTION, False), (EPISTEMIC, True)]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    original=socket.socket.connect
    def blocked(sock,address):
        if isinstance(address,tuple) and address[0] in ('127.0.0.1','::1'):
            return original(sock,address)  # Windows event-loop setup only.
        raise AssertionError('External network forbidden')
    monkeypatch.setattr(socket.socket,'connect',blocked)
    monkeypatch.setattr(socket.socket,'connect_ex',blocked)
    class FixedDate(date):
        @classmethod
        def today(cls): return TODAY
    monkeypatch.setattr(a,'date',FixedDate)


def output(limitation,outcome='unsupported_question'):
    return dict(version='pokelab-research-answer-v1',outcome=outcome,
        facts=[dict(text='The supplied snapshot records the active deck.',evidence=['active-deck'])] if outcome=='answered' else [],
        interpretation=[],limitations=[limitation])


@pytest.mark.parametrize('outcome',['unsupported_question','insufficient_evidence','answered'])
@pytest.mark.parametrize('limitation,accepted',CASES)
def test_exact_sentences_all_outcomes(limitation,accepted,outcome):
    envelope=a.Envelope.model_validate_json((Path(__file__).parent/'fixtures/agent_research_budew_revision157.json').read_text(encoding='utf-8'))
    payload=output(limitation,outcome)
    parsed=a.Answer.model_validate(payload)
    assert grounding.violation(parsed,envelope)==(None if accepted else 'uncited_limitation_claim')
    if accepted:
        assert a.assess(json.dumps(payload),envelope).outcome==outcome
    else:
        with pytest.raises(a.ContractError) as exc:
            a.assess(json.dumps(payload),envelope)
        assert exc.value.diagnostics==dict(condition='uncited_limitation_claim',json_parsed=True,schema_valid=True)


@pytest.mark.parametrize('scope',['active_deck_research','selected_card_research'])
@pytest.mark.parametrize('limitation,accepted',CASES)
def test_real_api_unsupported_answer_always_runs_guard(setup,monkeypatch,scope,limitation,accepted):
    sources,_=setup;calls=[];guard_calls=[]
    original=grounding.violation
    def traced(answer,envelope):
        guard_calls.append(answer.outcome)
        return original(answer,envelope)
    monkeypatch.setattr(grounding,'violation',traced)
    def fake(request):
        calls.append(request)
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(output(limitation))},'finish_reason':'stop'}],
            'usage':{'prompt_tokens':123,'completion_tokens':45}})
    app=create_app(database=sources.paths['cards'],state_database=sources.paths['collection'],
        competitive_database=sources.paths['competitive'],deck_database=sources.paths['workspace'])
    app.state.research_agent=a.ResearchService(sources.paths,
        selection=Selection(provider='gemini',model='gemini-3.5-flash-lite'),transport=httpx.MockTransport(fake))
    query=dict(scope=scope,question='Why is this deck built around Charizard ex?',revision=7,window='30')
    if scope=='active_deck_research': query['archetype']=KEY
    else: query['printing']='sm2-1'
    with TestClient(app) as client:
        response=client.post('/api/v1/agent/research',json=query)
    assert response.status_code==200
    result=response.json()
    assert len(calls)==1 and guard_calls==['unsupported_question']
    assert result['execution']['input_tokens']==123 and result['execution']['finish_reason']=='stop'
    if accepted:
        assert result['status']=='unsupported_question' and result['answer']==output(limitation)
    else:
        assert result['status']=='invalid_answer_contract' and result['answer'] is None
        assert result['contract_diagnostics']['condition']=='uncited_limitation_claim'
        assert limitation not in json.dumps(result,ensure_ascii=False)
