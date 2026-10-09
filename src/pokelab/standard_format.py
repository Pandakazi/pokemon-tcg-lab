"""Shipped Standard policy; update this module and rebuild the card index at rotation."""
VERSION = 'standard-2026-hij-v1'
REGULATION_MARKS = frozenset(('H', 'I', 'J'))
SOURCE = 'https://www.pokemon.com/us/pokemon-news/2026-pokemon-tcg-standard-format-rotation-announcement'
# Explicit exceptions belong here, not in prompts or provider adapters.
BANNED_NAMES = frozenset()


def printing_legal(card, game, *, basic=False):
    if game == 'pocket' or card['name'].casefold() in BANNED_NAMES:return False
    if basic:return True
    mark=card.get('regulationMark')
    if mark:return mark in REGULATION_MARKS
    # Unmarked legacy/data-incomplete records need affirmative source evidence.
    # A source flag cannot override a known rotated regulation mark.
    return card.get('legal',{}).get('standard')
