"""Persistent single-modifier proof, including malformed state and unknown effects."""
from copy import deepcopy
import json
import pytest
from pydantic import ValidationError
from pokelab.collection import identity
from pokelab.engine import functional_signature
from pokelab.rules import (Action, CardInstance, Location, RESCUE_BOARD, RULESET, Registry,
                           Scenario, apply, evaluate, evaluation_view)
from pokelab.rules.registry import reviewed_sources, source_fingerprint


class Cards:
    def __init__(self): self.records=reviewed_sources()
    def get(self,key,include_image=False): return {'card':deepcopy(self.records[key])}


def state(cards,damage=0):
    def card(key,printing,zone,**fields):
        return CardInstance(id=key,owner='alice',controller='alice',printing_id=printing,
            functional_id=identity(functional_signature(cards.records[printing])),
            location=Location(player='alice',zone=zone),**fields)
    return Scenario(ruleset=RULESET,revision=4,players=('alice','bob'),turn_player='alice',
        isolation_confirmed=True,unresolved_dependencies=(),instances=(
            card('host','me02-001','active',damage_counters=damage),
            card('tool','sv05-159','attached',attached_to='host',profile=RESCUE_BOARD),
            card('concealed-hand','me01-110','hand'),card('concealed-deck','me01-130','deck')))


def action(s):
    return Action(profile=RESCUE_BOARD,actor='alice',source='tool',expected_revision=s.revision,expected_state_hash=s.state_hash())


def change(s,key,**fields):
    return s.model_copy(update={'instances':tuple(c.model_copy(update=fields) if c.id==key else c for c in s.instances)})


@pytest.mark.parametrize('base,damage,expected,condition',[(3,0,2,False),(3,1,2,False),(3,2,0,True),
    (3,3,0,True),(1,0,0,False),(0,0,0,False),(0,2,0,True)])
def test_exact_derivation_and_no_execution(base,damage,expected,condition):
    cards=Cards(); cards.records['me02-001']['retreat']=base
    s=state(cards,damage); before=s.model_dump_json(); records=deepcopy(cards.records)
    result=evaluate(action(s),s,cards)
    assert result.status=='SUPPORTED_LEGAL' and result.scope=='attached-retreat-cost-only'
    d=result.derivation
    assert d.base_printed_cost==base and d.derived_cost==expected and d.remaining_hp==50-damage*10
    assert d.modifier.condition_satisfied is condition
    assert d.modifier.operation==('set-zero' if condition else 'subtract-floor-zero')
    assert d.modifier.amount==(0 if condition else 1)
    assert d.modifier.source=='tool' and d.modifier.affected=='host' and d.modifier.duration=='while-attached'
    assert d.executable is False and result.delta is None
    assert evaluate(action(s),s,cards)==result
    assert type(result).model_validate_json(result.model_dump_json())==result
    applied=apply(action(s),s,cards,evaluated=result)
    assert not applied.applied and applied.state==s and s.model_dump_json()==before and cards.records==records


def test_profile_exact_source_identity_and_fingerprint():
    cards=Cards(); resolved=Registry().resolve(RESCUE_BOARD,cards); p=resolved.profile
    assert resolved.support=='REVIEWED' and p.printing_id=='sv05-159'
    source=cards.records['sv05-159']
    assert source['category']=='Trainer' and source['trainerType']=='Tool'
    assert p.functional_id==identity(functional_signature(source))
    assert p.source_fingerprint==source_fingerprint(source)
    assert p.evidence[0].content==source['effect'] and p.evidence[0].field_path=='/effect'
    assert p.handler_version=='1' and p.ref.version=='1'


@pytest.mark.parametrize('change_fields',[
    {'attached_to':'missing'}, {'attached_to':'concealed-hand'}, {'attached_to':'tool'},
    {'attached_to':None}, {'owner':'bob'}, {'controller':'bob'},
    {'location':Location(player='bob',zone='attached')}, {'location':Location(player='alice',zone='hand',position=1)}])
def test_malformed_attachment_rejected(change_fields):
    cards=Cards(); s=change(state(cards),'tool',**change_fields)
    with pytest.raises(ValidationError): evaluate(action(s),s,cards)


def test_duplicates_identity_and_non_pokemon_host():
    cards=Cards(); s=state(cards)
    for extra in (s.instances[1],s.instances[1].model_copy(update={'id':'duplicate-slot'})):
        bad=s.model_copy(update={'instances':(*s.instances,extra)})
        with pytest.raises(ValidationError): evaluate(action(bad),bad,cards)
    bad=change(s,'tool',functional_id='wrong')
    assert evaluate(action(bad),bad,cards).status=='UNSUPPORTED'
    bad=change(s,'tool',profile=None)
    assert evaluate(action(bad),bad,cards).status=='UNSUPPORTED'
    bad=change(s,'host',printing_id='me01-130',functional_id=identity(functional_signature(cards.records['me01-130'])))
    assert evaluate(action(bad),bad,cards).status=='INSUFFICIENT_INFORMATION'


@pytest.mark.parametrize('deps,isolation,status',[(('unknown-retreat-effect',),True,'UNSUPPORTED'),
    (('hp-modifier',),True,'UNSUPPORTED'),(None,True,'INSUFFICIENT_INFORMATION'),((),False,'INSUFFICIENT_INFORMATION')])
def test_unknowns_block_final_cost(deps,isolation,status):
    cards=Cards(); s=state(cards).model_copy(update={'unresolved_dependencies':deps,'isolation_confirmed':isolation})
    result=evaluate(action(s),s,cards)
    assert result.status==status and result.derivation is None and result.delta is None


def test_multiple_attachments_fail_without_stacking():
    cards=Cards(); s=state(cards)
    extra=s.instances[1].model_copy(update={'id':'second','location':Location(player='alice',zone='attached',position=1)})
    s=s.model_copy(update={'instances':(*s.instances,extra)})
    result=evaluate(action(s),s,cards)
    assert result.status=='UNSUPPORTED' and result.derivation is None
    assert result.unsupported_dependencies==('attachment-modifier-stacking',)


@pytest.mark.parametrize('field,value',[('hp',None),('hp','50'),('retreat',None),('retreat',-1),('retreat',True)])
def test_missing_or_invalid_printed_inputs(field,value):
    cards=Cards(); cards.records['me02-001'][field]=value; s=state(cards)
    assert evaluate(action(s),s,cards).status=='INSUFFICIENT_INFORMATION'


def test_missing_damage_knockout_boundary_and_persistent_off_turn():
    cards=Cards()
    for damage,status in ((None,'INSUFFICIENT_INFORMATION'),(5,'UNSUPPORTED'),(6,'UNSUPPORTED')):
        s=state(cards,damage); assert evaluate(action(s),s,cards).status==status
    s=state(cards).model_copy(update={'turn_player':'bob'})
    assert evaluate(action(s),s,cards).derivation.derived_cost==0


@pytest.mark.parametrize('field,value',[('effect','Changed'),('trainerType','Item'),('regulationMark','X')])
def test_changed_source_blocks(field,value):
    cards=Cards(); s=state(cards); cards.records['sv05-159'][field]=value
    result=evaluate(action(s),s,cards)
    assert result.support=='STALE' and result.derivation is None


def test_public_perspective_no_unrelated_hidden_data_and_stale_input():
    cards=Cards(); s=state(cards,2); result=evaluate(action(s),s,cards)
    for player in s.players:
        visible=evaluation_view(result,player,players=s.players)
        text=json.dumps(visible)
        assert visible['derivation']['derived_cost']==0
        assert all(secret not in text for secret in ('concealed-hand','concealed-deck',s.state_hash()))
    changed=change(s,'host',damage_counters=0)
    assert evaluate(action(s),changed,cards).checks[0].code=='STALE_STATE'
    unattached=change(s,'tool',attached_to=None,location=Location(player='alice',zone='discard'))
    assert evaluate(action(unattached),unattached,cards).checks[0].code=='ATTACHMENT_REQUIRED'
