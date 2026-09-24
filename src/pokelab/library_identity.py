"""Presentation-only grouping; never replaces canonical functional identity."""
from .engine import functional_signature, normalized_name

BASIC_TYPES = ('Grass', 'Fire', 'Water', 'Lightning', 'Psychic', 'Fighting', 'Darkness', 'Metal', 'Fairy')
BASIC_NAMES = {normalized_name(prefix + kind + ' Energy'): kind
               for kind in BASIC_TYPES for prefix in ('', 'Basic ')}


def library_signature(card):
    # Source Normal also occurs on named Special Energy. Only curated Basic names
    # may collapse; never infer a type from arbitrary effects or name substrings.
    if card.get('category') == 'Energy' and card.get('energyType') == 'Normal':
        kind = BASIC_NAMES.get(normalized_name(card['name']))
        types = card.get('types')
        if kind and (not types or types == [kind]):
            return 'library-basic-energy:' + kind
    return functional_signature(card)
