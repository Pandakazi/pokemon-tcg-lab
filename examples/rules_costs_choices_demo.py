"""Read-only Pass C PM harness. No server, database writes or turn engine.

Run with PYTHONPATH=src; optional --cards PATH checks the real read-only cache.
The output intentionally separates trusted evidence/steps from player projections.
"""
import argparse
import json
from pokelab.collection import identity
from pokelab.engine import functional_signature
from pokelab.rules import (Action, CardInstance, Choices, GUMSHOOS, Location, RULESET,
                           ULTRA_BALL, Registry, Scenario, apply, evaluate,
                           apply_view, evaluation_view)
from rules_foundation_demo import ExcerptCards


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cards', help='Existing cards.sqlite3; opened read-only.')
    args=parser.parse_args()
    if args.cards:
        from pokelab.api import ReadOnlyCards
        cards=ReadOnlyCards(args.cards)
    else:
        cards=ExcerptCards()
    profiles=[Registry().resolve(ref,cards) for ref in (ULTRA_BALL,GUMSHOOS)]
    if any(p.support!='REVIEWED' for p in profiles):
        raise SystemExit('Profile/source mismatch: no effect executed. Re-review the source.')

    def card(key,zone,position=0,printing='me02-001',profile=None):
        return CardInstance(id=key,owner='alice',controller='alice',printing_id=printing,
            functional_id=identity(functional_signature(cards.get(printing)['card'])),profile=profile,
            location=Location(player='alice',zone=zone,position=position))

    state=Scenario(ruleset=RULESET,revision=0,players=('alice','bob'),turn_player='alice',turn='alice-turn-1',
        isolation_confirmed=True,unresolved_dependencies=(),instances=(
            card('ultra','resolving',printing='me01-131',profile=ULTRA_BALL),
            card('gum','active',printing='me01-110',profile=GUMSHOOS),
            card('payment-a','hand',0),card('payment-b','hand',1,printing='me01-130'),card('kept','hand',2),
            card('concealed-top','deck',0,printing='me01-130'),card('selected-pokemon','deck',1),
            card('concealed-other','deck',2)))
    before=state.model_dump_json()

    def propose(s,ref,source,choices):
        return Action(profile=ref,actor='alice',source=source,choices=choices,
                      expected_revision=s.revision,expected_state_hash=s.state_hash())

    empty=propose(state,ULTRA_BALL,'ultra',Choices())
    need_cost=evaluate(empty,state,cards)
    paid=propose(state,ULTRA_BALL,'ultra',Choices(payment=('payment-a','payment-b')))
    need_search=evaluate(paid,state,cards)
    full=propose(state,ULTRA_BALL,'ultra',Choices(payment=('payment-a','payment-b'),search='selected-pokemon',
                                                shuffle=('concealed-other','concealed-top')))
    ultra=evaluate(full,state,cards); applied=apply(full,state,cards,evaluated=ultra)
    invalid=full.model_copy(update={'choices':full.choices.model_copy(update={'payment':('payment-a','payment-a')})})
    failed=apply(invalid,state,cards,evaluated=ultra)
    assert applied.applied and not failed.applied and failed.state==state
    assert apply_view(applied,'bob')['reveals']==[dict(instance='selected-pokemon',printing='me02-001')]

    gum_action=propose(state,GUMSHOOS,'gum',Choices(exchange='kept'))
    gum=evaluate(gum_action,state,cards); exchanged=apply(gum_action,state,cards,evaluated=gum)
    repeat=propose(exchanged.state,GUMSHOOS,'gum',Choices(exchange='payment-a'))
    repeat_result=evaluate(repeat,exchanged.state,cards)
    next_turn=exchanged.state.model_copy(update={'turn':'alice-turn-2','revision':2})
    reset=evaluate(propose(next_turn,GUMSHOOS,'gum',Choices(exchange='payment-a')),next_turn,cards)
    stale=apply(gum_action,exchanged.state,cards,evaluated=gum)
    assert exchanged.applied and repeat_result.checks[0].code=='ALREADY_USED'
    assert reset.status=='SUPPORTED_LEGAL' and not stale.applied and state.model_dump_json()==before
    bob=apply_view(exchanged,'bob')
    assert 'concealed-top' not in json.dumps(bob) and 'kept' not in json.dumps(bob)
    print(json.dumps(dict(
        checkpoint='PASS C DEMO PASSED — NOT PM CERTIFICATION',
        provenance=[p.profile.model_dump(mode='json') for p in profiles],
        ultra_ball=dict(choice_stages=[need_cost.required_choices,need_search.required_choices],
            trusted_ordered_steps=[s.model_dump(mode='json') for s in ultra.delta.steps],
            applied=applied.applied,invalid_cost_atomic=failed.state==state,bob=apply_view(applied,'bob')),
        evidence_gathering=dict(applied=exchanged.applied,
            pending_bob=evaluation_view(gum,'bob',players=state.players),
            alice=apply_view(exchanged,'alice'),bob=bob,
            usage=[u.model_dump(mode='json') for u in exchanged.state.usage],
            repeat=repeat_result.checks[0].code,next_turn=reset.status,stale_rejected=not stale.applied),
        original_unchanged=True),ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
