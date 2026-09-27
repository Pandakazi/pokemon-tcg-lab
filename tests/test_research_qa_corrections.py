"""Offline regressions for the three PM-observed Research failures."""
import json
import socket
from pathlib import Path

import httpx
import pytest

from pokelab import agent_research as a, deck_research as d
from pokelab.agent_context_models import FieldValue
from pokelab.agent_providers import Selection
from test_agent_context import setup
from test_research import research, KEY, TODAY


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError('Network forbidden')
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    monkeypatch.setattr(socket.socket,'connect_ex',forbidden)


@pytest.fixture
def budew():
    return a.Envelope.model_validate_json((Path(__file__).parent/'fixtures/agent_research_budew_revision157.json').read_text(encoding='utf-8'))


def card_evidence(envelope):
    return next(e for e in envelope.packet.evidence if e.payload.kind=='card')


def response(text, refs, limitations=None):
    return dict(version='pokelab-research-answer-v1',outcome='answered',
        facts=[dict(text=text,evidence=refs)],interpretation=[],
        limitations=limitations or ['Creator intent cannot be established from the supplied evidence.'])


def test_budew_source_evidence_has_omitted_not_numeric_cost(budew):
    card=card_evidence(budew)
    assert card.payload.printing=='me02.5-221'
    assert card.payload.functional_id=='bb71f052255398422b7dc659a97b9501'
    attacks=json.loads(next(f.value for f in card.payload.printed if f.field=='attacks'))
    assert attacks==[dict(name='Itchy Pollen',damage=10,
        effect="During your opponent's next turn, they can't play any Item cards from their hand.")]
    assert budew.content_hash=='991a77f9439050275916f1933a169b7a5d886a4b1874c601e3381d9a2eb819f1'


@pytest.mark.parametrize('text',[
    'Budew has the attack Itchy Pollen for 1 Energy which deals 10 damage and states that during the opponent\'s next turn, they cannot play any Item cards from their hand.',
    'Itchy Pollen costs one Energy.', 'Itchy Pollen requires 0 Energy.',
    'Itchy Pollen is free.', 'Itchy Pollen requires no Energy.',
])
def test_unsupported_budew_cost_rejected(budew,text):
    with pytest.raises(a.ContractError) as err:
        a.assess(json.dumps(response(text,[card_evidence(budew).id])),budew)
    assert err.value.diagnostics['condition']=='unsupported_attack_cost'
    assert text not in json.dumps(err.value.diagnostics)


def test_printed_effect_without_invented_cost_passes(budew):
    a.assess(json.dumps(response('Itchy Pollen deals 10 damage and prevents Item cards being played from the opponent\'s hand during their next turn.',[card_evidence(budew).id])),budew)


@pytest.mark.parametrize('cost,claim,accepted', [([],0,True),([],1,False),(['Colorless'],1,True),(['Grass','Colorless'],2,True),(['Grass'],0,False)])
def test_explicit_cost_semantics_and_citation_support(budew,cost,claim,accepted):
    card=card_evidence(budew)
    printed=tuple(FieldValue(field=f.field,value=json.dumps([dict(name='Itchy Pollen',damage=10,cost=cost)])) if f.field=='attacks' else f for f in card.payload.printed)
    updated=card.model_copy(update={'payload':card.payload.model_copy(update={'printed':printed})})
    envelope=budew.model_copy(update={'packet':budew.packet.model_copy(update={'evidence':tuple(updated if e.id==card.id else e for e in budew.packet.evidence)})})
    text=json.dumps(response(f'Itchy Pollen costs {claim} Energy.',[card.id]))
    if accepted: a.assess(text,envelope)
    else:
        with pytest.raises(a.ContractError): a.assess(text,envelope)
    with pytest.raises(a.ContractError):
        a.assess(json.dumps(response(f'Itchy Pollen costs {claim} Energy.',['active-deck'])),envelope)


@pytest.mark.parametrize('limitation',[
    'The active deck contains Dragapult ex.', 'The deck contains no Charizard ex.',
    'This deck does not include Charizard ex.', 'Budew has Itchy Pollen.',
    'Creator intent is unavailable. The deck runs two Budew.',
])
def test_factual_limitations_fail_closed(budew,limitation):
    with pytest.raises(a.ContractError) as err:
        a.assess(json.dumps(response('Synthetic supported fact.',['active-deck'],[limitation])),budew)
    assert err.value.diagnostics['condition']=='uncited_limitation_claim'


@pytest.mark.parametrize('limitation',[
    'Creator intent cannot be established from the supplied evidence.',
    'No piloting guide is supplied; matchup performance cannot be established.',
    'Cannot establish whether the deck contains another printing outside this snapshot.',
])
def test_epistemic_limitations_do_not_require_citations(budew,limitation):
    a.assess(json.dumps(response('Synthetic supported fact.',['active-deck'],[limitation])),budew)


def comparison_envelope(setup):
    return a.make_deck_envelope(a.ResearchRequest(scope='active_deck_research',revision=7,archetype=KEY,
        question='How does this deck differ from typical decks?'),setup[0],today=TODAY)[0]


def test_no_deviation_evidence_and_comparison_framing(setup):
    e=comparison_envelope(setup)
    summary=next(i for i in e.packet.evidence if i.kind=='deviation-summary')
    values={f.field:json.loads(f.value) for f in summary.fields}
    assert values['available'] is True
    assert all(values['counts'][k]==0 for k in ('UNCOMMON_PRESENT','COMMON_ABSENT','ABOVE_TYPICAL_QUANTITY','BELOW_TYPICAL_QUANTITY'))
    assert values['configuration']['core_percent']==80 and values['configuration']['typical_mass_percent']==80
    assert 'Similarities may follow as context' in a.DECK_SYSTEM
    assert 'Do not call the decks identical' in a.DECK_SYSTEM
    population=next(i for i in e.packet.evidence if i.kind=='population')
    valid=response('Under the current thresholds, no supported composition/quantity deviations were detected in this population.',[summary.id,population.id],
        ['Threshold-based comparison does not establish literal identity or equal performance.'])
    valid['interpretation']=[dict(text='Core/common inclusion provides similarity context.',evidence=[summary.id])]
    a.assess(json.dumps(valid),e)
    with pytest.raises(a.ContractError) as err:
        a.assess(json.dumps(response('The key difference is its core cards.',[summary.id])),e)
    assert err.value.diagnostics['condition']=='unsupported_comparison_difference'


@pytest.mark.parametrize('prefix',['Aurora','Cinder'])
def test_overview_prioritizes_generic_core_evolution_line_under_cap(setup,prefix):
    p=d.build_profile(setup[0],revision=7,as_of=TODAY,archetype=KEY)
    template=p.cards[0]
    cards=[]
    for identity,name,parents,qty in [('z-base',prefix+' Seed',(),4),('z-mid',prefix+' Branch',('z-base',),3),('z-final',prefix+' Crown',('z-mid',),3)]+[
        (f'a-support-{i}',f'Support {i}',(),1) for i in range(8)]:
        cards.append(template.model_copy(update=dict(identity=identity,name=name,category='Pokemon',quantity=qty,
            evolution_parents=parents,printed=(FieldValue(field='attacks',value=json.dumps([dict(name=name+' Attack',cost=['Colorless'])])),))))
    p=p.model_copy(update={'cards':tuple(cards),'comparisons':tuple(d.compare(c.identity,c.name,c.quantity,[c.quantity]*16) for c in cards)})
    packet=d.select_evidence(p,'What is this deck trying to do?')
    mechanics=[i for i in packet.evidence if i.kind=='mechanics']
    assert [i.identity for i in mechanics[:3]]==['z-final','z-mid','z-base']
    assert len(mechanics)==6 and packet.serialized_bytes<=24576
    assert 'cap/mechanics:5' in packet.coverage.omitted
    assert packet==d.select_evidence(p,'What is this deck trying to do?')


def test_fake_provider_rejection_is_single_call_safe_and_preserves_execution(budew,monkeypatch):
    calls=[]
    def handle(request):
        calls.append(request)
        return httpx.Response(200,json=dict(choices=[dict(message=dict(content=json.dumps(response(
            'Itchy Pollen costs one Energy.',[card_evidence(budew).id]))),finish_reason='stop')],
            usage=dict(prompt_tokens=123,completion_tokens=45)))
    monkeypatch.setattr(a,'make_envelope',lambda *args:budew)
    svc=a.ResearchService(dict(cards='a',collection='b',workspace='c',competitive='d'),
        selection=Selection(provider='gemini',model='gemini-3.5-flash-lite'),transport=httpx.MockTransport(handle))
    result=svc.run(a.ResearchRequest(printing='me02.5-221',variant='holo',question='What is its role?',revision=157))
    assert len(calls)==1 and result['answer'] is None and result['status']=='invalid_answer_contract'
    assert result['execution']['input_tokens']==123
    assert result['contract_diagnostics']['condition']=='unsupported_attack_cost'
    assert 'costs one Energy' not in json.dumps(result)


@pytest.mark.parametrize('claim,limitation,condition',[
    ('No supported deviations were detected under the configured thresholds. Similarities provide context.',
     'Thresholds do not prove identical decks or equal performance.',None),
    ('The main difference is its core cards.','Creator intent cannot be established.','unsupported_comparison_difference'),
    ('The decks are literally identical.','Creator intent cannot be established.','unsupported_comparison_difference'),
    ('No supported deviations were detected.','The deck contains no Charizard ex.','uncited_limitation_claim'),
])
def test_comparison_fake_provider_boundary(setup,monkeypatch,claim,limitation,condition):
    envelope=comparison_envelope(setup);calls=[]
    summary=next(i.id for i in envelope.packet.evidence if i.kind=='deviation-summary')
    population=next(i.id for i in envelope.packet.evidence if i.kind=='population')
    def handle(request):
        calls.append(request)
        body=json.loads(request.content)
        assert 'Similarities may follow as context' in body['messages'][0]['content']
        return httpx.Response(200,json=dict(choices=[dict(message=dict(content=json.dumps(
            response(claim,[summary,population],[limitation]))),finish_reason='stop')]))
    monkeypatch.setattr(a,'make_deck_envelope',lambda *args:(envelope,{}))
    svc=a.ResearchService(setup[0].paths,selection=Selection(provider='gemini',model='gemini-3.5-flash-lite'),transport=httpx.MockTransport(handle))
    result=svc.run(a.ResearchRequest(scope='active_deck_research',question='How does this deck differ?',revision=7,archetype=KEY))
    assert len(calls)==1
    if condition:
        assert result['status']=='invalid_answer_contract' and result['answer'] is None
        assert result['contract_diagnostics']['condition']==condition
    else: assert result['status']=='answered'
