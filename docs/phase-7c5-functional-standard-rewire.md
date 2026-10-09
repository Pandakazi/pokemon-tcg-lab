# Phase 7C.5 functional identity and Standard legality rewire

Base: `f6e916462934ee3fd9a6403f2a19a0e20639ea70` on `phase7c5-concrete-deck-resolution`.

## Architecture and confirmed causes

Previously, Collection/Deck Builder used legacy exact-text functional hashes (plus curated Basic Energy keys). DeckProvider inferred legality from raw member flags; Agent resolution recomputed whitespace-equivalence groups on each request. Alternate text formatting split groups, printing hints could determine resolution too early, and canonical display selection did not prefer ordinary base printings.

The rewire preserves all stored legacy hashes. It extends the card-cache ingestion/index layer with derived `gameplay_functions` and `gameplay_printings` tables. Printing rows map to normalized gameplay IDs and retain the exact legacy functional/Library hashes. Function rows store the signature, normalized name, derived Standard legality and canonical printing. Name/member indexes support lookup. No Collection, saved-deck, active-deck, default-printing or ownership migration is performed.

SQLiteCards initialization backfills a missing/version-stale derived index; each card/set ingestion updates affected groups transactionally. The existing desktop identity rebuild also refreshes it. An offline CLI supports explicit rebuild. The QA launcher prepares the index before starting the read-only API. Agent requests never initialize/rebuild it; a stale policy version requires preparation. Runtime catalogue reads reuse precomputed legacy hashes too.

## Gameplay identity

The existing functional signature supplies gameplay fields; the new index requests its whitespace-normalized form. Stored legacy callers continue using the unchanged default.

- Pokemon: name, category, suffix, HP, types, stage, evolves-from, complete represented Ability/attack fields including name/effect/cost/damage, weaknesses, resistances, retreat and rules.
- Trainers: name, category, Trainer subtype, effect/rules and any represented gameplay fields.
- Special Energy: name, category, Energy type, effects/rules and other represented gameplay fields.
- Basic Energy: the existing curated type identity, independent of art/name-prefix/printing.
- ACE SPEC/Radiant construction classes remain gameplay distinctions when represented by rarity. Other rarity/art/set/number/finish metadata is excluded.

Normalization collapses whitespace recursively, including repeated newlines. It does not rewrite wording, values, damage, costs or effects. Existing normalized-name behavior is reused. Cards lacking gameplay text retain a printing discriminator rather than being falsely merged.

## Standard policy

`standard_format.py` is the shipped authority: policy version `standard-2026-hij-v1`, H/I/J marks, curated Basic Energy, and an explicit exception hook. A known mark is authoritative even when the source flag is stale. Unmarked cards require existing affirmative source evidence; absent evidence stays unknown. Pocket is excluded. A function is legal if at least one member establishes legality, unknown if no member establishes it and some evidence is missing, otherwise illegal.

Sources: https://www.pokemon.com/us/pokemon-news/2026-pokemon-tcg-standard-format-rotation-announcement and https://community.pokemon.com/en-us/discussion/23170/letter-to-the-community-march-19-2026 . Public documentation was checked; no provider inference was used. Raw TCGdex/Library provenance is not rewritten. Rotation updates change the shipped policy/version and rebuild the derived index; no remote rotation service was introduced.

DeckProvider maps legacy deck identities through the index for legality. Thus historical exact allocations can represent a currently legal equivalent without changing the allocation or its saved identity. Generated reports use the indexed gameplay ID as the authoritative slot key and a separate canonical printing for display.

## Canonical selection and resolution

Selection order is legal member, non-promo, non-premium/base rarity, lowest ordinary collector number, then deterministic ID. Set counts identify above-base collector numbers when available. Promo set/rarity and full-art/illustration/secret/hyper/rainbow/shiny/Ultra-rare cues are excluded preferentially; special printings remain deterministic fallbacks.

Generated resolution first retrieves name-matching gameplay IDs, filters functional legality, then selects canonical display. An old, mismatched or missing provider printing cannot invalidate a unique legal name match. If multiple genuinely different legal identities remain, a valid same-name printing or an explicitly named attack/Ability in the supplied role can disambiguate. Otherwise ambiguity remains; no broad name-only merge or strategic inference is used.

Mechanical replacement begins only after functional resolution fails. Explicit active-deck cuts retain strict identity handling. Prompts, Agent conversation/state architecture, UI, evidence presentation and Limitless ingestion are unchanged. The Call Bell monotonic safeguard remains untouched.

## Live-cache inspection

Inspection ran on an isolated backup of the QA card cache; source/player databases were not changed.

Resolved with the new index:
- Ultra Ball: `me01-131`.
- Boss's Orders: `me01-114`.
- Dragapult ex: `sv08.5-073`.

No supported legal member under configured rules in that local snapshot:
Pidgey, Pidgeotto, Pidgeot ex, Professor's Research, Super Rod, Town Store, Natu, Xatu, Arven, Iono, Nest Ball, Technical Machine: Evolution, Defiance Band, Lumineon V, Lost Vacuum and Double Turbo Energy.

Those now report unavailable Standard legality rather than artwork ambiguity. This establishes lack of support in the inspected cache, not a claim that an uncached reprint cannot exist. Meaningfully different old wording is not automatically treated as an errata-equivalent card.

## Verification

- Focused Agent/index/resolver checks: 106 passed.
- Focused identity + Collection/Deck Builder compatibility: 66 passed.
- Focused ingestion/desktop/index checks: 60 passed.
- One final network-blocked backend gate: 476 passed, one obsolete synthetic A-mark/current-legal fixture assertion failed (112.30 seconds). Corrected that fixture to H, then reran only the affected context module: 26 passed. No production changes followed the gate and no broad gate was repeated. The gate included all 45 Collection/Deck Builder/allocation tests, which passed.
- git diff --check passed; two existing dependency deprecation warnings only.
- QA launcher PowerShell syntax check passed.
- No frontend changes/tests, no live model calls, no runtime restart.

Older synthetic deck tests were updated from contradictory A-mark/true-source-flag fixtures to explicit current H and historical G equivalents. Unknown-evidence fixtures omit the mark. The previous Ultra Ball test still proves formatting grouping and bad-ID recovery; its canonical fixture now supplies a base collector number. Its old-hint expectation now preserves meaningful legal ambiguity instead of allowing an obsolete printing to override functional-first intent.

## PM runtime preparation and limits

The normal QA restart command prepares/backfills the index offline automatically:

```powershell
Set-Location 'C:\Users\Mike\Documents\Codex\2026-09-25\referenced-chatgpt-conversation-this-is-an\work\phase5'
.\scripts\Start-Phase5-QA.ps1 -Action Restart -PhaseLabel 'Phase 7C.5'
```

For another runtime using this checkout, prepare its card cache before starting its read-only API:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
& 'C:\Users\Mike\Documents\pokemon-tcg-lab\.venv\Scripts\python.exe' -m pokelab.functional_index --db 'C:\Users\Mike\Documents\pokemon-tcg-lab\data\cards.sqlite3'
```

Preparation writes derived card-cache mappings only. It does not rewrite card source JSON, exact printing IDs, player ownership, revisions or saved allocations. Direct SQL mutations bypassing supported ingestion require an explicit offline rebuild. Canonical ranking is deterministic over available metadata; missing/incorrect source fields can still require review. No semantic errata equivalence or universal rules parser was added. Complete deck generation still depends on valid model choices and adequate cached legal cards.

Separate PM cleanup backlog: raw inline `[fact_ids: "active-deck"]` metadata leak; intentionally not changed here.

No merge, tag, certification or Phase 7D work.
