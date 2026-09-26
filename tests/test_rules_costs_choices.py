"""Pass C mechanics and information-boundary contracts; no persistence/network."""
from copy import deepcopy
import json
import pytest
from pydantic import ValidationError
from pokelab.collection import identity
from pokelab.engine import functional_signature
from pokelab.rules import (Action, CardInstance, Choices, GUMSHOOS, Location, RULESET,
                           ULTRA_BALL, Registry, Scenario, apply, evaluate,
                           apply_view, evaluation_view, state_view)
from pokelab.rules.models import Usage, digest
from pokelab.rules.registry import reviewed_sources


class Cards:
    def __init__(self): self.records = reviewed_sources()
    def get(self, key, include_image=False): return {'card': deepcopy(self.records[key])}


def instance(key, zone, position=0, printing='me02-001', player='alice', profile=None):
    return CardInstance(id=key, owner=player, controller=player, printing_id=printing,
        functional_id=identity(functional_signature(reviewed_sources()[printing])), profile=profile,
        location=Location(player=player, zone=zone, position=position))


def scenario():
    return Scenario(ruleset=RULESET, revision=3, players=('alice','bob'), turn_player='alice', turn='alice-turn-1',
        isolation_confirmed=True, unresolved_dependencies=(), instances=(
            instance('ultra', 'resolving', printing='me01-131', profile=ULTRA_BALL),
            instance('gum', 'active', printing='me01-110', profile=GUMSHOOS),
            instance('gum2', 'bench', printing='me01-110', profile=GUMSHOOS),
            instance('pay1','hand',0), instance('pay2','hand',1,printing='me01-130'), instance('keep','hand',2),
            instance('top-secret','deck',0,printing='me01-130'), instance('found','deck',1), instance('other-secret','deck',2),
            instance('old-discard','discard'), instance('opponent-hand','hand',player='bob'),
            instance('opponent-deck','deck',player='bob')))


def action(state, gum=False, choices=None, source=None):
    return Action(profile=GUMSHOOS if gum else ULTRA_BALL, actor='alice',
        source=source or ('gum' if gum else 'ultra'), expected_revision=state.revision,
        expected_state_hash=state.state_hash(), choices=choices or Choices())


def paid(**changes):
    return Choices(**(dict(payment=('pay1','pay2'), search='found', shuffle=('other-secret','top-secret')) | changes))


def locations(state): return {c.id:(c.location.zone,c.location.position) for c in state.instances}


def remove(state, *ids):
    return state.model_copy(update={'instances':tuple(c for c in state.instances if c.id not in ids)})


def test_ultra_choices_and_exact_atomic_transition():
    state=scenario(); cards=Cards(); before=state.model_dump_json()
    missing=evaluate(action(state),state,cards)
    assert missing.status=='NEEDS_CHOICE' and missing.required_choices==('payment',)
    assert len(missing.choices)==1  # No deck-search disclosure before a valid cost proposal.
    search=evaluate(action(state,choices=Choices(payment=('pay1','pay2'))),state,cards)
    assert search.required_choices==('search',)
    candidate=action(state,choices=paid()); result=evaluate(candidate,state,cards)
    assert result.status=='SUPPORTED_LEGAL' and result==evaluate(candidate,state,cards)
    assert type(result).model_validate_json(result.model_dump_json())==result
    assert [(s.phase,s.operation) for s in result.delta.steps]==[
        ('cost','discard'),('effect','search'),('effect','reveal'),('effect','move-to-hand'),('effect','shuffle')]
    assert result.delta.steps[0].instances==('pay1','pay2')
    applied=apply(candidate,state,cards,evaluated=result)
    assert applied.applied and applied.state.revision==4
    expected=locations(state) | {'pay1':('discard',1),'pay2':('discard',2),'keep':('hand',0),
        'found':('hand',1),'other-secret':('deck',0),'top-secret':('deck',1)}
    assert locations(applied.state)==expected and applied.state.usage==()
    assert state.model_dump_json()==before
    assert apply(candidate,state,cards,evaluated=result).state==applied.state
    reordered=state.model_copy(update={'instances':tuple(reversed(state.instances))})
    assert reordered.state_hash()==state.state_hash()
    assert evaluate(candidate,reordered,cards)==result


@pytest.mark.parametrize('payment',[
    (),('pay1',),('pay1','pay2','keep'),('pay1','pay1'),('ultra','pay1'),
    ('opponent-hand','pay1'),('found','pay1'),('gum','pay1'),('old-discard','pay1'),('missing','pay1')])
def test_invalid_payment_is_atomic(payment):
    state=scenario(); candidate=action(state,choices=paid(payment=payment)); before=state.model_dump_json()
    result=evaluate(candidate,state,Cards())
    assert result.status=='SUPPORTED_ILLEGAL' and result.choices[0].rejection
    failed=apply(candidate,state,Cards(),evaluated=result)
    assert not failed.applied and failed.state==state and state.model_dump_json()==before


@pytest.mark.parametrize('search',['top-secret','pay1','old-discard','gum','gum2','opponent-deck','missing'])
def test_invalid_search_is_atomic(search):
    state=scenario(); candidate=action(state,choices=paid(search=search))
    result=evaluate(candidate,state,Cards())
    assert result.status=='SUPPORTED_ILLEGAL' and result.choices[1].rejection
    assert apply(candidate,state,Cards(),evaluated=result).state==state


@pytest.mark.parametrize('shuffle',[(),('top-secret',),('top-secret','top-secret'),
    ('top-secret','found'),('top-secret','opponent-deck'),('other-secret','top-secret','found')])
def test_invalid_shuffle_never_pays_cost(shuffle):
    state=scenario(); candidate=action(state,choices=paid(shuffle=shuffle))
    result=evaluate(candidate,state,Cards())
    assert result.status=='SUPPORTED_ILLEGAL' and result.delta is None
    assert not apply(candidate,state,Cards(),evaluated=result).applied


def test_explicit_shuffle_required_and_different_permutations():
    state=scenario(); candidate=action(state,choices=paid(shuffle=None))
    result=evaluate(candidate,state,Cards())
    assert result.status=='NEEDS_CHOICE' and result.required_choices==('shuffle',)
    candidate=action(state,choices=paid(shuffle=('top-secret','other-secret')))
    result=evaluate(candidate,state,Cards())
    applied=apply(candidate,state,Cards(),evaluated=result)
    assert locations(applied.state)['top-secret']==('deck',0)
    state=remove(state,'top-secret','other-secret')
    candidate=action(state,choices=paid(shuffle=()))
    result=evaluate(candidate,state,Cards())
    assert result.status=='SUPPORTED_LEGAL' and apply(candidate,state,Cards(),evaluated=result).applied


def test_unpayable_and_no_result_do_not_guess():
    state=remove(scenario(),'pay2','keep')
    assert evaluate(action(state),state,Cards()).checks[0].code=='COST_UNPAYABLE'
    state=remove(scenario(),'found','other-secret')
    result=evaluate(action(state,choices=Choices(payment=('pay1','pay2'))),state,Cards())
    assert result.status=='UNSUPPORTED' and result.unsupported_dependencies==('no-result-search-rule',)
    assert not apply(result.action,state,Cards(),evaluated=result).applied


@pytest.mark.parametrize('gum',[False,True])
def test_receipt_tamper_stale_and_source_change(gum):
    state=scenario(); cards=Cards(); choices=Choices(exchange='pay1') if gum else paid()
    candidate=action(state,gum,choices); result=evaluate(candidate,state,cards)
    changed_choices=Choices(exchange='pay2') if gum else paid(payment=('pay1','keep'))
    forged=result.model_copy(update={'delta':result.delta.model_copy(update={'moves':()})})
    forged_steps=result.model_copy(update={'delta':result.delta.model_copy(update={'steps':()})})
    changed_state=state.model_copy(update={'revision':state.revision+1})
    changed_hash=state.model_copy(update={'turn':'changed-same-revision'})
    for a,s,r in ((candidate,state,forged),(candidate,state,forged_steps),(action(state,gum,changed_choices),state,result),
                  (candidate,changed_state,result),(candidate,changed_hash,result)):
        failed=apply(a,s,cards,evaluated=r)
        assert not failed.applied and failed.state==s
    if gum:
        forged_usage=result.model_copy(update={'delta':result.delta.model_copy(update={'usage_added':()})})
        assert not apply(candidate,state,cards,evaluated=forged_usage).applied
    printing='me01-110' if gum else 'me01-131'
    if gum: cards.records[printing]['abilities'][0]['effect']='Changed'
    else: cards.records[printing]['effect']='Changed'
    assert Registry().resolve(candidate.profile,cards).support=='STALE'
    assert not apply(candidate,state,cards,evaluated=result).applied


def test_gumshoos_first_repeat_other_instance_and_turn_boundary():
    state=scenario(); cards=Cards(); before=state.model_dump_json()
    assert Registry().resolve(GUMSHOOS,cards).support=='REVIEWED'
    missing=evaluate(action(state,True),state,cards)
    assert missing.status=='NEEDS_CHOICE' and missing.required_choices==('exchange',)
    candidate=action(state,True,Choices(exchange='pay1')); result=evaluate(candidate,state,cards)
    assert result.status=='SUPPORTED_LEGAL' and result==evaluate(candidate,state,cards)
    applied=apply(candidate,state,cards,evaluated=result)
    assert applied.applied and state.model_dump_json()==before
    assert locations(applied.state)==locations(state) | {'pay1':('deck',0),'top-secret':('hand',0)}
    assert applied.state.usage==(Usage(turn=state.turn,player='alice',effect='Evidence Gathering',scope='instance',instance='gum'),)
    again=action(applied.state,True,Choices(exchange='pay2'))
    repeat=evaluate(again,applied.state,cards)
    assert repeat.checks[0].code=='ALREADY_USED' and not apply(again,applied.state,cards,evaluated=repeat).applied
    assert evaluate(action(applied.state,True,Choices(exchange='pay2'),source='gum2'),applied.state,cards).status=='SUPPORTED_LEGAL'
    next_turn=applied.state.model_copy(update={'turn':'alice-turn-2','revision':5})
    assert evaluate(action(next_turn,True,Choices(exchange='pay2')),next_turn,cards).status=='SUPPORTED_LEGAL'
    assert not apply(candidate,applied.state,cards,evaluated=result).applied


@pytest.mark.parametrize('exchange',['top-secret','gum','old-discard','opponent-hand','missing'])
def test_gum_invalid_choice(exchange):
    state=scenario(); candidate=action(state,True,Choices(exchange=exchange))
    result=evaluate(candidate,state,Cards())
    assert result.status=='SUPPORTED_ILLEGAL' and result.choices[0].rejection
    assert apply(candidate,state,Cards(),evaluated=result).state==state


@pytest.mark.parametrize('gum',[False,True])
def test_authority_dependencies_and_foreign_choices(gum):
    state=scenario().model_copy(update={'unresolved_dependencies':('unknown-ability-lock',)})
    assert evaluate(action(state,gum),state,Cards()).status=='UNSUPPORTED'
    state=state.model_copy(update={'unresolved_dependencies':None})
    assert evaluate(action(state,gum),state,Cards()).status=='INSUFFICIENT_INFORMATION'
    state=scenario()
    choices=paid() if gum else Choices(exchange='pay1')
    assert evaluate(action(state,gum,choices),state,Cards()).status=='SUPPORTED_ILLEGAL'


def test_gum_needs_turn_hand_and_deck():
    state=scenario().model_copy(update={'turn':None})
    assert evaluate(action(state,True),state,Cards()).checks[0].code=='TURN_REQUIRED'
    for ids in (('pay1','pay2','keep'),('top-secret','found','other-secret')):
        state=remove(scenario(),*ids)
        assert evaluate(action(state,True),state,Cards()).checks[0].code=='EXCHANGE_UNAVAILABLE'


def test_private_projections_and_selected_reveal_only():
    state=scenario(); cards=Cards()
    for gum in (False,True):
        candidate=action(state,gum,Choices(exchange='pay1') if gum else paid())
        result=evaluate(candidate,state,cards)
        opponent=evaluation_view(result,'bob',players=state.players)
        assert opponent=={'visibility':'private-pending-resolution'}
        own=json.dumps(evaluation_view(result,'alice',players=state.players))
        assert 'top-secret' not in own and state.state_hash() not in own
        assert 'moves' not in own and 'delta' not in own
        applied=apply(candidate,state,cards,evaluated=result)
        opponent=apply_view(applied,'bob'); encoded=json.dumps(opponent)
        assert 'top-secret' not in encoded and 'other-secret' not in encoded
        if gum:
            assert 'pay1' not in encoded and opponent['reveals']==[]
            assert 'top-secret' in json.dumps(apply_view(applied,'alice'))
        else:
            assert opponent['reveals']==[{'instance':'found','printing':'me02-001'}]
            assert 'keep' not in encoded
        failed=apply(candidate,applied.state,cards,evaluated=result)
        assert apply_view(failed,'bob')['reveals']==[]
    for player in state.players:
        assert 'top-secret' not in json.dumps(state_view(state,player))
    with pytest.raises(ValueError): state_view(state,'mallory')


def test_search_candidates_do_not_disclose_order():
    state=scenario(); candidate=action(state,choices=Choices(payment=('pay1','pay2')))
    first=evaluation_view(evaluate(candidate,state,Cards()),'alice',players=state.players)
    altered=state.model_copy(update={'instances':tuple(c.model_copy(update={'location':
        c.location.model_copy(update={'position':3-c.location.position})})
        if c.id in ('found','other-secret') else c for c in state.instances)})
    second=evaluation_view(evaluate(action(altered,choices=candidate.choices),altered,Cards()),'alice',players=state.players)
    assert first==second


def test_usage_validation_and_hash_compatibility():
    state=scenario().model_copy(update={'turn':None})
    old=state.model_dump(mode='json'); old.pop('turn'); old.pop('usage')
    old['instances']=sorted(old['instances'],key=lambda c:c['id'])
    assert state.state_hash()==digest(old)
    usage=Usage(turn='one',player='alice',scope='instance',instance='gum',effect='Evidence Gathering')
    with pytest.raises(ValidationError): Scenario.model_validate(state.model_dump() | {'usage':(usage,usage)})
    with pytest.raises(ValidationError): Usage(turn='one',player='alice',scope='instance',effect='x')
    with pytest.raises(ValidationError): Usage(turn='one',player='alice',scope='player',instance='gum',effect='x')
    other=usage.model_copy(update={'instance':'gum2'})
    a=state.model_copy(update={'usage':(usage,other)})
    b=state.model_copy(update={'usage':(other,usage)})
    assert a.state_hash()==b.state_hash()


def test_conflicting_usage_scope_fails_closed():
    state=scenario()
    for scope in ('player','named-effect'):
        altered=state.model_copy(update={'usage':(Usage(turn=state.turn,player='alice',scope=scope,effect='Evidence Gathering'),)})
        result=evaluate(action(altered,True,Choices(exchange='pay1')),altered,Cards())
        assert result.status=='UNSUPPORTED' and result.checks[0].code=='USAGE_SCOPE'


@pytest.mark.parametrize('gum',[False,True])
def test_source_zone_and_control_boundaries(gum):
    state=scenario(); source='gum' if gum else 'ultra'
    for changes in ({'controller':'bob'}, {'owner':'bob'},
                    {'location':Location(player='alice',zone='hand',position=3)}):
        altered=state.model_copy(update={'instances':tuple(c.model_copy(update=changes) if c.id==source else c for c in state.instances)})
        candidate=action(altered,gum,Choices(exchange='pay1') if gum else paid())
        result=evaluate(candidate,altered,Cards())
        assert result.status=='SUPPORTED_ILLEGAL'
        assert not apply(candidate,altered,Cards(),evaluated=result).applied


def test_reviewed_evidence_contains_exact_cached_fields():
    cards=Cards()
    for ref,printing,field in ((ULTRA_BALL,'me01-131','effect'),(GUMSHOOS,'me01-110','abilities')):
        resolved=Registry().resolve(ref,cards)
        assert resolved.support=='REVIEWED'
        evidence=next(e for e in resolved.profile.evidence if e.kind=='CARD_TEXT')
        if field=='effect': assert evidence.content==cards.records[printing][field]
        else: assert json.loads(evidence.content)==cards.records[printing][field][0]
        assert resolved.profile.handler_version=='1' and resolved.profile.ref.version=='1'


def test_opponent_exchange_projection_is_independent_of_hidden_choices():
    state=scenario(); cards=Cards(); views=[]
    for key in ('pay1','pay2','keep'):
        candidate=action(state,True,Choices(exchange=key))
        result=evaluate(candidate,state,cards)
        views.append(apply_view(apply(candidate,state,cards,evaluated=result),'bob'))
    assert views[0]==views[1]==views[2]
