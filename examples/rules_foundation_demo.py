"""Read-only A/B review harness. No API server, matches, deck or collection writes.

Run with PYTHONPATH=src. Default: pinned deterministic source excerpts.
Optional --cards PATH verifies and uses the existing local read-only card provider.
"""
import argparse
from copy import deepcopy
import json

from pokelab.collection import identity
from pokelab.engine import functional_signature
from pokelab.rules import Action, CardInstance, Location, ODDISH, RULESET, SWITCH, Registry, Scenario, apply, evaluate
from pokelab.rules.registry import reviewed_sources


class ExcerptCards:
    def get(self, printing_id, include_image=False):
        return {'card': deepcopy(reviewed_sources()[printing_id])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cards', help='Existing cards.sqlite3; opened read-only.')
    args = parser.parse_args()
    if args.cards:
        from pokelab.api import ReadOnlyCards
        cards = ReadOnlyCards(args.cards)
    else:
        cards = ExcerptCards()
    registry = Registry()
    resolutions = [registry.resolve(ref, cards) for ref in (SWITCH, ODDISH)]
    if any(r.support != 'REVIEWED' for r in resolutions):
        print(json.dumps([r.model_dump(mode='json') for r in resolutions], indent=2))
        raise SystemExit('Source mismatch/unavailable: no scenario was executed. Review the profile before proceeding.')

    def instance(key, owner, zone, printing='me02-001'):
        return CardInstance(id=key, owner=owner, controller=owner,
            functional_id=identity(functional_signature(cards.get(printing)['card'])), printing_id=printing,
            profile=SWITCH if printing=='me01-130' else ODDISH, location=Location(player=owner,zone=zone))

    state = Scenario(ruleset=RULESET, revision=0, players=('alice','bob'), turn_player='alice',
        instances=(instance('switch','alice','resolving','me01-130'),instance('active','alice','active'),
                   instance('bench','alice','bench'),instance('opponent','bob','active')),
        isolation_confirmed=True, unresolved_dependencies=())
    before = state.model_dump_json()
    candidate = Action(profile=SWITCH, actor='alice', source='switch', target='bench',
                       expected_revision=state.revision, expected_state_hash=state.state_hash())
    result = evaluate(candidate,state,cards)
    applied = apply(candidate,state,cards,evaluated=result)
    preview = evaluate(candidate.model_copy(update={'profile':ODDISH,'source':'active','target':'opponent'}),state,cards)
    stale = apply(candidate,applied.state,cards,evaluated=result)
    assert before == state.model_dump_json()
    print(json.dumps(dict(ruleset=RULESET.model_dump(),
        profile_support=[r.support for r in resolutions], switch=result.model_dump(mode='json'),
        applied=applied.applied, applied_revision=applied.state.revision,
        original_unchanged=True, stale_apply_rejected=not stale.applied,
        oddish=preview.model_dump(mode='json')),indent=2,ensure_ascii=False))


if __name__ == '__main__':
    main()
