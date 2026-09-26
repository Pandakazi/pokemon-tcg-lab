"""Trusted host supplies scenarios; the question never establishes gameplay state."""
from .agent_context_models import FieldValue, Reference, RulesFacts
from .rules import Registry, evaluate
from .rules.registry import builtin_profiles

SAFE_DEPENDENCIES = frozenset(('energy-payment','attack-permission','weakness-resistance',
    'damage-modifiers-prevention','attack-resolution-knockouts-prizes','isolation-confirmation',
    'assessed-relevant-dependencies','turn-token','no-result-search-rule','matching-source-fingerprint',
    'private-zone-control','matching-usage-scope','attachment-modifier-stacking','knockout-state',
    'printed-hp','printed-retreat','host-damage-counters','attached-effects','current-state-action',
    'reviewed-matching-profile'))


def safe_dependencies(values):
    public=tuple(v for v in values if v in SAFE_DEPENDENCIES)
    return public + (('additional-private-or-unreviewed-dependency',) if any(v not in SAFE_DEPENDENCIES for v in values) else ())


def rules_view(cards, printing, trusted=None):
    profiles = [p for p in builtin_profiles() if p.printing_id == printing]
    if not profiles:
        return RulesFacts(profile=None, profile_version=None, handler_version=None, review_support='UNKNOWN',
            status='UNSUPPORTED', scope='unresolved', result_type='unavailable', unsupported=('reviewed-profile',)), ()
    profile = profiles[0]
    resolution = Registry().resolve(profile.ref, cards)
    refs = tuple(Reference(id=e.id, source=e.kind, resource=e.reference, content_hash=e.content_hash,
                          version=profile.ref.version, checked_at=e.retrieved_at, excerpt=e.content) for e in profile.evidence)
    base = dict(profile=profile.ref.id, profile_version=profile.ref.version, handler_version=profile.handler_version,
                review_support=resolution.support, scope=profile.scope, limitations=profile.limitations)
    if resolution.support != 'REVIEWED':
        return RulesFacts(**base, status='UNSUPPORTED', result_type='unavailable', unsupported=('matching-reviewed-source',)), refs
    if trusted is None:
        return RulesFacts(**base, status='INSUFFICIENT_INFORMATION', result_type='profile-only',
                          missing=('explicit-gameplay-scenario',)), refs
    # Host-only (action, scenario, prior evaluation, authenticated perspective).
    # Recompute before projecting. Neither this tuple nor receipt is put in context.
    action, state, receipt, perspective = trusted
    if perspective not in state.players or action.profile != profile.ref:
        raise ValueError('Invalid trusted rules context.')
    current = evaluate(action, state, cards)
    if current != receipt: raise ValueError('Stale or forged rules receipt.')
    if perspective != action.actor and current.derivation is None:
        return RulesFacts(**base, status='INSUFFICIENT_INFORMATION', result_type='unavailable',
                          missing=('private-pending-resolution',)), refs
    # Only in-play objects are eligible target references. Private cost/search choices
    # remain in their gameplay UI; do not send them to a future model.
    public = {c.id for c in state.instances if c.location.zone in ('active','bench','resolving','discard','attached')}
    preview, transition = (), ()
    result_type = 'unavailable'
    if current.preview:
        result_type = 'preview'
        preview = (FieldValue(field='printed_damage', value=str(current.preview.printed_damage)),
                   FieldValue(field='attack', value=current.preview.attack))
    if current.derivation:
        result_type = 'derivation'
        d = current.derivation
        preview = tuple(FieldValue(field=k, value=str(getattr(d,k))) for k in
                        ('base_printed_cost','remaining_hp','derived_cost'))
    if current.delta:
        result_type = 'scoped-transition-proposal'
        if current.scope == 'switch-effect-only':
            transition = tuple(f'{m.instance}: {m.before.zone} -> {m.after.zone}' for m in current.delta.moves if m.instance in public)
        else:
            transition = tuple(f'{s.phase}: {s.operation}' for s in current.delta.steps)
    return RulesFacts(**base, status=current.status, evaluated_support=current.support, result_type=result_type,
        checks=tuple(c.code for c in current.checks), required_choices=current.required_choices,
        permitted_targets=tuple(k for k in current.legal_targets if k in public), preview=preview, transition=transition,
        # Missing-information strings may themselves contain hidden instance IDs.
        missing=safe_dependencies(current.missing_information),
        unsupported=safe_dependencies(current.unsupported_dependencies)), refs
