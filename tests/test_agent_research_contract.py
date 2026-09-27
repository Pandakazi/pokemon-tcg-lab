"""Provider wording must describe, not weaken, the production answer contract."""
import json
from pathlib import Path
import socket

import httpx
import pytest

from pokelab import agent_research as agent
from pokelab import agent_providers as providers
from pokelab.agent_qualification_config import OUTPUT_BYTES, INPUT_BYTES
from pokelab.rules.models import digest


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError('Network forbidden')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket.socket, 'connect_ex', forbidden)


@pytest.fixture
def envelope():
    value=agent.Envelope.model_validate_json((Path(__file__).parent/'fixtures/agent_research_budew_revision157.json').read_text(encoding='utf-8'))
    assert value.content_hash=='991a77f9439050275916f1933a169b7a5d886a4b1874c601e3381d9a2eb819f1'
    assert digest(value.model_dump(mode='json',exclude={'content_hash'}))==value.content_hash
    return value


def answer(envelope):
    statement=dict(text='Synthetic statement.',evidence=[envelope.packet.evidence[0].id])
    return dict(version='pokelab-research-answer-v1',outcome='answered',facts=[statement],
        interpretation=[statement.copy()],limitations=['Synthetic uncertainty.'])


def check(value,envelope,valid):
    if valid: agent.assess(json.dumps(value),envelope)
    else:
        with pytest.raises(agent.ContractError): agent.assess(json.dumps(value),envelope)


def test_every_literal_json_answer_example_in_production_prompt_validates(envelope):
    # Scan every object, not one hand-picked example or a copied test string.
    decoder=json.JSONDecoder();position=0;examples=[]
    while (start:=agent.SYSTEM.find('{',position))!=-1:
        value,consumed=decoder.raw_decode(agent.SYSTEM[start:])
        examples.append(agent.assess(agent.SYSTEM[start:start+consumed],envelope))
        position=start+consumed
    assert examples
    assert len((agent.SYSTEM+agent.canonical(envelope)).encode())<INPUT_BYTES
    assert len(agent.SYSTEM.encode())+agent.ENVELOPE_BYTES<INPUT_BYTES


@pytest.mark.parametrize('field',['version','outcome','facts','interpretation','limitations'])
@pytest.mark.parametrize('operation',['omit','null'])
def test_all_top_level_fields_required_and_nonnull(envelope,field,operation):
    value=answer(envelope)
    if operation=='omit': del value[field]
    else: value[field]=None
    check(value,envelope,False)


@pytest.mark.parametrize('outcome',['answered','insufficient_evidence','unsupported_question','answered|insufficient_evidence|unsupported_question'])
@pytest.mark.parametrize('facts,interpretation',[(False,False),(True,False),(False,True),(True,True)])
def test_outcome_and_empty_array_rules(envelope,outcome,facts,interpretation):
    value=answer(envelope);value['outcome']=outcome
    if not facts: value['facts']=[]
    if not interpretation: value['interpretation']=[]
    valid=(outcome=='answered' and (facts or interpretation)) or outcome=='insufficient_evidence' or (outcome=='unsupported_question' and not facts and not interpretation)
    check(value,envelope,valid)


@pytest.mark.parametrize('field,maximum',[('facts',8),('interpretation',5),('limitations',8)])
@pytest.mark.parametrize('boundary',['zero','max','over'])
def test_array_bounds(envelope,field,maximum,boundary):
    value=answer(envelope);count={'zero':0,'max':maximum,'over':maximum+1}[boundary]
    value[field]=value[field]*count
    check(value,envelope,boundary!='over' and not (field=='limitations' and boundary=='zero'))


@pytest.mark.parametrize('field,maximum',[('text',1600),('limitation',800)])
@pytest.mark.parametrize('boundary',['empty','blank','max','over'])
def test_nonblank_and_character_limits(envelope,field,maximum,boundary):
    value=answer(envelope);text={'empty':'','blank':' \t\n','max':'a'*maximum,'over':'a'*(maximum+1)}[boundary]
    if field=='text': value['facts'][0]['text']=text
    else: value['limitations']=[text]
    check(value,envelope,boundary=='max')


@pytest.mark.parametrize('count',[0,1,12,13])
def test_statement_citation_cardinality(envelope,count):
    value=answer(envelope);value['facts'][0]['evidence']=[envelope.packet.evidence[0].id]*count
    check(value,envelope,1<=count<=12)


@pytest.mark.parametrize('target',['evidence','active-deck','source','printing','functional','hash','url','invented'])
def test_exact_citation_target_membership(envelope,target):
    card=next(e.payload for e in envelope.packet.evidence if e.payload.kind=='card')
    ids={'evidence':envelope.packet.evidence[0].id,'active-deck':'active-deck','source':envelope.packet.references[0].id,
         'printing':card.printing,'functional':card.functional_id,'hash':envelope.content_hash,
         'url':'https://example.invalid/','invented':'ev-not-in-this-envelope'}
    value=answer(envelope);value['facts'][0]['evidence']=[ids[target]]
    check(value,envelope,target in ('evidence','active-deck'))


@pytest.mark.parametrize('change',['missing_text','missing_evidence','string_citation','extra_statement_field','extra_rules_field','cannot_establish_field'])
def test_statement_shape_and_no_extra_fields(envelope,change):
    value=answer(envelope)
    if change.startswith('missing_'): del value['facts'][0][change.removeprefix('missing_')]
    elif change=='string_citation': value['facts'][0]['evidence']='active-deck'
    elif change=='extra_statement_field': value['facts'][0]['source']='active-deck'
    elif change=='extra_rules_field': value['rules']={}
    else: value['cannot_establish']=[]
    check(value,envelope,False)


@pytest.mark.parametrize('wrapper',['fence','prefix','suffix'])
def test_json_only_parser_is_not_relaxed(envelope,wrapper):
    text=json.dumps(answer(envelope))
    text={'fence':'```json\n'+text+'\n```','prefix':'Answer: '+text,'suffix':text+'\nExplanation.'}[wrapper]
    with pytest.raises(agent.ContractError): agent.assess(text,envelope)


@pytest.mark.parametrize('extra',[0,1])
def test_exact_transport_answer_byte_ceiling_with_fake_transport(envelope,extra):
    text=json.dumps(answer(envelope),ensure_ascii=False)
    text+=' '*(OUTPUT_BYTES-len(text.encode())+extra)
    transport=httpx.MockTransport(lambda request:httpx.Response(200,json={
        'choices':[{'message':{'content':text},'finish_reason':'stop'}]}))
    result=providers.complete(providers.Selection(provider='gemini',model='gemini-3.5-flash-lite'),
        agent.SYSTEM,agent.canonical(envelope),transport=transport,max_output=4096)
    assert OUTPUT_BYTES==16384
    assert result.status==('ok' if extra==0 else 'output_too_large')


def test_individual_maxima_do_not_override_overall_transport_limit(envelope):
    value=answer(envelope)
    value['facts']=[dict(text='a'*1600,evidence=['active-deck']) for _ in range(8)]
    value['interpretation']=[dict(text='b'*1600,evidence=['active-deck']) for _ in range(5)]
    value['limitations']=['c'*800 for _ in range(8)]
    text=json.dumps(value)
    agent.assess(text,envelope)
    assert len(text.encode())>OUTPUT_BYTES
    assert '16,384 UTF-8 bytes' in agent.SYSTEM
