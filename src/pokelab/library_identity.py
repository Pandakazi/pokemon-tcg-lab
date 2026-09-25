"""Presentation-only grouping; never replaces canonical functional identity."""
from .engine import functional_signature, normalized_name
from .images import TCGdexImages

# Shared by Library representatives and read-only competitive artwork previews.
# c/s are the cards/sets aliases. Keep Library's certified ordering unchanged.
REPRESENTATIVE_ORDER_SQL = """basic_image_priority(c.raw) DESC,
    COALESCE(json_extract(s.raw,'$.releaseDate'),'') DESC,
    COALESCE(c.regulation,'') DESC,c.id DESC"""

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


def basic_image_priority(card):
    """Prefer usable source image metadata only for curated Basic Energy.

    No remote probes while browsing. Eligibility is applied before ranking; a
    missing or unavailable remote asset still uses the normal UI fallback.
    """
    return int(library_signature(card).startswith('library-basic-energy:')
               and TCGdexImages().url(card) is not None)
