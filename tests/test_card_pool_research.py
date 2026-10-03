"""Card-pool product path: actual printed fixtures and mocked provider only."""
import json
from pathlib import Path
import socket
import sqlite3
import httpx
import pytest
from fastapi.testclient import TestClient
from pokelab import agent_research as a, card_pool_research as p
from pokelab.agent_providers import Selection
from pokelab.api import create_app
from pokelab.deck_research import fields
from pokelab.research_grounding import fields as values
from tcg_lab.card_db import SQLiteCards
from test_agent_context import setup
from test_research import research, TODAY


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    original=socket.socket.connect
    def blocked(sock,address):
        if isinstance(address,tuple) and address[0] in ('127.0.0.1','::1'): return original(sock,address)
        raise AssertionError('External network forbidden')
    monkeypatch.setattr(socket.socket,'connect',blocked)
    monkeypatch.setattr(socket.socket,'connect_ex',blocked)


@pytest.fixture
def sources(setup):
    sources,_=setup
    fixture=json.loads((Path(__file__).parent/'fixtures/mechanics_standard_examples.json').read_text(encoding='utf-8'))
    store=SQLiteCards(sources.paths['cards'])
    for record in fixture['records']: store.put(record['card'])
    # The raw-card fixture omits separate set-series cache rows; preserve the
    # inspected corpus's TCG index provenance when installing this local fixture.
    with sqlite3.connect(sources.paths['cards']) as db:
        db.executemany("UPDATE cards SET game='tcg' WHERE id=?",[(r['card']['id'],) for r in fixture['records']])
    with sqlite3.connect(sources.paths['workspace']) as db:
        doc=json.loads(db.execute('SELECT document FROM workspace').fetchone()[0])
        doc['entries']=[dict(identity='fixture-budew',quantity=1,allocations=[dict(printing_id='me02.5-016',variant='normal',quantity=1)])]
        db.execute('UPDATE workspace SET document=?',(json.dumps(doc),))
    return sources


def query(question='What cards can mill my opponent?',**kw):
    return a.ResearchRequest(scope='card_pool_research',question=question,**kw)


def answer(envelope):
    item=next(e for e in envelope['packet']['evidence'] if e['kind']=='card-pool-candidate')
    payload=values(item['fields']);name=payload['name']
    return dict(version='pokelab-research-answer-v1',outcome='answered',
        facts=[dict(text=f"I'd start by looking at {name}. Its printed text says: "+payload['components'][0]['text'],evidence=[item['id']])],
        interpretation=[dict(text=f"{name} is worth researching for that printed effect; whether it fits your plan needs more context.",evidence=[item['id']])],
        limitations=['The supplied evidence does not establish tournament success or a matchup plan.'])


def pool_response(legacy,envelope):
    """Test-only adaptation of authored v1 claim fixtures to required v2 items."""
    return dict(version='pokelab-card-pool-answer-v2',outcome=legacy['outcome'],
        candidates=[e['id'] for e in envelope['packet']['evidence'] if e['kind']=='card-pool-candidate'] if legacy['outcome']!='unsupported_question' else [],
        synthesis=[dict(**s,required=True) for s in legacy['facts']+legacy['interpretation']],
        limitations=legacy['limitations'])


def service(sources,transform=lambda x:x,finish='stop'):
    calls=[]
    def handle(request):
        body=json.loads(request.content);calls.append(body)
        assert 'authorization' not in request.headers
        assert body['provider']=={'allow_fallbacks':False,'max_price':{'prompt':0,'completion':0,'request':0}}
        assert body['max_tokens']==4096
        assert body['messages'][0]['content']==a.POOL_SYSTEM
        envelope=json.loads(body['messages'][1]['content'])
        assert len((a.POOL_SYSTEM+json.dumps(envelope,ensure_ascii=False,separators=(',',':'))).encode())<=32768
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(pool_response(transform(answer(envelope)),envelope))},'finish_reason':finish}]})
    return a.ResearchService(sources.paths,selection=Selection(provider='openrouter',model='fixture/model:free'),transport=httpx.MockTransport(handle)),calls


@pytest.mark.parametrize('question,context',[
    ('What are some really good cards if I wanted to make a milling Pokemon deck for Standard format tournament play?',{}),
    ('What cards can mill my opponent?',{}),('What cards can mill me?',{}),
    ('I want to build around moving damage counters. What cards should I research?',{}),
    ('What cards could help a deck that tries to deny my opponent Energy?',{}),
    ('What other cards do something like Budew?',{'printing':'me02.5-016'}),
    ('Is there another card that stops players from using Tools?',{'printing':'me02.5-016'}),
    ('What other Pokemon move damage counters?',{'printing':'me02.5-099'}),
    ('What cards might support what this deck is trying to do?',{'include_deck':True,'revision':7}),
    ('Are there any weird cards in Standard that interact with the mechanics in this deck?',{'include_deck':True,'revision':7}),
])
def test_canonical_generalized_product_path(sources,question,context):
    before={k:v.read_bytes() for k,v in sources.paths.items()}
    svc,calls=service(sources);result=svc.run(query(question,**context))
    assert result['status']=='answered',result
    assert len(calls)==1
    envelope=result['envelope']
    assert len([e for e in envelope['packet']['evidence'] if e['kind']=='card-pool-candidate'])<=5
    assert 'catalog_names' not in envelope
    assert before=={k:v.read_bytes() for k,v in sources.paths.items()}


def test_open_needs_no_workspace_or_collection(sources):
    sources.paths['workspace']=sources.paths['workspace'].with_name('absent-workspace.sqlite3')
    sources.paths['collection']=sources.paths['collection'].with_name('absent-collection.sqlite3')
    svc,calls=service(sources);result=svc.run(query())
    assert result['status']=='answered' and result['envelope']['active_deck']=={} and len(calls)==1


@pytest.mark.parametrize('question,outcome',[
    ('Quantum banana transposition','insufficient_evidence'),
    ('How should I play Great Tusk Mill against Dragapult ex?','unsupported_question'),
    ('Replace a card in my deck','unsupported_question'),
])
def test_boundaries_do_not_infer_or_call(sources,question,outcome):
    svc,calls=service(sources);result=svc.run(query(question))
    assert result['status']==outcome and not calls
    assert not result['answer']['facts'] and not result['answer']['interpretation']


def test_tools_not_items_and_direction(sources):
    e=p.build(query('Is there another card that stops players from using Tools?',printing='me02.5-016'),sources,TODAY)
    assert e.packet.query['representations'][0]['concepts']==['tool_nullification']
    names=[values(i.model_dump()['fields'])['name'] for i in e.packet.evidence if i.kind=='card-pool-candidate']
    assert 'Jamming Tower' in names and 'Budew' not in names
    for q,c in [('mill my opponent','opponent_mill'),('mill me','self_mill')]:
        assert p.build(query(q),sources).packet.query['representations'][0]['concepts']==[c]


@pytest.mark.parametrize('mutation,condition',[
    (lambda x:{**x,'facts':[{'text':'A fact','evidence':['ev-invented']}]},'invalid_reference'),
    (lambda x:{**x,'facts':[{'text':'A fact','evidence':['active-deck']}]},'invalid_reference'),
    (lambda x:{**x,'facts':[{'text':'Budew is the best tournament staple.', 'evidence':x['facts'][0]['evidence']}]},'unsupported_competitive_claim'),
    (lambda x:{**x,'facts':[{'text':'Mega Venusaur ex is a mill engine.', 'evidence':x['facts'][0]['evidence']}]},'candidate_outside_evidence'),
    (lambda x:{**x,'facts':[{'text':x['facts'][0]['text']+' It has 999 HP.', 'evidence':x['facts'][0]['evidence']}]},'unsupported_numeric_card_claim'),
])
def test_strict_bounded_rejections(sources,mutation,condition):
    svc,calls=service(sources,mutation);result=svc.run(query())
    assert result['status']=='invalid_answer_contract',result
    assert result['contract_diagnostics']['condition']==condition
    assert result['answer'] is None and len(calls)==1


def test_revision_protection_api(sources):
    svc,calls=service(sources)
    assert svc.run(query(include_deck=True,revision=8))['status']=='context_changed'
    assert not calls
    app=create_app(database=sources.paths['cards'],state_database=sources.paths['collection'],competitive_database=sources.paths['competitive'],deck_database=sources.paths['workspace'])
    app.state.research_agent=svc
    with TestClient(app) as client:
        assert client.post('/api/v1/agent/research',json=query().model_dump()).json()['status']=='answered'
        assert client.post('/api/v1/agent/research',json={'scope':'card_pool_research','question':'x','include_deck':True}).status_code==422


def test_prompt_contract_examples_and_projection_determinism(sources):
    import re
    envelope=p.build(query(),sources,TODAY)
    assert envelope==p.build(query(),sources,TODAY)
    assert len(a.canonical(envelope).encode())<=24576
    for example in re.findall(r'^\{.*\}$',a.LEGACY_POOL_SYSTEM,re.M):
        assert a.assess(example,envelope).outcome=='insufficient_evidence'


def test_truncated_pool_answer_never_shown(sources):
    svc,calls=service(sources,finish='length')
    result=svc.run(query())
    assert result['status']=='output_token_limit_reached' and result['answer'] is None and len(calls)==1


def test_related_cannot_be_promoted_to_direct(sources):
    e=p.build(query('Stop players from using Tools'),sources)
    item=next(i for i in e.packet.evidence if i.kind=='card-pool-candidate')
    payload=values(item.model_dump()['fields']);payload['classification']='related_functional'
    changed=item.model_copy(update={'fields':fields(payload)})
    e=e.model_copy(update={'packet':e.packet.model_copy(update={'evidence':tuple(changed if x.id==item.id else x for x in e.packet.evidence)})})
    reply=dict(version='pokelab-research-answer-v1',outcome='answered',facts=[],
        interpretation=[dict(text=payload['name']+' is directly equivalent.',evidence=[item.id])],limitations=['Tournament success is unknown.'])
    with pytest.raises(a.ContractError) as exc: a.assess(json.dumps(reply),e)
    assert exc.value.diagnostics['condition']=='unsupported_match_equivalence'


def test_deck_orientation_has_citable_printed_anchor(sources):
    e=p.build(query('What cards might support what this deck is trying to do?',include_deck=True,revision=7),sources)
    anchors=[i for i in e.packet.evidence if i.kind=='deck-mechanics']
    assert anchors and anchors[0].references
    assert values(anchors[0].model_dump()['fields'])['components'][0]['text']
    assert e.packet.query['deck_orientation_inferred']


def test_empty_search_and_budget_never_invent_candidates(sources,monkeypatch):
    monkeypatch.setattr(p,'BYTES',1800)
    e=p.build(query(),sources)
    assert len(a.canonical(e).encode())<=1800
    assert not any(i.kind=='card-pool-candidate' for i in e.packet.evidence)
    assert 'candidate:byte-budget' in e.packet.coverage.omitted


def test_long_pool_query_is_rejected_instead_of_silently_truncated():
    from pydantic import ValidationError
    with pytest.raises(ValidationError): query('x'*1001)
