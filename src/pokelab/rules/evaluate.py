"""Pure evaluation/apply over caller-owned isolated scenarios. No persistence."""
from sqlite3 import Error as SQLiteError
from tcg_lab.cards import CardLookupError, CardProvider
from pokelab.collection import identity
from pokelab.engine import functional_signature
from .models import (Action, ApplyResult, Check, Choices, DamagePreview, Delta, Evaluation,
                     Move, Scenario)
from .registry import Registry


def evaluate(action: Action, state: Scenario, cards: CardProvider, registry: Registry | None = None) -> Evaluation:
    # Revalidate even model_copy/model_construct inputs; those bypass Pydantic checks.
    action = Action.model_validate(action.model_dump())
    state = Scenario.model_validate(state.model_dump())
    registry = registry or Registry()
    resolution = registry.resolve(action.profile, cards, state.ruleset)
    profile = resolution.profile
    base = dict(action=action, ruleset=state.ruleset, state_revision=state.revision,
        state_hash=state.state_hash(), support=resolution.support,
        scope=profile.scope if profile else 'unresolved',
        evidence=profile.evidence if profile else (), interpretation=profile.ref if profile else None,
        handler_version=profile.handler_version if profile else None,
        limitations=profile.limitations if profile else ())

    def result(status, code, message, **fields):
        return Evaluation(**base, status=status, checks=(Check(code=code, message=message),), **fields)

    if action.expected_revision != state.revision or action.expected_state_hash != state.state_hash():
        return result('INSUFFICIENT_INFORMATION', 'STALE_STATE', 'Re-evaluate against the current revision and state hash.',
                      missing_information=('current-state-action',))
    if resolution.support != 'REVIEWED':
        return result('UNSUPPORTED', resolution.support, resolution.reason,
                      unsupported_dependencies=('reviewed-matching-profile',))
    if not state.isolation_confirmed or state.unresolved_dependencies is None:
        return result('INSUFFICIENT_INFORMATION', 'ISOLATION_REQUIRED',
            'Caller must explicitly establish this is an isolated scenario; the engine does not infer absent effects.',
            missing_information=('isolation-confirmation', 'assessed-relevant-dependencies'))
    if state.unresolved_dependencies:
        return result('UNSUPPORTED', 'UNKNOWN_DEPENDENCIES', 'Relevant unmodelled interactions prevent certainty.',
                      unsupported_dependencies=state.unresolved_dependencies)
    if profile.handler in ('switch-effect', 'printed-damage') and action.choices != Choices():
        return result('UNSUPPORTED', 'EXTRA_CHOICES', 'This profile does not interpret Pass C choices.')

    instances = {c.id: c for c in state.instances}
    source = instances.get(action.source)
    if action.actor not in state.players or action.actor != state.turn_player:
        return result('SUPPORTED_ILLEGAL', 'ACTOR', 'Actor must be the turn owner in this isolated scope.')
    if source is None:
        return result('SUPPORTED_ILLEGAL', 'SOURCE', 'Source instance does not exist.')
    if source.owner != action.actor or source.controller != action.actor or source.location.player != action.actor:
        return result('SUPPORTED_ILLEGAL', 'SOURCE_CONTROL', 'Source must be owned, controlled and located with the actor.')
    if source.profile != action.profile or source.printing_id != profile.printing_id or source.functional_id != profile.functional_id:
        return result('UNSUPPORTED', 'INSTANCE_PROFILE', 'Source instance does not match the reviewed printing, function and profile.')

    # One detached lookup per relevant instance. No canonical/collection mutation.
    resolved = {}
    for card in state.instances:
        if (card.id == source.id or card.location.zone in ('active', 'bench')
            or (profile.handler in ('ultra-ball', 'evidence-gathering') and card.location.player == action.actor)):
            try:
                record = cards.get(card.printing_id)['card']
                if record['id'] != card.printing_id or identity(functional_signature(record)) != card.functional_id:
                    raise ValueError('Instance identity mismatch')
                if card.location.zone in ('active', 'bench') and record['category'] != 'Pokemon':
                    raise ValueError('Active/Bench object is not a Pokemon')
                resolved[card.id] = record
            except (CardLookupError, KeyError, TypeError, ValueError, OSError, SQLiteError):
                return result('INSUFFICIENT_INFORMATION', 'INSTANCE_DATA', 'Relevant instance data is missing or inconsistent.',
                              missing_information=(card.id,))

    # Check again against the exact record used below (provider may refresh between reads).
    from .registry import source_fingerprint
    if source_fingerprint(resolved[source.id]) != profile.source_fingerprint:
        return result('UNSUPPORTED', 'SOURCE_CHANGED', 'Source changed during evaluation; re-review is required.',
                      unsupported_dependencies=('matching-source-fingerprint',))

    if profile.handler in ('ultra-ball', 'evidence-gathering'):
        from .interactions import evaluate_interaction
        return evaluate_interaction(action, state, source, profile, resolved, result)

    if profile.handler == 'switch-effect':
        if source.location.zone != 'resolving':
            return result('SUPPORTED_ILLEGAL', 'SOURCE_ZONE', 'Switch must already be in the resolving zone; playing the Item is outside scope.')
        active = next((c for c in state.instances if c.location.player == action.actor and c.location.zone == 'active'), None)
        if active is None or active.owner != action.actor or active.controller != action.actor:
            return result('SUPPORTED_ILLEGAL', 'ACTIVE_REQUIRED', 'An owned and controlled Active Pokemon is required.')
        targets = tuple(sorted(c.id for c in state.instances if c.location.player == action.actor
                        and c.location.zone == 'bench' and c.owner == action.actor and c.controller == action.actor))
        if not targets:
            return result('SUPPORTED_ILLEGAL', 'BENCH_REQUIRED', 'No eligible own Benched Pokemon exists.')
        if action.target is None:
            return result('NEEDS_CHOICE', 'CHOOSE_BENCH', 'Choose exactly one eligible Bench instance.',
                          legal_targets=targets, required_choices=('target',))
        if action.target not in targets:
            return result('SUPPORTED_ILLEGAL', 'TARGET', 'Target is not an eligible own Benched Pokemon.', legal_targets=targets)
        target = instances[action.target]
        delta = Delta(base_revision=state.revision, base_hash=state.state_hash(), next_revision=state.revision+1,
            moves=(Move(instance=active.id, before=active.location, after=target.location),
                   Move(instance=target.id, before=target.location, after=active.location)))
        return result('SUPPORTED_LEGAL', 'ISOLATED_SWITCH', 'The isolated already-authorized Switch effect can resolve.',
                      legal_targets=targets, delta=delta)

    if profile.handler == 'printed-damage':
        if source.location.zone != 'active':
            return result('SUPPORTED_ILLEGAL', 'SOURCE_ZONE', 'Printed attack preview requires the actor\'s Active Oddish.')
        opponent = next(p for p in state.players if p != action.actor)
        targets = tuple(c.id for c in state.instances if c.location.zone == 'active' and c.location.player == opponent
                        and c.owner == opponent and c.controller == opponent)
        if not targets:
            return result('INSUFFICIENT_INFORMATION', 'TARGET_REQUIRED', 'An opposing Active Pokemon is required.',
                          missing_information=('opposing-active',))
        if action.target is None:
            return result('NEEDS_CHOICE', 'CHOOSE_ACTIVE', 'Specify the opposing Active instance.', legal_targets=targets,
                          required_choices=('target',))
        if action.target not in targets:
            return result('SUPPORTED_ILLEGAL', 'TARGET', 'Target must be the opposing Active Pokemon.', legal_targets=targets)
        attack = resolved[source.id]['attacks'][0]
        return result('INSUFFICIENT_INFORMATION', 'PREVIEW_ONLY', 'Printed damage is known; full attack execution is not established.',
            legal_targets=targets, preview=DamagePreview(attack=attack['name'], printed_damage=attack['damage'],
                printed_energy_cost=tuple(attack['cost']), target=action.target),
            missing_information=('energy-payment', 'attack-permission'),
            unsupported_dependencies=('weakness-resistance', 'damage-modifiers-prevention', 'attack-resolution-knockouts-prizes'))
    return result('UNSUPPORTED', 'HANDLER', 'No handler is implemented.')


def apply(action: Action, state: Scenario, cards: CardProvider, *, evaluated: Evaluation,
          registry: Registry | None = None) -> ApplyResult:
    """Re-evaluate and compare the receipt; never trust externally supplied deltas."""
    current = evaluate(action, state, cards, registry)
    if current.status != 'SUPPORTED_LEGAL' or current.delta is None:
        return ApplyResult(applied=False, evaluation=current, state=state)
    if current != evaluated:
        rejected = current.model_copy(update=dict(status='INSUFFICIENT_INFORMATION', delta=None,
            checks=(Check(code='EVALUATION_MISMATCH', message='Evaluation receipt changed; evaluate this exact action and state again.'),),
            missing_information=('matching-evaluation-receipt',)))
        return ApplyResult(applied=False, evaluation=rejected, state=state)
    destinations = {move.instance: move.after for move in current.delta.moves}
    changed = state.model_dump()
    changed['revision'] = current.delta.next_revision
    changed['usage'] = tuple(u.model_dump() for u in (*state.usage, *current.delta.usage_added))
    changed['instances'] = tuple(c.model_copy(update={'location': destinations[c.id]}).model_dump()
                                if c.id in destinations else c.model_dump() for c in state.instances)
    return ApplyResult(applied=True, evaluation=current, state=Scenario.model_validate(changed))
