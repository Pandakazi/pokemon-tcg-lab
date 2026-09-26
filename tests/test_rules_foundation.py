"""Small deterministic A/B scenarios. No network, database or production writes."""
from copy import deepcopy
import pytest
from pydantic import ValidationError
from tcg_lab.cards import CardLookupError
from pokelab.collection import identity
from pokelab.engine import functional_signature
from pokelab.rules import (Action, CardInstance, Evaluation, Location, ODDISH, RULESET,
                           SWITCH, Registry, Scenario, apply, evaluate)
from pokelab.rules.models import Check, ProfileRef
from pokelab.rules.registry import builtin_profiles, reviewed_sources, source_fingerprint


class Cards:
    def __init__(self): self.records = reviewed_sources()
    def get(self, key, include_image=False):
        if key not in self.records: raise CardLookupError('Missing fixture')
        return {'card': deepcopy(self.records[key])}


@pytest.fixture
def cards(): return Cards()


def instance(key, owner, zone, printing='me02-001', position=0):
    card = reviewed_sources()[printing]
    return CardInstance(id=key, owner=owner, controller=owner,
        functional_id=identity(functional_signature(card)), printing_id=printing,
        profile=SWITCH if printing=='me01-130' else ODDISH,
        location=Location(player=owner, zone=zone, position=position))


@pytest.fixture
def state():
    return Scenario(ruleset=RULESET, revision=7, players=('p1','p2'), turn_player='p1',
        instances=(instance('switch','p1','resolving','me01-130'), instance('active','p1','active'),
                   instance('bench','p1','bench'), instance('opponent','p2','active')),
        unresolved_dependencies=(), isolation_confirmed=True)


def action(state, **changes):
    return Action(profile=changes.pop('profile',SWITCH), actor='p1', source=changes.pop('source','switch'),
        target=changes.pop('target','bench'), expected_revision=state.revision,
        expected_state_hash=state.state_hash(), **changes)


def change_instance(state, key, **changes):
    return state.model_copy(update={'instances':tuple(c.model_copy(update=changes) if c.id==key else c for c in state.instances)})


def test_reviewed_profiles_and_fingerprint_projection(cards):
    registry=Registry()
    for ref in (SWITCH,ODDISH):
        resolved=registry.resolve(ref,cards)
        assert resolved.support=='REVIEWED'
        assert resolved.profile.ruleset==RULESET
        assert {e.kind for e in resolved.profile.evidence}=={'CARD_TEXT','POKELAB_INTERPRETATION'}
        assert all(e.effective_from is None for e in resolved.profile.evidence)
    base=source_fingerprint(cards.records['me01-130'])
    cards.records['me01-130'].update(image='irrelevant',pricing={'amount':99},variants={'holo':True},set={'id':'me01','code':'MEG'})
    assert source_fingerprint(cards.records['me01-130'])==base
    assert registry.resolve(SWITCH,cards).support=='REVIEWED'


@pytest.mark.parametrize('change,expected',[
    ({'review_status':'UNREVIEWED'},'UNREVIEWED'),
    ({'review_status':'STALE'},'STALE'),
    ({'reviewed_by':None},'UNREVIEWED'),
    ({'evidence':()},'MISSING_EVIDENCE'),
    ({'handler_version':'future'},'VERSION_MISMATCH'),
    ({'ruleset':RULESET.model_copy(update={'version':'future'})},'VERSION_MISMATCH'),
])
def test_authority_gate(cards,state,change,expected):
    profile=builtin_profiles()[0].model_copy(update=change)
    registry=Registry((profile,))
    assert registry.resolve(SWITCH,cards).support==expected
    result=evaluate(action(state),state,cards,registry)
    assert result.status=='UNSUPPORTED' and result.delta is None


@pytest.mark.parametrize('field,value',[('effect','Changed effect'),('rarity','ACE SPEC Rare'),('newRuleField',True),('legal',{'standard':False})])
def test_source_changes_invalidate(cards,field,value):
    cards.records['me01-130'][field]=value
    assert Registry().resolve(SWITCH,cards).support=='STALE'


def test_unknown_missing_and_corrupt_evidence(cards):
    assert Registry().resolve(ProfileRef(id='not-implemented',version='1'),cards).support=='UNKNOWN'
    assert Registry().resolve(SWITCH.model_copy(update={'version':'2'}),cards).support=='UNKNOWN'
    profile=builtin_profiles()[0]
    bad=profile.evidence[0].model_copy(update={'content':'Changed without hash update'})
    assert Registry((profile.model_copy(update={'evidence':(bad,*profile.evidence[1:])}),)).resolve(SWITCH,cards).support=='MISSING_EVIDENCE'
    del cards.records['me01-130']
    assert Registry().resolve(SWITCH,cards).support=='MISSING_EVIDENCE'


def test_valid_switch_deterministic_exact_delta_and_immutable_apply(cards,state):
    before=state.model_dump_json(); candidate=action(state)
    result=evaluate(candidate,state,cards)
    assert result==evaluate(candidate,state,cards)
    assert result.status=='SUPPORTED_LEGAL' and result.scope=='switch-effect-only'
    assert [(m.instance,m.before.zone,m.after.zone) for m in result.delta.moves]==[('active','active','bench'),('bench','bench','active')]
    assert state.model_dump_json()==before
    assert Evaluation.model_validate_json(result.model_dump_json())==result
    applied=apply(candidate,state,cards,evaluated=result)
    assert applied.applied and applied.state.revision==8
    assert applied.state.state_hash()!=state.state_hash()
    expected={c.id:c for c in state.instances}
    expected['active']=expected['active'].model_copy(update={'location':state.instances[2].location})
    expected['bench']=expected['bench'].model_copy(update={'location':state.instances[1].location})
    assert {c.id:c for c in applied.state.instances}==expected
    assert state.model_dump_json()==before
    assert not apply(candidate,applied.state,cards,evaluated=result).applied


def test_choice_and_no_bench(cards,state):
    result=evaluate(action(state,target=None),state,cards)
    assert result.status=='NEEDS_CHOICE' and result.legal_targets==('bench',)
    assert result.required_choices==('target',) and result.delta is None
    assert not apply(action(state,target=None),state,cards,evaluated=result).applied
    empty=state.model_copy(update={'instances':tuple(c for c in state.instances if c.id!='bench')})
    result=evaluate(action(empty),empty,cards)
    assert result.status=='SUPPORTED_ILLEGAL' and result.checks[0].code=='BENCH_REQUIRED'


@pytest.mark.parametrize('key,change',[
    ('switch',{'owner':'p2'}), ('switch',{'controller':'p2'}),
    ('bench',{'owner':'p2'}), ('bench',{'controller':'p2'}),
    ('active',{'controller':'p2'}),
    ('switch',{'location':Location(player='p1',zone='hand')}),
    ('bench',{'location':Location(player='p1',zone='discard')}),
])
def test_wrong_owner_controller_or_zone(cards,state,key,change):
    altered=change_instance(state,key,**change); before=altered.model_dump_json()
    result=evaluate(action(altered),altered,cards)
    assert result.status=='SUPPORTED_ILLEGAL'
    assert not apply(action(altered),altered,cards,evaluated=result).applied
    assert altered.model_dump_json()==before


@pytest.mark.parametrize('target',['active','opponent','absent'])
def test_invalid_target(cards,state,target):
    assert evaluate(action(state,target=target),state,cards).status=='SUPPORTED_ILLEGAL'


def test_duplicate_and_invalid_location_rejected(state,cards):
    with pytest.raises(ValidationError):
        Scenario.model_validate({**state.model_dump(),'instances':(*state.instances,state.instances[0])})
    with pytest.raises(ValidationError):
        Scenario.model_validate({**state.model_dump(),'instances':(*state.instances,instance('duplicate-slot','p1','bench'))})
    with pytest.raises(ValidationError):Location(player='p1',zone='active',position=1)
    with pytest.raises(ValidationError):Location(player='p1',zone='lost-zone')
    corrupt=change_instance(state,'bench',location=state.instances[1].location)
    with pytest.raises(ValidationError):evaluate(action(corrupt),corrupt,cards)


def test_stale_revision_hash_and_forged_receipt(cards,state):
    candidate=action(state); result=evaluate(candidate,state,cards)
    for bad in (candidate.model_copy(update={'expected_revision':6}), candidate.model_copy(update={'expected_state_hash':'0'*64})):
        rejected=apply(bad,state,cards,evaluated=result)
        assert not rejected.applied and rejected.state==state
        assert rejected.evaluation.checks[0].code=='STALE_STATE'
    forged=result.model_copy(update={'checks':(Check(code='FAKE',message='Forged receipt'),)})
    assert not apply(candidate,state,cards,evaluated=forged).applied
    cards.records['me01-130']['effect']='Different'
    assert not apply(candidate,state,cards,evaluated=result).applied


@pytest.mark.parametrize('dependencies,isolation,status',[(None,True,'INSUFFICIENT_INFORMATION'),((),False,'INSUFFICIENT_INFORMATION'),(('unknown-stadium',),True,'UNSUPPORTED')])
def test_unknown_dependencies_never_legal(cards,state,dependencies,isolation,status):
    altered=state.model_copy(update={'unresolved_dependencies':dependencies,'isolation_confirmed':isolation})
    result=evaluate(action(altered),altered,cards)
    assert result.status==status and result.delta is None


def test_oddish_printed_preview_never_executes(cards,state):
    candidate=action(state,profile=ODDISH,source='active',target='opponent')
    result=evaluate(candidate,state,cards)
    assert result==evaluate(candidate,state,cards)
    assert result.support=='REVIEWED' and result.status=='INSUFFICIENT_INFORMATION'
    assert result.preview.printed_damage==20 and result.preview.printed_energy_cost==('Grass',)
    assert result.preview.executable is False and result.delta is None
    assert 'energy-payment' in result.missing_information
    assert 'weakness-resistance' in result.unsupported_dependencies
    assert not apply(candidate,state,cards,evaluated=result).applied
    assert evaluate(action(state,profile=ODDISH,source='bench',target='opponent'),state,cards).status=='SUPPORTED_ILLEGAL'
    assert evaluate(action(state,profile=ODDISH,source='active',target='bench'),state,cards).status=='SUPPORTED_ILLEGAL'


def test_versions_strict_input_and_identity(cards,state):
    with pytest.raises(ValidationError):Action.model_validate({**action(state).model_dump(),'expected_revision':True})
    with pytest.raises(ValidationError):Scenario.model_validate({**state.model_dump(),'attachments':[]})
    with pytest.raises(ValidationError):Scenario.model_validate({**state.model_dump(),'schema_version':2})
    altered=state.model_copy(update={'ruleset':RULESET.model_copy(update={'version':'historical'})})
    assert evaluate(action(altered),altered,cards).support=='VERSION_MISMATCH'
    altered=change_instance(state,'bench',functional_id='wrong')
    assert evaluate(action(altered),altered,cards).status=='INSUFFICIENT_INFORMATION'
    altered=change_instance(state,'switch',profile=ODDISH)
    assert evaluate(action(altered),altered,cards).status=='UNSUPPORTED'


def test_same_revision_changed_state_and_forged_delta_are_rejected(cards,state):
    candidate=action(state); result=evaluate(candidate,state,cards)
    changed=change_instance(state,'bench',location=Location(player='p1',zone='bench',position=1))
    assert changed.revision==state.revision and changed.state_hash()!=state.state_hash()
    assert not apply(candidate,changed,cards,evaluated=result).applied
    forged=result.model_copy(update={'delta':result.delta.model_copy(update={'moves':()})})
    assert not apply(candidate,state,cards,evaluated=forged).applied
    reordered=state.model_copy(update={'instances':tuple(reversed(state.instances))})
    assert reordered.state_hash()==state.state_hash()
    assert evaluate(candidate,reordered,cards)==result


@pytest.mark.parametrize('bad',[True,'1',1.0])
def test_schema_version_rejects_coercions(state,bad):
    with pytest.raises(ValidationError):Scenario.model_validate({**state.model_dump(),'schema_version':bad})


def test_unregistered_cases_and_provider_failure(cards,state):
    for key in ('ultra-ball','gumshoos','poffin','rescue-board'):
        candidate=action(state).model_copy(update={'profile':ProfileRef(id=key,version='1')})
        assert evaluate(candidate,state,cards).status=='UNSUPPORTED'
    class Unavailable:
        def get(self,*args): raise OSError('Offline cache unavailable')
    assert evaluate(action(state),state,Unavailable()).status=='UNSUPPORTED'
