# Post-Phase-5 correction: Variation Family discovery

Phase 5 is PM certified. This correction **passed PM QA** and is accepted in the
September 25, 2026 certification closeout. It changes collectible discovery,
not its certified deck architecture, legality, allocations or collection identities.
No schema migration, source synchronization, deck rewrite, UI redesign or AI matching.

## Observed local source evidence

Inspected the synchronized TCGdex SQLite `cards`, `sets` and `metadata` tables on
2026-09-25. The cache contains 23,736 records. Reviewed the complete top-level field
inventory and `variants_detailed` fields; no explicit playable/reprint family ID
or relationship is present. `variantId` is a finish-configuration identifier reused
across unrelated cards (for example ordinary holo), not playable identity evidence.
Third-party product IDs, artwork, cameo Dex IDs, set IDs and rarity are collectible
metadata, not an equivalence link.

Reviewed name, category, HP, types, stage, evolution, suffix, attacks (name, costs,
damage, effects), abilities, weaknesses, resistances, retreat, Trainer subtype,
Energy type, effect text, held-item data, regulation marks, legality, set/card IDs,
set series/game classification and exact finish flags. The source inventory has no
top-level `rules` field in this snapshot; the service nevertheless preserves it if
present. `item` occurs on eight historical Pokémon records and is retained as
gameplay evidence.

The canonical functional signature already excludes set, art, rarity and regulation
mark, but compares most gameplay fields literally. Ordinary Variations previously
used these canonical groups. Builder used the same groups except curated Basic
Energy type grouping. Library representative selection has its separate certified
scope and remains untouched.

### Mega Charizard X ex — actual exclusion cause

`me02-013`, `me02-109` and `me02-125` have identical gameplay fields and the same
canonical ID, `8f73c57bcc5f245039ff512d2ac2eb5a`.

Gold `me02-130` adds `suffix: "ex"`, absent on the other three, and encodes Water
weakness as `"x2"` instead of `"×2"`. Its HP 360, Fire type, Stage2, Charmeleon
evolution, Inferno X attack, cost, damage, effect and retreat 2 are otherwise equal.
These two literal metadata differences create canonical ID
`e6d72de63463f3f06525bc58b2051b78`, excluding it from the old discovery group.

Promos `mep-023` and `mep-029` also use `suffix: "ex"`/`x2`, and use `[R]` rather
than `{R}` in the otherwise identical effect. Those are the same energy-token
notation with different delimiters. Their separate canonical ID is retained.
All six cached printings now share one **discovery family**. The two promo records
lack image URLs; the existing honest image-unavailable fallback remains.

### Boss's Orders — actual historical split

Six current/SV-era printings (`me01-114`, `me02.5-183`, `me02.5-256`, `sv02-172`,
`sv02-248`, `sv02-265`) are Supporters with this effect:

> Switch in 1 of your opponent's Benched Pokémon to the Active Spot.

Three older printings (`swsh9-132`, `swsh11tg-TG24`, `swshp-SWSH251`) are Supporters
with this effect:

> Switch 1 of your opponent's Benched Pokémon with their Active Pokémon.

The service contains a narrowly documented alias for **only these two entire effect
strings**, gated by normalized name `boss's orders` and subtype `Supporter`. Both
describe choosing one opposing Benched Pokémon and switching it into the Active
position. Other gameplay fields/rules still must match. This is not a generic
wording paraphrase engine or a name-only exception. Added clauses, another effect,
another name, another Trainer subtype or ACE SPEC restriction do not match.

All nine cached printings are discoverable together. Source Standard flags remain
false on the historical SV/SWSH examples and true on current ME examples. The
family query never filters by Standard legality and never changes legality.

### Collision and Energy evidence

Real Charizard examples remain separate: `base1-4` (120 HP, Energy Burn/Fire Spin),
`swsh4-25` (170 HP, Battle Sense/Royal Blaze), `swsh10.5-010` (170 HP, Burn Brightly/
Flare Blitz), and Pocket `A1-035` (150 HP, different Fire Spin). Sharing name or set
never overrides gameplay differences. Pocket and physical TCG records never join.

`base1-101` Psychic Energy and `sv03.5-207` Basic Psychic Energy retain the existing
curated Psychic type grouping; Fire `base1-98` stays separate. Special Energy
`swsh9-151` and `swsh10-216` Double Turbo Energy retain their exact canonical
functional relationship. Special and ambiguous Energy receive no broadened rules.

## Deterministic rule

`pokelab.variation_families` is a pure read-only service over a collection snapshot.
Normalized name is only a candidate filter. There is no fuzzy matching, model call,
network request or source/database update.

1. Include game classification in every family key. Unknown games remain singleton.
2. Reuse the certified curated Basic Energy recognition/type key, scoped to game.
3. For other Energy, reuse the canonical functional signature exactly.
4. For Pokémon and Trainers, retain the existing gameplay signature fields and
   held-item data. Normalize Unicode NFKC, curly apostrophes and whitespace, plus
   observed `{energy symbol}` / `[energy symbol]` delimiters. Keep list order,
   case-sensitive gameplay text and numeric types; do not erase clauses.
5. Pokémon require HP, types, stage, retreat and evolution source when non-Basic,
   plus existing rules evidence. Invalid structured lists or incomplete
   attacks/abilities are conservative singletons. Only infer a missing lowercase
   `ex` suffix when the full source name explicitly ends in lowercase ` ex`;
   never remove conflicting suffixes or equate uppercase EX with lowercase ex.
   Normalize `x`/`×` only in full numeric damage/weakness/resistance multiplier
   expressions. Preserve HP, attacks, costs, abilities, stage, evolution, types,
   retreat, weaknesses, resistances, rule text and other canonical gameplay fields.
6. Trainers require subtype and nonempty effect text. Apply only the exact Boss's
   Orders alias above, and retain any ACE SPEC rarity-based restriction.
7. Compare the resulting complete signatures. No same-set override, name-only
   join, transitive wildcard matching, general wording inference or legality-based
   filtering is performed.

An audit of this cache found 185 Pokémon/Trainer discovery groups joining multiple
unchanged canonical IDs (167 Pokémon, 18 Trainers). The stated typography rules
apply deterministically to all candidates, rather than special-casing a card ID.
1,836 Pokémon and 245 Trainer records remain conservative singletons because the
required evidence is incomplete. These counts describe this cache, not future syncs.

## API and preservation boundary

Added opt-in `scope=family` to the existing variations endpoint. Card Detail and
Builder Variations request it. `scope=functional`, `scope=deck`, `scope=library`
and the legacy default behavior remain unchanged. The Phase 2 artwork chooser
continues requesting Library scope. Exact finishes, ownership payloads, paging,
inspection routes, source legality and the certified framed UI remain unchanged.

**A discovery family is not a replacement certified deck ID.** Every returned
printing keeps its original `deck_identity`, ownership functional ID and Library
ID. Existing active/saved JSON and defaults are not rewritten. Explicit exact
additions still remember a default under that printing's certified deck key;
implicit additions use it within that key. This correction does not bridge defaults,
merge functional deck totals or confer legality across previously distinct canonical
IDs merely because their artwork is now discoverable together. In particular,
Mega gold/regular and the two Boss wording groups remain distinct deck keys.
The inherited name-based copy-limit validator remains authoritative across those
keys. Changing that certified identity boundary requires a separate explicit task.

## Conservative exclusions

- Only locally synchronized records can be discovered; this does not fetch missing
  historical sets or promise a complete historical catalogue.
- Missing stage/evolution/retreat, unknown game, missing Trainer text/subtype,
  malformed attacks/abilities, meaningful wording differences and conflicting
  rules stay separate. Numeric string versus integer damage stays separate.
- Historical Charizard wording/Ability-type differences are not automatically
  declared equivalent. Boss's Orders is the sole curated wording alias.
- Supported Normal/Holo/Reverse and existing finish keys remain distinct. Foil,
  stamps and detailed source variant IDs do not invent new allocation/ownership
  dimensions. Presentation of known finishes is handled separately by the accepted
  [finish renderer](finish-visualization.md).

## Files and verification

- `src/pokelab/variation_families.py`: matching service.
- `src/pokelab/api.py`: family query scope.
- `web/src/Variations.tsx`, `api.ts`: scope selection/type only; no UI redesign.
- `tests/fixtures/variation-families.json`: 24 frozen real records and 14 set
  metadata records; pricing and unrelated set catalogue listings omitted.
- `tests/test_variation_families.py`: bidirectional Mega/Boss membership, real and
  mutated collisions, exact wording guard, Basic/Special Energy, exact finishes,
  game separation, source legality, paging and byte-preservation checks.
- `web/integration/variation-families.spec.ts`: real family discovery, gold exact
  addition/preference, preserved earlier allocation, ownership, settled frame,
  whitespace hover and historical inspection.

Targeted first: 25 new Python cases passed. Affected API/collection/deck boundary
run: 104 passed. Frontend deck component checks: 6 passed. TypeScript and production
build passed. Browser results and runtime commit are recorded in the QA handoff.
Those were focused implementation checks, not a new full-suite run. PM subsequently
accepted this correction; it is preserved with Phase 5. No Phase 6 work is included.
