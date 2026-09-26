"""Small player projections. Raw scenarios/receipts are trusted-engine data only.

No player gets deck order, private state hashes, raw deltas or unresolved reveals.
This is filtering, not authentication: the host supplies the authenticated player
and must only pass evaluator-produced receipts/results, never client-made objects.
"""


def state_view(state, player):
    if player not in state.players:
        raise ValueError('Unknown perspective.')
    zones = []
    for owner in state.players:
        for name in ('active', 'bench', 'resolving', 'discard', 'hand', 'deck', 'attached'):
            cards = sorted((c for c in state.instances if c.location.player == owner and c.location.zone == name),
                           key=lambda c: c.location.position)
            visible = name != 'deck' and (name != 'hand' or owner == player)
            zone = dict(player=owner, zone=name, count=len(cards))
            if visible:
                zone['cards'] = [dict(instance=c.id, printing=c.printing_id) for c in cards]
            zones.append(zone)
    return dict(revision=state.revision, turn_player=state.turn_player, zones=zones)


def evaluation_view(evaluation, player, *, players):
    if player not in players:
        raise ValueError('Unknown perspective.')
    if evaluation.derivation is not None:
        # Derivation contains public in-play source/host data only, never the action
        # hash, hidden zones or a gameplay delta. Retreat is explicitly non-executable.
        return dict(status=evaluation.status, scope=evaluation.scope,
                    derivation=evaluation.derivation.model_dump(mode='json'), limitations=evaluation.limitations)
    # Even status/checks on an opponent's pending private choice can be an oracle.
    if player != evaluation.action.actor:
        return {'visibility': 'private-pending-resolution'}
    # No delta/preview/hash: they can expose the top card or permutation before apply.
    return dict(status=evaluation.status, scope=evaluation.scope, support=evaluation.support,
                required_choices=evaluation.required_choices,
                choices=[c.model_dump(mode='json') for c in evaluation.choices if c.kind != 'resolution'],
                checks=[dict(code=c.code) for c in evaluation.checks],
                unsupported_dependencies=evaluation.unsupported_dependencies)


def apply_view(applied, player):
    view = dict(applied=applied.applied, state=state_view(applied.state, player), reveals=[])
    # Failed/proposed effects reveal nothing. Successful Ultra Ball reveals only its
    # selected Pokemon (discarded cost cards are already in the public discard zone).
    if applied.applied and applied.evaluation.delta:
        cards = {c.id: c for c in applied.state.instances}
        for step in applied.evaluation.delta.steps:
            if step.operation == 'reveal':
                view['reveals'].extend(dict(instance=key, printing=cards[key].printing_id) for key in step.instances)
    return view
