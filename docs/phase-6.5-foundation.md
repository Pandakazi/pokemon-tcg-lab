# Phase 6.5A/B — isolated rules/mechanics foundation

Implementation for PM review, not merged, tagged or certified. Baseline:
`645bc3b3188995a9cbc51c20e17738413ddd99ca`. Branch: `phase6.5-rules-foundation`.
Only Pass A + Pass B. No Pass C, UI, public API, Agent or battle engine.

## Actual architecture

`pokelab.rules.models` contains frozen, extra-forbidden Pydantic contracts.
`registry` holds two reviewed profiles, evidence excerpts and source fingerprints.
`evaluate` provides pure `evaluate` and `apply` functions over caller-owned scenarios.
Existing CardProvider lookup, functional_signature and identity hashing are reused
without changing any certified identity, deck validation or persistence behavior.

The only executable transition is **resolution of an already-authorized isolated
Switch effect**. The caller places Switch in `resolving`; this package does not
authorize playing an Item, pay costs, discard it, clear Special Conditions, process
attachments or execute triggers. An explicit isolation declaration and assessed
empty dependency list are required. These are scenario assumptions, not an automatic
proof that arbitrary real games contain no interfering effects. If the caller cannot
establish that boundary, it must not declare it. Full Switch play is unsupported.

Oddish is a **printed base-damage preview**, not an executable attack or applied
damage. Preview returns 20 and cost `[Grass]`; result remains
INSUFFICIENT_INFORMATION, with no delta and explicit unimplemented dependencies.

## Contracts and authority

Results: SUPPORTED_LEGAL, SUPPORTED_ILLEGAL, NEEDS_CHOICE,
INSUFFICIENT_INFORMATION, UNSUPPORTED. `scope` is mandatory; a supported scoped
result is never an unconditional full-game legality statement. Results carry the
action, state revision/hash, ruleset, profile/handler versions, checks, choices,
missing information, dependencies, provenance, limitations and optional delta/preview.

Profile support is separately REVIEWED, UNKNOWN, UNREVIEWED, STALE,
MISSING_EVIDENCE or VERSION_MISMATCH. Missing profiles/versions, review metadata,
evidence, changed content or unsupported versions fail closed. Unmodelled scenario
dependencies produce UNSUPPORTED; unassessed dependencies produce insufficient information.

Scope is pinned to `international-en-physical` / `2026-09-25.ab1`, English physical
TCG, international, isolated interactions. This is an implementation scope/version,
**not an invented official rulebook edition or effective date**. Only this pin is
implemented. Historical/future versions are rejected. No tournament format legality
or official-current-rulebook completeness claim is made.

Evidence types distinguish CARD_TEXT, OFFICIAL_GAME_RULE, OFFICIAL_CARD_RULING,
ERRATA and POKELAB_INTERPRETATION. Only CARD_TEXT and POKELAB_INTERPRETATION are
needed/bundled for these bounded proofs. Records include reference URL/path, field,
content hash, applicability, retrieval metadata and optional publication/effective
dates. Unknown dates remain null; cache checked_at is not an effective date.

The two interpretations were engineering-reviewed against pinned local source
excerpts and their narrow handler behavior in this implementation; review metadata
states that explicitly. This is not an official ruling or Mike's certification.
Profiles are trusted version-controlled code, not user-submittable declarations.

## Fingerprints

`mechanics-v1` hashes sorted canonical JSON of source fields, excluding an explicit
list of presentation/bookkeeping fields (images, sets, pricing, variants, illustration,
source update timestamp, Pokédex/flavor metadata). Unknown new fields remain included.
Rarity, regulation, legality flags, attacks, effects and rules are included. This is
deliberately stricter than functional identity; even a legality-flag change requires
review. The original functional ID algorithm remains unchanged.

Both the source fingerprint and existing functional ID must match. Evidence text
hashes must match and both required authority kinds must be present. Expected
fingerprints are derived from version-controlled reviewed source excerpts, never
from whatever the live cache currently says. A provider refresh between resolution
and evaluation is checked again. Unsupported target-instance data cannot be ignored.

## Minimal state and application

Schema 1 has exactly two players, turn owner, revision, ruleset, unique instances,
owner/controller references, functional/source/profile references and locations.
Zones are Active, Bench, resolving, hand and discard with positions. A position
bound is an input safety limit, not an official Bench-capacity rule. Duplicate IDs,
duplicate slots, invalid Active positions and unknown player references are rejected.
State hash covers all scenario data and canonicalizes instance enumeration order.

No deck, Prize, Lost Zone, Energy attachments, damage counters, conditions, persistent
effects, hidden-information engine or turn-history model is implemented. They are
unnecessary for an isolated swap and non-executable printed preview.

Switch requires matching source/profile identity, own controlled resolving source,
own controlled Active and one own controlled Bench target. Missing choice returns
eligible instance IDs; absent Bench or invalid choice is scoped illegal. Delta swaps
exactly two locations and increments revision once; the source remains resolving.

Evaluation never mutates input. Apply requires a prior evaluation receipt, re-evaluates
against source evidence and both expected revision/hash, and compares the receipt.
It never executes a supplied delta blindly. Failure returns unchanged state. Successful
apply creates a new validated Scenario; repeated application of the same old action
is rejected. No randomness, storage writes or external I/O is performed by handlers;
the injected provider may perform read-only card lookup.

## PM review

From the implementation checkout in PowerShell, using the existing Python environment:

```powershell
$env:PYTHONPATH = Join-Path $PWD 'src'
& 'C:/Users/Mike/Documents/pokemon-tcg-lab/.venv/Scripts/python.exe' examples/rules_foundation_demo.py
& 'C:/Users/Mike/Documents/pokemon-tcg-lab/.venv/Scripts/python.exe' examples/rules_foundation_demo.py --cards 'C:/Users/Mike/Documents/pokemon-tcg-lab/data/cards.sqlite3'
& 'C:/Users/Mike/Documents/pokemon-tcg-lab/.venv/Scripts/python.exe' -m pytest tests/test_rules_foundation.py -q
```

No servers or database initialization are required. Expected demo: both profiles
REVIEWED; Switch SUPPORTED_LEGAL within switch-effect-only; exactly Active/Bench
swap; applied revision 1; original unchanged; stale apply rejected. Oddish preview
20/Grass, executable=false, INSUFFICIENT_INFORMATION, no delta.

Inspect evidence/review notes and the explicit isolation contract before approving.
If local source content changes, the live demo should refuse execution until review;
never update hashes merely to make it pass.

## Next checkpoint

Verification: 36 new deterministic foundation tests and 44 existing validator,
Deck Builder and research-copy regression tests passed (80 total). Two pre-existing
Starlette/httpx and anyio deprecation warnings. Both profiles also matched the real
read-only local card cache; the demo produced the expected swap and printed preview.
No frontend build, browser suite, broad backend suite, server restart or ingestion
was needed: no existing runtime module or database schema was changed.

The architecture is suitable for a later narrowly scoped Pass C design after PM
acceptance. Costs, private choices, usage ledgers, shuffle resolution and source-card
lifecycle are still absent. They must be specified and tested before Ultra Ball or
Gumshoos execution. Nothing in this package starts that work automatically.
