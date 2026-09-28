"""Bounded product-answer guards. No provider output or exception prose retained.

These checks reject known unsupported assertion forms; they are not a universal
natural-language entailment verifier. Only supplied/cited evidence is inspected.
"""
import json
import re


def fields(values):
    return {f['field']: json.loads(f['value']) for f in values}


def records(envelope):
    evidence = {}
    for item in envelope.packet.evidence:
        value = item.model_dump(mode='json')
        payload = value.get('payload', {})
        if 'fields' in value:
            payload = fields(value['fields'])
        printed = fields(payload.get('printed', []))
        evidence[item.id] = dict(name=payload.get('name'), attacks=printed.get('attacks', []),
            kind=value.get('kind', payload.get('kind')), data=payload)
    active = envelope.active_deck
    if hasattr(active, 'model_dump'): active = active.model_dump(mode='json')
    evidence['active-deck'] = dict(entries=[dict(name=e.get('name'),
        attacks=fields(e.get('printed', [])).get('attacks', [])) for e in active.get('entries', [])])
    return evidence


NUMBER = r'(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten)'
COST = re.compile(r'\b(?:for|costs?|requires?|needs?)\s+(?:only\s+)?('+NUMBER+r')\s+(?:[a-z]+\s+)?energ(?:y|ies)\b', re.I)
WORDS = dict(zip('zero one two three four five six seven eight nine ten'.split(), range(11)))
DEVIATIONS = ('UNCOMMON_PRESENT','COMMON_ABSENT','ABOVE_TYPICAL_QUANTITY','BELOW_TYPICAL_QUANTITY')


def violation(answer, envelope):
    source = records(envelope)
    names = {r.get('name') for r in source.values() if r.get('name')}
    names.update(e['name'] for e in source['active-deck']['entries'] if e.get('name'))
    # Direct deck assertions (including absence) and assertions about named cards
    # belong in cited claim arrays. Do not treat a negated fact as uncertainty.
    subject = r'(?:(?:(?:the|this|active|your)\s+)*deck|'+ '|'.join(re.escape(n) for n in sorted(names))+r')'
    assertion = re.compile(r'\b'+subject+r'\s+(?:(?:does|do)\s+not\s+)?(?:contains?|includes?|runs?|plays?|has|have|lacks?|omits?|uses?|deals?|prevents?|is built around)\b', re.I)
    for text in answer.limitations:
        # Declaring a premise contradicted by deck contents asserts a factual
        # comparison; it is not merely an uncertainty/scope boundary.
        if re.search(r'\b(?:premise|assumption)\b[^.!?;]{0,240}\bthat contradicts (?:the )?(?:supplied |active )?deck (?:composition|contents)\b',text,re.I):
            return 'uncited_limitation_claim'
        for match in assertion.finditer(text):
            prefix = re.split(r'[.;!?]', text[:match.start()])[-1]
            # An explicitly uncertain embedded proposition is not an assertion.
            if re.fullmatch(r'\s*(?:we |I )?(?:cannot|can\x27t) (?:establish|determine|verify) (?:whether|if)\s*',prefix,re.I):
                continue
            return 'uncited_limitation_claim'
    summaries = [r['data'] for r in source.values() if r.get('kind')=='deviation-summary']
    zero = any(s.get('available') is True and all(s.get('counts',{}).get(k)==0 for k in DEVIATIONS) for s in summaries)
    attacks = [attack for item in source.values() for entry in (item.get('entries') or [item])
        for attack in entry.get('attacks', []) if isinstance(attack,dict) and attack.get('name')]
    for statement in (*answer.facts, *answer.interpretation):
        cited = [entry for ref in statement.evidence for entry in
            (source[ref].get('entries') or [source[ref]])]
        for clause in re.split(r'(?<=[.!?;])\s+|\s+(?:but|however)\s+',statement.text):
            if zero and re.search(r'\b(?:differs from|stands out|is unusual|(?:key|main) difference|difference is|decks are (?:literally )?identical)\b',clause,re.I) and not re.search(r'\b(?:no|not|cannot)\b',clause,re.I):
                return 'unsupported_comparison_difference'
            for attack in attacks:
                if attack['name'].casefold() not in clause.casefold(): continue
                # Only direct cost forms, not arbitrary energy counts in effects.
                claims = COST.findall(clause)
                if re.search(r'\b(?:is free|zero-cost|requires no energy|costs no energy)\b',clause,re.I): claims.append('zero')
                supported = [a for entry in cited for a in entry.get('attacks', [])
                    if isinstance(a,dict) and a.get('name')==attack['name'] and isinstance(a.get('cost'),list)]
                for claim in claims:
                    number = int(claim) if claim.isdigit() else WORDS[claim.lower()]
                    if not supported or any(len(a['cost'])!=number for a in supported):
                        return 'unsupported_attack_cost'
    return None
