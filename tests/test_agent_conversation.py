"""Offline conversational boundary tests. Fake prose is not a live quality grade."""
import json
from copy import deepcopy
import httpx
import pytest
from pokelab import agent_conversation as c, agent_research as a
from pokelab.agent_providers import Selection
from test_card_pool_research import sources, setup, research, offline


def request(question='What problems must a mill deck solve?', **kw):
    return a.ResearchRequest(scope='conversation',question=question,**kw)


def output(envelope, text='A plausible plan needs repeatability and time to set up; test how it survives the prize clock.'):
    return dict(version='pokelab-conversation-answer-v1',paragraphs=[dict(text=text,evidence=[])],
        fact_ids=[e['id'] for e in envelope['evidence'] if e.get('printing')][:2])


def service(sources, transform=lambda value:value, finish='stop'):
    calls=[]
    def handle(req):
        body=json.loads(req.content);calls.append(body)
        assert 'authorization' not in req.headers
        assert body['provider']=={'allow_fallbacks':False,'max_price':{'prompt':0,'completion':0,'request':0}}
        assert body['max_tokens']==4096 and body['messages'][0]['content']==c.SYSTEM
        envelope=json.loads(body['messages'][1]['content'])
        assert len((c.SYSTEM+a.canonical(envelope)).encode())<=32768
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(transform(output(envelope)))},'finish_reason':finish}]})
    return a.ResearchService(sources.paths,selection=Selection(provider='openrouter',model='fixture/model:free'),transport=httpx.MockTransport(handle)),calls


PROMPTS=[
 ('What cards can mill my own deck, and which ones look easiest to build around?','mill me'),
 ('What cards can help me punish or shut down Pokémon Tools?','tool effect suppression'),
 ('What cards can move damage counters around, and which ones seem the most flexible?','move damage counters'),
 ('What cards can mess with my opponent’s Energy without just doing damage?','energy denial'),
 ('Out of the cards you found, which ones look like the cleanest starting points and why?',None),
 ('Which of these is actually the best tournament option right now?',None),
 ('I want something annoying that makes it hard for my opponent to actually play the game. What cards fit that?','item lock'),
 ('I want to build something stupid around making my opponent run out of cards. What directions could I take that?','mill my opponent'),
 ('If I wanted to make mill actually function, what problems would I need to solve besides just finding cards that discard from the deck?',None),
 ('How would I play a Great Tusk mill deck into Dragapult?',None),
]


@pytest.mark.parametrize('question,lookup',PROMPTS)
def test_behavioral_intents_do_not_gate_reasoning(sources,question,lookup):
    if lookup: assert lookup in c.queries(question)
    svc,calls=service(sources)
    result=svc.run(request(question))
    assert result['status']=='answered',result
    assert len(calls)==1 and result['answer']['paragraphs']
    assert result['envelope']['question']==question
    assert result['envelope']['external_research'] is False


def test_followup_refreshes_referents_and_does_not_need_new_query(sources):
    svc,calls=service(sources)
    first=svc.run(request('What cards can move damage counters?'))
    assert first['status']=='answered',first
    printings=[e['printing'] for e in first['envelope']['evidence'] if e.get('printing')]
    assert printings
    second=svc.run(request('Which of those looks easiest to build around?',conversation_id=first['conversation_id']))
    assert second['status']=='answered'
    envelope=second['envelope']
    assert envelope['history'][0]['question']=='What cards can move damage counters?'
    assert printings==[e['printing'] for e in envelope['evidence'] if e.get('printing')]
    assert c.queries('Which of those looks easiest to build around?')==[]
    assert len(calls)==2


def test_concept_coaching_audit_proof_continuity(sources):
    svc,calls=service(sources);key=None
    questions=['Build me a weird Pikachu damage-manipulation deck.',
        'I like it, but how do I pilot it?', 'What are the three weakest parts of the list we just built?',
        'My opening hand is Pikachu ex, Snorunt, Munkidori, Ultra Ball, Iono, Lightning Energy, and Super Rod. I am going first. Talk me through the turn.',
        'Audit every interaction, Energy requirement and legality assumption.', 'Prove it. Which parts are facts, evidence and reasoning?']
    for i,q in enumerate(questions):
        result=svc.run(request(q,conversation_id=key));assert result['status']=='answered',result
        if i: assert result['envelope']['history'][-1]['question']==questions[i-1]
        key=result['conversation_id']
    assert result['envelope']['proof_requested'] and len(calls)==6


def test_exact_component_and_card_facts_are_local_readonly(sources):
    before={k:p.read_bytes() for k,p in sources.paths.items()}
    svc,calls=service(sources)
    result=svc.run(request('What does Adrena-Brain do?'))
    assert result['status']=='answered'
    cards=[e for e in result['envelope']['evidence'] if e.get('printing')]
    assert any(any(x['name']=='Adrena-Brain' for x in e['value'].get('abilities',[])) for e in cards)
    assert before=={k:p.read_bytes() for k,p in sources.paths.items()}
    selected=svc.run(request('What printing is this?',printing='me02.5-016',variant='normal',include_deck=True,revision=7))
    assert selected['status']=='answered',selected
    assert selected['envelope']['selected']==dict(printing='me02.5-016',variant='normal')
    deck=next(e for e in selected['envelope']['evidence'] if e['id']=='active-deck')
    assert deck['value']['revision']==7 and deck['value']['entries'][0]['quantity']==1
    assert before=={k:p.read_bytes() for k,p in sources.paths.items()}


def test_stale_deck_expired_session_no_provider(sources):
    svc,calls=service(sources)
    assert svc.run(request(include_deck=True,revision=8))['status']=='context_changed'
    assert svc.run(request(conversation_id='a'*32))['status']=='conversation_expired'
    assert calls==[]


def test_zero_results_and_missing_card_store_still_reason(sources):
    sources.paths['cards']=sources.paths['cards'].with_name('absent.sqlite3')
    svc,calls=service(sources)
    result=svc.run(request('What structural problems should I test?'))
    assert result['status']=='answered' and result['envelope']['evidence']==[]
    assert len(calls)==1 and not sources.paths['cards'].exists()


@pytest.mark.parametrize('claim',['This is Tier 1.','This has a 62% win rate.','It dominated Worlds.','This is the most-played variant.'])
def test_unsupported_empirical_claim_qualified_not_whole_answer_rejected(sources,claim):
    def edit(value):
        value['paragraphs'].append(dict(text=claim,evidence=[]));return value
    svc,_=service(sources,edit)
    result=svc.run(request())
    assert result['status']=='answered' and result['empirical_qualification']
    assert claim not in a.canonical(result)
    assert result['answer']['paragraphs'][0]['text'].startswith('A plausible plan')
    assert result['answer']['paragraphs'][-1]['text']==c.QUALIFICATION


@pytest.mark.parametrize('change',[
 lambda v:{**v,'fact_ids':['ref-invented']},
 lambda v:{**v,'paragraphs':[{'text':'Useful','evidence':['unknown']} ]},
 lambda v:{**v,'paragraphs':[{'text':'  ','evidence':[]} ]},
 lambda v:{**v,'facts':[{'damage':999}]},
])
def test_contract_and_fact_ownership_remain_strict(sources,change):
    svc,_=service(sources,change)
    result=svc.run(request());assert result['status']=='invalid_answer_contract' and result['answer'] is None
    assert svc.conversations.items=={}


def test_internal_failure_and_truncation_never_commit_history(sources,monkeypatch):
    svc,_=service(sources,finish='length')
    assert svc.run(request())['status']=='output_token_limit_reached'
    assert not svc.conversations.items
    svc,_=service(sources)
    monkeypatch.setattr(c,'assess',lambda *a:(_ for _ in ()).throw(RuntimeError('unsafe exception')))
    result=svc.run(request())
    assert result['status']=='internal_assessment_failure' and 'unsafe exception' not in a.canonical(result)
    assert not svc.conversations.items


def test_secrets_never_enter_history_or_response(sources,monkeypatch):
    secret='mock-secret-quarantine-value-123456'
    monkeypatch.setenv('POKELAB_GEMINI_API_KEY',secret)
    svc,calls=service(sources,lambda v:{**v,'paragraphs':[dict(text=secret,evidence=[])]})
    result=svc.run(request());assert result['status']=='provider_failure'  # transport quarantines first
    assert secret not in a.canonical(result) and not svc.conversations.items
    assert svc.run(request(secret))['status']=='secret_input_rejected' and len(calls)==1


def test_sessions_bounded_isolated_and_expire(monkeypatch):
    store=c.Conversations();turns=[dict(question=str(i),answer='reasoning') for i in range(20)]
    key=store.put(None,turns,['x']*20)
    assert len(store.get(key)['turns'])==6 and len(store.get(key)['printings'])==8
    assert store.get(None)==dict(turns=[],printings=[])
    for i in range(40): store.put(None,[],[])
    assert len(store.items)==32 and store.get(key) is None
    monkeypatch.setattr(c,'monotonic',lambda:10**20)
    assert store.get(next(iter(store.items))) is None and not store.items


def test_prompt_literal_example_validates():
    literal=next(line for line in c.SYSTEM.splitlines() if line.startswith('{'))
    result,qualified=c.assess(literal,dict(evidence=[]))
    assert result['paragraphs'] and not qualified
    assert 'Strategic inference needs no database verdict' in c.SYSTEM
    assert 'compare' in c.SYSTEM and 'printed' in c.SYSTEM
