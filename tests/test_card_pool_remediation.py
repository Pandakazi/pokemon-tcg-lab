"""Exact PM envelope reconstruction, authored answers, no historical output retained."""
from datetime import date
import json
from pathlib import Path
import httpx
import pytest
from pokelab import agent_research as a, card_pool_research as p
from pokelab.agent_providers import Selection
from pokelab.research_grounding import fields
from pokelab.rules.models import digest
from test_card_pool_research import offline, sources, setup, research, query, pool_response

ROOT=Path(__file__).parent/'fixtures'
PACKETS=json.loads((ROOT/'card_pool_pm_20261002.json').read_text(encoding='utf-8'))
CASES=json.loads((ROOT/'card_pool_pm_answers.json').read_text(encoding='utf-8'))['cases']


def envelope(key='simple'):
    return p.PoolEnvelope.model_validate(dict(PACKETS[key],catalog_names=PACKETS['catalog_names']))


def reply(text,names=('Centiskorch',)):
    e=envelope();ids={fields(i.model_dump()['fields'])['name']:i.id for i in e.packet.evidence}
    return dict(version='pokelab-research-answer-v1',outcome='answered',
        facts=[dict(text=text,evidence=[ids[n] for n in names])],interpretation=[],
        limitations=['Tournament success cannot be established from this evidence.'])


@pytest.mark.parametrize('case',CASES,ids=lambda x:x['id'])
def test_frozen_answer_contract(case):
    e=envelope(case['envelope'])
    if case['expected']=='accepted':
        assert a.assess(json.dumps(case['answer']),e).outcome=='answered'
    else:
        with pytest.raises(a.ContractError) as exc: a.assess(json.dumps(case['answer']),e)
        assert exc.value.diagnostics['condition']==case['expected']


@pytest.mark.parametrize('key,expected',[
    ('simple','e12ca2b923f1b1b1523b9e8d92c8df6b8c12ccbf14ab890cd8b075ade0f0afa9'),
    ('flagship','c11c463c60deaf422defe460d6d742d2015ef9d498403a8fd9ece090c8d501de'),
])
def test_exact_hash_id_serialization_provenance(key,expected):
    e=envelope(key)
    assert e.content_hash==expected==digest(e.model_dump(mode='json',exclude={'content_hash'}))
    again=p.PoolEnvelope.model_validate_json(a.canonical(e))
    assert [i.id for i in again.packet.evidence]==[i.id for i in e.packet.evidence]
    ids=[i.id for i in e.packet.evidence];refs={r.id:r for r in e.packet.references}
    assert len(ids)==len(set(ids))==5
    assert set(ids).isdisjoint(refs)
    for item in e.packet.evidence:
        value=fields(item.model_dump()['fields'])
        assert item.id=='ev-pool-'+digest(dict(kind=item.kind,payload=value))[:24]
        assert item.references and set(item.references)<=refs.keys()
        assert all(refs[r].source=='TCGdex' and refs[r].content_hash and refs[r].url for r in item.references)
        assert value['components'] and all(c['text']==c['structured']['effect'] for c in value['components'])
        # The provider may cite each individually, without inventing a component ID.
        assert a.assess(json.dumps(reply_for_item(item)),e).outcome=='answered'


def reply_for_item(item):
    value=fields(item.model_dump()['fields'])
    return dict(version='pokelab-research-answer-v1',outcome='answered',facts=[dict(
        text=value['name']+': '+value['components'][0]['text'],evidence=[item.id])],
        interpretation=[],limitations=['Tournament performance is unknown.'])


@pytest.mark.parametrize('text,names',[
    ("Centiskorch's Controlled Burn costs 1 Fire Energy and discards the top 2 cards of your opponent's deck.",('Centiskorch',)),
    ("Centiskorch's Controlled Burn costs 1 Energy.",('Centiskorch',)),
    ("Centiskorch's Controlled Burn costs one Energy. Coalossal's Cragalanche costs four Energy.",('Centiskorch','Coalossal')),
])
def test_proven_false_rejections_now_accept(text,names):
    assert a.assess(json.dumps(reply(text,names)),envelope()).outcome=='answered'


@pytest.mark.parametrize('text,names,expected',[
    ("Centiskorch's Controlled Burn costs 2 Fire Energy.",('Centiskorch',),'unsupported_attack_cost'),
    ("Centiskorch's Controlled Burn costs 1 Water Energy.",('Centiskorch',),'unsupported_attack_cost'),
    ("Centiskorch's Controlled Burn is free.",('Centiskorch',),'unsupported_attack_cost'),
    ("Centiskorch's Controlled Burn costs 1 Fire Energy. Fire Energy is a useful card for this strategy.",('Centiskorch',),'candidate_outside_evidence'),
    ("Centiskorch's Controlled Burn costs four Energy. Coalossal's Cragalanche costs one Energy.",('Centiskorch','Coalossal'),'unsupported_attack_cost'),
    ('Centiskorch has 999 HP.',('Centiskorch',),'unsupported_numeric_card_claim'),
    ('Centiskorch does 150 damage.',('Centiskorch','Coalossal'),'unsupported_numeric_card_claim'),
    ('Mega Venusaur ex is a mill engine.',('Centiskorch',),'candidate_outside_evidence'),
])
def test_wrong_costs_cards_cross_subject_values_still_rejected(text,names,expected):
    with pytest.raises(a.ContractError) as exc: a.assess(json.dumps(reply(text,names)),envelope())
    d=exc.value.diagnostics
    assert d['condition']==expected
    assert d['stage']=='card_pool_grounding' and d['path']==['facts',0,'text']
    assert set(d['cited_evidence_ids'])<={e.id for e in envelope().packet.evidence}
    assert text not in json.dumps(d)


@pytest.mark.parametrize('references,expected',[([], 'schema_validation'),(['ref-private-unsafe'], 'invalid_reference'),(['active-deck'],'invalid_reference')])
def test_missing_source_and_wrong_context_citations(references,expected):
    answer=reply('Centiskorch mills the opponent.');answer['facts'][0]['evidence']=references
    with pytest.raises(a.ContractError) as exc: a.assess(json.dumps(answer),envelope())
    assert exc.value.diagnostics['condition']==expected
    assert 'ref-private-unsafe' not in json.dumps(exc.value.diagnostics)


@pytest.mark.parametrize('key',['simple','flagship'])
def test_exact_pm_envelope_through_production_service(sources,monkeypatch,key):
    e=envelope(key);calls=[]
    monkeypatch.setattr(p,'build',lambda *args,**kw:e)
    case=next(c for c in CASES if c['envelope']==key and c['expected']=='accepted')
    def handle(request):
        body=json.loads(request.content);calls.append(body)
        assert body['messages'][0]['content']==a.POOL_SYSTEM
        assert json.loads(body['messages'][1]['content'])==PACKETS[key]
        assert body['provider']=={'allow_fallbacks':False,'max_price':{'prompt':0,'completion':0,'request':0}}
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(pool_response(case['answer'],PACKETS[key]))},'finish_reason':'stop'}]})
    svc=a.ResearchService(sources.paths,selection=Selection(provider='openrouter',model='fixture/model:free'),transport=httpx.MockTransport(handle))
    result=svc.run(query(e.packet.request['question']))
    assert result['status']=='answered' and len(calls)==1
    assert result['envelope']['content_hash']==e.content_hash


def test_live_builder_ids_unique_and_budget_prunes_references(sources,monkeypatch):
    for cap in (24576,6000,1800):
        monkeypatch.setattr(p,'BYTES',cap)
        e=p.build(query(),sources,today=date(2026,10,2))
        ids=[i.id for i in e.packet.evidence]
        assert len(ids)==len(set(ids))
        used={r for i in e.packet.evidence for r in i.references}
        assert used=={r.id for r in e.packet.references}
        assert len(a.canonical(e).encode())<=cap


def test_prompt_teaches_pool_layout_and_supported_conversational_costs():
    assert 'packet.evidence[*].fields' in a.POOL_SYSTEM
    assert 'containing item' in a.POOL_SYSTEM and 'Name the card/attack' in a.POOL_SYSTEM
    assert 'Mechanical research can still answer' in a.POOL_SYSTEM
    assert 'Limitations express uncertainty, not uncited card/deck facts' in a.POOL_SYSTEM


@pytest.mark.parametrize('key',['simple','flagship'])
@pytest.mark.parametrize('outcome',['answered','unsupported_question'])
def test_recovered_limitation_failure_in_legacy_assessment(key,outcome):
    """Historical strict boundary remains; v2 degradation is covered separately."""
    e=envelope(key);calls=[]
    answer=reply('Centiskorch: Discard the top 2 cards of your opponent\'s deck.')
    answer['outcome']=outcome
    if outcome=='unsupported_question': answer['facts']=[]
    answer['limitations']=['Centiskorch uses Controlled Burn to discard cards from the opponent\'s deck.']
    with pytest.raises(a.ContractError) as exc: a.assess(json.dumps(answer),e)
    assert exc.value.diagnostics==dict(condition='uncited_limitation_claim',json_parsed=True,schema_valid=True)
    assert answer['limitations'][0] not in json.dumps(exc.value.diagnostics)


@pytest.mark.parametrize('text',[
    'Creator intent cannot be established from the supplied evidence.',
    'Tournament success cannot be established from the supplied evidence.',
])
def test_epistemic_limitations_still_accepted(text):
    answer=reply('Centiskorch: Discard the top 2 cards of your opponent\'s deck.')
    answer['limitations']=[text]
    assert a.assess(json.dumps(answer),envelope()).outcome=='answered'


def test_contrast_does_not_hide_competitive_claim():
    answer=reply('Centiskorch is not proven, but is a tournament staple.')
    with pytest.raises(a.ContractError) as exc: a.assess(json.dumps(answer),envelope())
    assert exc.value.diagnostics['condition']=='unsupported_competitive_claim'
