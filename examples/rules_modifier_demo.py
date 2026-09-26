"""Read-only Rescue Board derivation proof; no attachment or retreat execution."""
import argparse
import json
from pokelab.collection import identity
from pokelab.engine import functional_signature
from pokelab.rules import Action, CardInstance, Location, RESCUE_BOARD, RULESET, Registry, Scenario, apply, evaluate
from rules_foundation_demo import ExcerptCards


class DemoCards(ExcerptCards):
    def get(self, key, include_image=False):
        if key == 'me01-001':
            # Exact cached host excerpt, not a reviewed/executable attack profile.
            return {'card': dict(category='Pokemon', id=key, name='Bulbasaur', rarity='Common',
                hp=80, types=['Grass'], stage='Basic', attacks=[dict(cost=['Grass'], name='Bind Down',
                effect="During your opponent's next turn, the Defending Pokémon can't retreat.", damage=10)],
                weaknesses=[dict(type='Fire', value='×2')], retreat=2, regulationMark='I',
                legal={'standard':True,'expanded':True})}
        return super().get(key, include_image)


def scenario(cards, counters=0):
    def instance(key, printing, zone, **fields):
        return CardInstance(id=key, owner='alice', controller='alice', printing_id=printing,
            functional_id=identity(functional_signature(cards.get(printing)['card'])),
            location=Location(player='alice', zone=zone), **fields)
    return Scenario(ruleset=RULESET, revision=0, players=('alice','bob'), turn_player='alice',
        isolation_confirmed=True, unresolved_dependencies=(), instances=(
            instance('host','me01-001','active',damage_counters=counters),
            instance('board','sv05-159','attached',attached_to='host',profile=RESCUE_BOARD)))


def action(state):
    return Action(profile=RESCUE_BOARD, actor='alice', source='board', expected_revision=state.revision,
                  expected_state_hash=state.state_hash())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cards',help='Existing cards.sqlite3, opened read-only.')
    args=parser.parse_args()
    if args.cards:
        from pokelab.api import ReadOnlyCards
        cards=ReadOnlyCards(args.cards)
    else:
        cards=DemoCards()
    resolved=Registry().resolve(RESCUE_BOARD,cards)
    assert resolved.support=='REVIEWED', resolved.reason
    results=[]
    for counters in (0,5):
        state=scenario(cards,counters); before=state.model_dump_json(); candidate=action(state)
        result=evaluate(candidate,state,cards)
        assert result.derivation is not None and result.delta is None
        assert result.derivation.modifier.condition_satisfied == (counters==5)
        assert result.derivation.derived_cost == (0 if counters==5 else 1)
        assert not apply(candidate,state,cards,evaluated=result).applied and state.model_dump_json()==before
        results.append(result.derivation.model_dump(mode='json'))
    unknown=state.model_copy(update={'unresolved_dependencies':('unknown-retreat-modifier',)})
    blocked=evaluate(action(unknown),unknown,cards)
    assert blocked.status=='UNSUPPORTED' and blocked.derivation is None
    class Changed:
        def get(self,key,include_image=False):
            from copy import deepcopy
            record=deepcopy(cards.get(key))
            if key=='sv05-159': record['card']['effect']='Changed source text'
            return record
    stale=Registry().resolve(RESCUE_BOARD,Changed())
    assert stale.support=='STALE'
    print(json.dumps(dict(profile=resolved.profile.model_dump(mode='json'),derivations=results,
        unknown_modifier=blocked.status,source_change=stale.support,no_delta=True,no_mutation=True),indent=2,ensure_ascii=False))
    print('PASS D DEMO PASSED — NOT PM CERTIFICATION')


if __name__=='__main__':
    main()
