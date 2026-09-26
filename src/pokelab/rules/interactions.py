"""Two bounded handlers sharing the foundation's receipts and atomic delta."""
from .models import Choice, Delta, Location, Move, Step, Usage


def evaluate_interaction(action, state, source, profile, records, result):
    actor = action.actor
    supplied = action.choices
    by_id = {c.id: c for c in state.instances}

    def zone(name):
        return tuple(c.id for c in sorted(state.instances, key=lambda c: c.location.position)
                     if c.location.player == actor and c.location.zone == name)

    def own(key):
        return by_id[key].owner == actor and by_id[key].controller == actor

    hand, deck = zone('hand'), zone('deck')
    # Mixed ownership/control of these private zones is outside this proof.
    if any(not own(key) for key in (*hand, *deck)):
        return result('UNSUPPORTED', 'PRIVATE_ZONE_CONTROL', 'Own hand/deck control must be established.',
                      unsupported_dependencies=('private-zone-control',))
    if action.target is not None:
        return result('SUPPORTED_ILLEGAL', 'EXTRA_TARGET', 'Use the typed choices for this profile.')

    def choice(key, kind, candidates, cardinality, selected, constraint):
        rejection = None
        if selected is not None and (len(selected) != cardinality or len(set(selected)) != len(selected)
                                     or not set(selected).issubset(candidates)):
            rejection = constraint
        return Choice(id=key, kind=kind, candidates=candidates, cardinality=cardinality,
                      supplied=selected, constraint=constraint, rejection=rejection)

    def incomplete(choices):
        if any(c.rejection for c in choices):
            return result('SUPPORTED_ILLEGAL', 'INVALID_CHOICE', 'A supplied choice violates its contract.', choices=choices)
        missing = tuple(c.id for c in choices if c.supplied is None)
        if missing:
            return result('NEEDS_CHOICE', 'CHOICES_REQUIRED', 'Supply the unresolved choices/resolution.',
                          choices=choices, required_choices=missing)
        return None

    def delta(destinations, steps, usage=()):
        moves = tuple(Move(instance=key, before=by_id[key].location, after=after)
                      for key, after in sorted(destinations.items()) if by_id[key].location != after)
        return Delta(base_revision=state.revision, base_hash=state.state_hash(),
                     next_revision=state.revision + 1, moves=moves, steps=steps, usage_added=usage)

    def layout(destinations, name, ids):
        for position, key in enumerate(ids):
            destinations[key] = Location(player=actor, zone=name, position=position)

    if profile.handler == 'ultra-ball':
        if source.location.zone != 'resolving':
            return result('SUPPORTED_ILLEGAL', 'SOURCE_ZONE', 'Ultra Ball must already be resolving; Item play legality is outside scope.')
        if supplied.exchange is not None:
            return result('SUPPORTED_ILLEGAL', 'EXTRA_CHOICE', 'Exchange is not an Ultra Ball choice.')
        payments = tuple(key for key in hand if key != source.id)
        cost = choice('payment', 'cost', payments, 2, supplied.payment,
                      'Exactly two distinct other owned/controlled hand instances are required.')
        if len(payments) < 2:
            return result('SUPPORTED_ILLEGAL', 'COST_UNPAYABLE', 'Fewer than two eligible payment instances.', choices=(cost,))
        # Do not expose search candidates before a valid cost proposal exists.
        pending = incomplete((cost,))
        if pending is not None:
            return pending
        # Candidate order must not disclose the deck's hidden order to the actor.
        targets = tuple(sorted(key for key in deck if records[key]['category'] == 'Pokemon'))
        search = choice('search', 'search', targets, 1,
                        None if supplied.search is None else (supplied.search,),
                        'Exactly one owned/controlled Pokemon instance from the acting deck is required.')
        choices = (cost, search)
        if cost.rejection or search.rejection:
            return incomplete(choices)
        if not targets:
            return result('UNSUPPORTED', 'NO_RESULT_SEARCH', 'No eligible Pokemon; no-result search rules are not reviewed.',
                          choices=choices, unsupported_dependencies=('no-result-search-rule',))
        if supplied.search is None:
            # A permutation is meaningful only after a search result is selected.
            return incomplete(choices)
        remaining = tuple(key for key in deck if key != supplied.search)
        shuffle = choice('shuffle', 'resolution', remaining, len(remaining), supplied.shuffle,
                         'Trusted resolver must provide each remaining own deck instance exactly once, in resolved order.')
        choices = (*choices, shuffle)
        pending = incomplete(choices)
        if pending is not None:
            return pending
        destinations = {}
        layout(destinations, 'hand', (*[key for key in hand if key not in supplied.payment], supplied.search))
        layout(destinations, 'discard', (*zone('discard'), *supplied.payment))
        layout(destinations, 'deck', supplied.shuffle)
        steps = (
            Step(phase='cost', operation='discard', instances=supplied.payment),
            Step(phase='effect', operation='search', instances=(supplied.search,)),
            Step(phase='effect', operation='reveal', instances=(supplied.search,)),
            Step(phase='effect', operation='move-to-hand', instances=(supplied.search,)),
            Step(phase='effect', operation='shuffle', instances=supplied.shuffle),
        )
        return result('SUPPORTED_LEGAL', 'ISOLATED_ULTRA_BALL', 'The bounded cost and effect can resolve atomically.',
                      choices=choices, delta=delta(destinations, steps))

    if source.location.zone not in ('active', 'bench'):
        return result('SUPPORTED_ILLEGAL', 'SOURCE_ZONE', 'Evidence Gathering requires this own in-play Gumshoos.')
    if any(value is not None for value in (supplied.payment, supplied.search, supplied.shuffle)):
        return result('SUPPORTED_ILLEGAL', 'EXTRA_CHOICE', 'Only the hand exchange choice belongs to this Ability.')
    if state.turn is None:
        return result('INSUFFICIENT_INFORMATION', 'TURN_REQUIRED', 'An externally established turn token is required.',
                      missing_information=('turn-token',))
    usage = Usage(turn=state.turn, player=actor, effect='Evidence Gathering', scope='instance', instance=source.id)
    if any(u.turn == state.turn and u.player == actor and u.effect == usage.effect and u.scope != usage.scope
           for u in state.usage):
        return result('UNSUPPORTED', 'USAGE_SCOPE', 'Ledger scope conflicts with this reviewed instance restriction.',
                      unsupported_dependencies=('matching-usage-scope',))
    if usage in state.usage:
        return result('SUPPORTED_ILLEGAL', 'ALREADY_USED', 'This source instance used Evidence Gathering during this turn.')
    if not hand or not deck:
        return result('SUPPORTED_ILLEGAL', 'EXCHANGE_UNAVAILABLE', 'An own hand card and a top deck card are required.')
    exchange = choice('exchange', 'exchange', hand, 1,
                      None if supplied.exchange is None else (supplied.exchange,),
                      'Choose exactly one owned/controlled hand instance.')
    pending = incomplete((exchange,))
    if pending is not None:
        return pending
    # Swap slots, preserving the rest of both ordered zones without revealing top.
    destinations = {supplied.exchange: by_id[deck[0]].location, deck[0]: by_id[supplied.exchange].location}
    steps = (Step(phase='effect', operation='exchange', instances=(supplied.exchange, deck[0])),
             Step(phase='effect', operation='record-usage', instances=(source.id,)))
    return result('SUPPORTED_LEGAL', 'ISOLATED_EVIDENCE_GATHERING', 'The private exchange and instance usage can resolve atomically.',
                  choices=(exchange,), delta=delta(destinations, steps, (usage,)))
