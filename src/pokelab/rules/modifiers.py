"""One reviewed, persistent single-modifier derivation; no transition engine."""
from .models import Choices, PersistentModifier, RetreatDerivation
from .registry import source_fingerprint


def derive_retreat_cost(action, state, source, profile, records, result):
    if action.choices != Choices() or action.target is not None:
        return result('SUPPORTED_ILLEGAL', 'EXTRA_SELECTION', 'The affected object is the attachment host; no choices are accepted.')
    if source.attached_to is None or source.location.zone != 'attached':
        return result('SUPPORTED_ILLEGAL', 'ATTACHMENT_REQUIRED', 'An existing attachment is required, not an attachment action.')
    host = next(c for c in state.instances if c.id == source.attached_to)
    attachments = tuple(c for c in state.instances if c.attached_to == host.id)
    if len(attachments) != 1:
        return result('UNSUPPORTED', 'MULTIPLE_ATTACHMENTS', 'Multiple attachments require unreviewed relevance/stacking rules.',
                      unsupported_dependencies=('attachment-modifier-stacking',))
    source_card = records[source.id]
    if source_card.get('category') != 'Trainer' or source_card.get('trainerType') != 'Tool':
        return result('UNSUPPORTED', 'TOOL_CLASSIFICATION', 'Reviewed Trainer/Tool classification is required.')
    card = records[host.id]
    hp, base = card.get('hp'), card.get('retreat')
    if type(hp) is not int or hp <= 0 or type(base) is not int or base < 0 or host.damage_counters is None:
        return result('INSUFFICIENT_INFORMATION', 'HOST_INPUTS', 'Known positive printed HP, nonnegative printed retreat and damage counters are required.',
                      missing_information=('printed-hp', 'printed-retreat', 'host-damage-counters'))
    remaining = hp - host.damage_counters * 10
    if remaining <= 0:
        return result('UNSUPPORTED', 'KNOCKOUT_BOUNDARY', 'A host with no remaining HP needs unimplemented knockout handling.',
                      unsupported_dependencies=('knockout-state',))
    condition = remaining <= 30
    modifier = PersistentModifier(source=source.id, profile=profile.ref, affected=host.id, value='retreat-cost',
        condition='remaining-hp-at-most', threshold=30, condition_satisfied=condition,
        operation='set-zero' if condition else 'subtract-floor-zero', amount=0 if condition else 1,
        evidence=profile.evidence)
    derived = 0 if condition else max(0, base - modifier.amount)
    return result('SUPPORTED_LEGAL', 'DERIVED_VALUE_ONLY',
        'Only the isolated derived value is supported; this does not authorize retreat.',
        derivation=RetreatDerivation(host=host.id, host_printing=host.printing_id,
            host_fingerprint=source_fingerprint(card), base_printed_cost=base, printed_hp=hp,
            damage_counters=host.damage_counters, remaining_hp=remaining, modifier=modifier, derived_cost=derived))
