"""Bounded reviewed local interpretations; no discovery, NLP, ingestion or AI."""
from types import MappingProxyType
from sqlite3 import Error as SQLiteError
import json

from tcg_lab.cards import CardLookupError, CardProvider
from pokelab.engine import functional_signature
from pokelab.collection import identity
from .models import Evidence, MechanicProfile, ProfileRef, ProfileResolution, Ruleset, digest

RULESET = Ruleset(id='international-en-physical', version='2026-09-25.ab1')
SWITCH = ProfileRef(id='switch.active-bench', version='1')
ODDISH = ProfileRef(id='oddish.seed-bomb.printed', version='1')
ULTRA_BALL = ProfileRef(id='ultra-ball.cost-search', version='1')
GUMSHOOS = ProfileRef(id='gumshoos.evidence-gathering', version='1')
HANDLER_VERSIONS = MappingProxyType({'switch-effect': '1', 'printed-damage': '1',
                                   'ultra-ball': '1', 'evidence-gathering': '1'})

# Presentation/source bookkeeping cannot affect gameplay. Unknown new fields ARE
# included: source evolution fails closed instead of silently hiding new mechanics.
NON_MECHANICS = frozenset(('set', 'localId', 'image', 'illustrator', 'variants',
    'variants_detailed', 'pricing', 'thirdParty', 'updated', 'dexId', 'cameoDexIds',
    'description', 'boosters'))


def source_fingerprint(card):
    return digest({key: value for key, value in card.items() if key not in NON_MECHANICS})


def reviewed_sources():
    """Detached source excerpts from the September 23 local cache, not live fetches."""
    return {
        'me01-131': dict(id='me01-131', name='Ultra Ball', category='Trainer', rarity='Common',
            trainerType='Item', effect='You can use this card only if you discard 2 other cards from your hand.\n\nSearch your deck for a Pokémon, reveal it, and put it into your hand. Then, shuffle your deck.',
            regulationMark='I', legal={'standard': True, 'expanded': True}),
        'me01-110': dict(id='me01-110', name='Gumshoos', category='Pokemon', rarity='Uncommon',
            hp=100, types=['Colorless'], evolveFrom='Yungoos', stage='Stage1',
            abilities=[dict(type='Ability', name='Evidence Gathering', effect='Once during your turn, you may use this Ability. Switch a card from your hand with the top card of your deck.')],
            attacks=[dict(cost=['Colorless', 'Colorless'], name='Bite', damage=50)],
            weaknesses=[dict(type='Fighting', value='×2')], retreat=1, regulationMark='I',
            legal={'standard': True, 'expanded': True}),
        'me01-130': dict(id='me01-130', name='Switch', category='Trainer', rarity='Common',
            trainerType='Item', effect='Switch your Active Pokémon with 1 of your Benched Pokémon.',
            regulationMark='I', legal={'standard': True, 'expanded': True}),
        'me02-001': dict(id='me02-001', name='Oddish', category='Pokemon', rarity='Common',
            hp=50, types=['Grass'], stage='Basic', attacks=[dict(cost=['Grass'], name='Seed Bomb', damage=20)],
            weaknesses=[dict(type='Fire', value='×2')], retreat=1, regulationMark='I',
            legal={'standard': True, 'expanded': True}),
    }


def evidence(key, kind, reference, field_path, content, retrieved_at=None):
    return Evidence(id=key, kind=kind, reference=reference, field_path=field_path,
        content=content, content_hash=digest(content), retrieved_at=retrieved_at,
        applicability='International English physical TCG; isolated foundation proof only. No official effective-date claim.')


def builtin_profiles():
    cards = reviewed_sources()
    specs = (
        (SWITCH, 'me01-130', 'switch-effect', 'switch-effect-only', '/effect', cards['me01-130']['effect'],
         '2026-09-23T02:38:21.490445+00:00',
         'Resolve only the already-authorized Switch effect: exchange the acting player\'s Active Pokémon and one chosen own Benched Pokémon. Require explicit isolated context; do not play/discard the Item or claim general play legality.'),
        (ODDISH, 'me02-001', 'printed-damage', 'printed-damage-preview', '/attacks/0',
         json.dumps(cards['me02-001']['attacks'][0], sort_keys=True, ensure_ascii=False, separators=(',', ':')),
         '2026-09-23T02:34:38.299080+00:00',
         'Report only Seed Bomb\'s printed base damage 20 and cost [Grass] from an own Active Oddish toward the opposing Active. No attack execution or Energy-payment claim.'),
        (ULTRA_BALL, 'me01-131', 'ultra-ball', 'ultra-ball-effect-only', '/effect', cards['me01-131']['effect'],
         None,
         'Already-authorized isolated effect only. Pay exactly two distinct other own hand cards as cost, select one own deck Pokémon, reveal only that result, move it to hand, then use a trusted explicit permutation of the remaining deck. No general Item legality or no-result search rule is established.'),
        (GUMSHOOS, 'me01-110', 'evidence-gathering', 'evidence-gathering-only', '/abilities/0',
         json.dumps(cards['me01-110']['abilities'][0], sort_keys=True, ensure_ascii=False, separators=(',', ':')),
         None,
         'Already-authorized isolated Evidence Gathering only. This Ability means the source instance, not a player-wide or all-Gumshoos restriction. Once per externally identified own turn, exchange one chosen own hand card with the top own deck card privately. No general Ability timing or leave/re-enter reset is established.'),
    )
    output = []
    for ref, printing, handler, scope, path, text, retrieved, interpretation in specs:
        output.append(MechanicProfile(ref=ref, ruleset=RULESET, printing_id=printing,
            functional_id=identity(functional_signature(cards[printing])),
            source_fingerprint=source_fingerprint(cards[printing]), handler=handler, handler_version='1',
            review_status='REVIEWED', reviewed_by='Codex engineering review against pinned local source excerpts',
            review_note='Narrow deterministic interpretation reviewed in this implementation. Not an official ruling or PM certification.',
            evidence=(evidence(ref.id+'.text', 'CARD_TEXT', 'https://api.tcgdex.net/v2/en/cards/'+printing, path, text, retrieved),
                      evidence(ref.id+'.interpretation', 'POKELAB_INTERPRETATION', 'pokelab/rules/registry.py', ref.id, interpretation)),
            scope=scope, limitations=('Isolated scenario only; not full gameplay legality.',
                'No official rulebook/ruling corpus is bundled. Missing global interactions are not inferred.',
                'No source card play/discard, attachments, conditions, modifiers, knockouts or prizes are executed.')))
    return tuple(output)


class Registry:
    def __init__(self, profiles=None):
        profiles = builtin_profiles() if profiles is None else tuple(profiles)
        index = {(p.ref.id, p.ref.version): p for p in profiles}
        if len(index) != len(profiles):
            raise ValueError('Duplicate profile/version.')
        self.profiles = MappingProxyType(index)

    def resolve(self, ref: ProfileRef, cards: CardProvider, ruleset=RULESET):
        profile = self.profiles.get((ref.id, ref.version))
        def result(support, reason, actual=None):
            return ProfileResolution(support=support, profile=profile, reason=reason, actual_fingerprint=actual)
        if profile is None:
            return result('UNKNOWN', 'No reviewed profile for this exact ID/version.')
        if ruleset != RULESET or profile.ruleset != RULESET or HANDLER_VERSIONS.get(profile.handler) != profile.handler_version:
            return result('VERSION_MISMATCH', 'Ruleset or handler version is not implemented.')
        if profile.review_status != 'REVIEWED':
            return result(profile.review_status, 'Interpretation is not currently reviewed.')
        if not profile.reviewed_by or not profile.review_note:
            return result('UNREVIEWED', 'Review metadata is missing.')
        if (not {'CARD_TEXT', 'POKELAB_INTERPRETATION'}.issubset({e.kind for e in profile.evidence})
            or any(digest(e.content) != e.content_hash for e in profile.evidence)):
            return result('MISSING_EVIDENCE', 'Required evidence is absent or its content hash is invalid.')
        try:
            card = cards.get(profile.printing_id)['card']
            actual = source_fingerprint(card)
            fid = identity(functional_signature(card))
        except (CardLookupError, KeyError, TypeError, ValueError, OSError, SQLiteError):
            return result('MISSING_EVIDENCE', 'Current source card is unavailable or incomplete.')
        if actual != profile.source_fingerprint or fid != profile.functional_id:
            return result('STALE', 'Source mechanics changed; interpretation must be reviewed again.', actual)
        return result('REVIEWED', 'Reviewed interpretation matches the pinned source and versions.', actual)
