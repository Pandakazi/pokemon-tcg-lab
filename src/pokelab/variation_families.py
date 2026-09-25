"""Read-only collectible discovery; never changes canonical/deck identity.

No name-only matching, legal-format filtering, fuzzy text matching or source writes.
See docs/variation-families.md for the observed source evidence and boundaries.
"""
import json
import re
import unicodedata

from .engine import functional_signature, normalized_name
from .library_identity import library_signature


def text(value):
    """Only typography/whitespace and observed energy-token delimiters."""
    value = unicodedata.normalize('NFKC', value).replace('\u2019', "'")
    value = re.sub(r'\{([GRWLPFDMNCY])\}', r'[\1]', value)
    return ' '.join(value.split())


def normalized(value):
    if isinstance(value, str): return text(value)
    if isinstance(value, list): return [normalized(v) for v in value]
    if isinstance(value, dict): return {k:normalized(v) for k,v in value.items()}
    return value


BOSS_EFFECTS = (
    "Switch in 1 of your opponent's Benched Pokémon to the Active Spot.",
    "Switch 1 of your opponent's Benched Pokémon with their Active Pokémon.",
)


def family_signature(record):
    card, game = record['card'], record['game']
    singleton = ('unresolved', game, card['id'])
    if game not in ('tcg', 'pocket'): return singleton
    basic = library_signature(card)
    if basic.startswith('library-basic-energy:'):
        return ('basic', game, basic)
    category = card.get('category')
    # Special/ambiguous Energy keeps the certified functional signature exactly.
    if category == 'Energy': return ('canonical-energy', game, functional_signature(card))
    identity = normalized(json.loads(functional_signature(card)))
    if 'unresolved_printing' in identity: return singleton
    # Held-item text is gameplay evidence on the few historical records carrying it.
    if 'item' in card: identity['item'] = normalized(card['item'])
    if category == 'Pokemon':
        if (type(card.get('hp')) is not int or not card.get('types')
            or not card.get('stage') or 'retreat' not in card
            or (card['stage'] != 'Basic' and not card.get('evolveFrom'))):
            return singleton
        for field in ('attacks', 'abilities', 'weaknesses', 'resistances'):
            if any(not isinstance(v, dict) for v in card.get(field, [])):
                return singleton
        if any(not a.get('name') or not isinstance(a.get('cost'), list) for a in card.get('attacks', [])):
            return singleton
        if any(not a.get('name') or not a.get('type') or not a.get('effect') for a in card.get('abilities', [])):
            return singleton
        # Only the observed lowercase ex suffix redundancy. Never discard a
        # conflicting suffix or conflate historical uppercase EX with lowercase ex.
        if card['name'].endswith(' ex') and card.get('suffix') in (None, 'ex'):
            identity['suffix'] = 'ex'
        for attack in identity.get('attacks', []):
            damage = attack.get('damage')
            if isinstance(damage, str) and re.fullmatch(r'\d+[x×]', damage):
                attack['damage'] = damage[:-1] + '×'
        for field in ('weaknesses', 'resistances'):
            for item in identity.get(field, []):
                value = item.get('value')
                if isinstance(value, str) and re.fullmatch(r'[x×]\d+', value):
                    item['value'] = '×' + value[1:]
    elif category == 'Trainer':
        if not card.get('trainerType') or not isinstance(card.get('effect'),str) or not card['effect'].strip(): return singleton
        # Exact, title + subtype gated wording pair seen in the local source.
        # Other effects/rules remain in the signature and cannot be inferred away.
        if (normalized_name(card['name']) == "boss's orders"
            and card['trainerType'] == 'Supporter' and identity['effect'] in BOSS_EFFECTS):
            identity['effect'] = BOSS_EFFECTS[0]
        if 'ACE SPEC' in card.get('rarity', '').upper():
            identity['deck_restriction'] = 'ACE SPEC'
    else:
        return singleton
    return ('variation-v1', game, json.dumps(identity,ensure_ascii=False,sort_keys=True,separators=(',', ':')))


def variation_members(snapshot, printing_id):
    """Name is only a candidate filter; full structured evidence decides membership."""
    anchor = snapshot.records[printing_id]
    key = family_signature(anchor)
    if key[0] == 'unresolved': return [printing_id]
    if key[0] == 'basic':
        candidates = snapshot.libraries[anchor['library_id']]
    elif key[0] == 'canonical-energy':
        candidates = snapshot.functions[anchor['functional_id']]
    else:
        name = normalized_name(anchor['card']['name'])
        candidates = [id for id,r in snapshot.records.items()
                      if r['game'] == anchor['game'] and normalized_name(r['card']['name']) == name]
    return [id for id in candidates if family_signature(snapshot.records[id]) == key]
