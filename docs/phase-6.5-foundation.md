# Phase 6.5A/B/C/D — isolated rules/mechanics foundation

**Phase 6.5 — Rules & Interaction Foundation ✅ CERTIFIED** by Mike following
manual PM QA PASS for A/B/C/D. Certification date: September 25, 2026. Baseline:
`645bc3b3188995a9cbc51c20e17738413ddd99ca`. Branch: `phase6.5-rules-foundation`.
A/B passed PM QA at `b17195a310564e35e92129aae517b56c44594ef5`.
Pass C passed PM QA at `af6f58aa5c308d71e071331126fae748968eee7b`.
Pass D passed PM QA at `f57d06d8466de1c977fa53c4b5642021681ded0e`.
Preservation tag: `phase-6.5-rules-foundation-certified-2026-09-25`, targeting the
final documentation closeout/main commit. No UI, public API, Agent or battle engine.

## Certification closeout

Certified scope is a deterministic rules and interaction **foundation**, not a
complete Pokémon TCG rules engine:

- **A — contracts, authority and evidence:** reviewed profiles, exact fingerprints,
  versioned interpretations/handlers, provenance, explicit support states and stale
  invalidation; unsupported/insufficient information are first-class results.
- **B — scenario and transitions:** unique gameplay instances, owner/controller/
  location, revision/hash, pure evaluation, exact deltas, receipt-verified atomic
  apply, stale/forged rejection; isolated Switch and non-executable Oddish preview.
- **C — costs, choices, usage and privacy:** Ultra Ball's distinct two-card cost,
  bounded search, selected-only reveal and explicit deterministic shuffle; Evidence
  Gathering's private exchange, instance-scoped usage and external turn boundary.
  Perspective-filtered serialization; no hidden randomness or partial application.
- **D — persistent conditional derivation:** Rescue Board attachment, bounded reusable
  modifier, remaining-HP condition, printed retreat derivation and zero floor;
  remaining HP ≤30 sets zero. Unknown relevant effects block definitive answers.
  No retreat execution, state mutation or derivation delta.

Closeout changes documentation/Git only. Previously completed, PM-reviewed validation
is **136 tests passed: 32 D + 81 A/B/C + 23 Deck Builder/research-copy regressions**.
Fixture and real-cache demos passed; database hashes were unchanged. No broad suites
were rerun for closeout and no new validation total is asserted.

The next-phase boundary remains explicit: no Phase 7 Agent/Research Mode, Agent
context/provider logic, AI integration, UI/API exposure or broader mechanics work.
General setup/mulligan/turn/gameplay loops, universal legal actions, Item/Supporter/
Ability timing, full Trainer/Tool legality, modifier stacking/order, Energy payment,
attack/retreat execution, Weakness/Resistance, damage ordering, conditions, evolution,
KO/prizes, Lost Zone behavior, comprehensive ruling corpus, broad card coverage,
battle simulation and goldfish/self-play remain unsupported. Unknown relevant
mechanics must be reported rather than guessed. No runtime semantics or database
schema changed; certified collection, printing, deck and research systems are preserved.

## Actual architecture

`pokelab.rules.models` contains frozen, extra-forbidden Pydantic contracts.
`registry` holds five reviewed profiles, evidence excerpts and source fingerprints.
`evaluate` provides pure `evaluate` and `apply` functions over caller-owned scenarios.
Existing CardProvider lookup, functional_signature and identity hashing are reused
without changing any certified identity, deck validation or persistence behavior.

The A/B executable transition is **resolution of an already-authorized isolated
Switch effect**. The caller places Switch in `resolving`; that handler does not
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

The interpretations were engineering-reviewed against pinned local source
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
Zones are Active, Bench, resolving, hand, discard and deck with positions. A position
bound is an input safety limit, not an official Bench-capacity rule. Duplicate IDs,
duplicate slots, invalid Active positions and unknown player references are rejected.
State hash covers all scenario data and canonicalizes instance enumeration and usage
ledger order. Additive C fields are an optional external turn token and usage entries.
When both are absent, original A/B state hashes are retained. Schema 1 and the A/B
ruleset context pin remain; C has separately identified/versioned profiles and handlers.

No Prize, Lost Zone, Energy attachments, conditions, universal visibility engine or
turn engine is implemented. C's ordered deck, usage entries and bounded projections,
and D's damage-counter input and attached modifier derivation, are described below.

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

## Accepted A/B verification

Verification: 36 new deterministic foundation tests and 44 existing validator,
Deck Builder and research-copy regression tests passed (80 total). Two pre-existing
Starlette/httpx and anyio deprecation warnings. Both profiles also matched the real
read-only local card cache; the demo produced the expected swap and printed preview.
No frontend build, browser suite, broad backend suite, server restart or ingestion
was needed: no existing runtime module or database schema was changed.

## Pass C implementation and scope

No material A/B redesign was required. `interactions.py` supplies two handlers to the
existing evaluator; both produce its same revision-bound delta/receipt and use its
same atomic apply path. `models.py` adds typed choices, ordered steps, deck locations,
an optional external turn token and a usage ledger. `perspective.py` filters trusted
results for a specified player. None of this is connected to the public API or UI.

**Ultra Ball, me01-131:** `ultra-ball.cost-search` version 1, handler `ultra-ball`
version 1, scope `ultra-ball-effect-only`. The exact cached text starts “You can use
this card only if you discard 2 other cards from your hand.” It is pinned verbatim,
including the blank line before the search instruction; the brief's paraphrase is
not substituted for source evidence. Source starts and remains in resolving. General
Item legality, source play/discard, timing and triggers are not implemented.

Cost is exactly two distinct other own, controlled hand instances. Choice validation
precedes all application. After a valid cost proposal, search accepts exactly one
own, controlled deck Pokemon. The successful receipt explicitly orders **cost:
discard**, then **effect: search, reveal, move-to-hand, shuffle**. All changes commit
together; failed costs, invalid targets or absent/invalid shuffle resolution discard
nothing. Search with no eligible Pokemon returns UNSUPPORTED; there is no invented
no-result/fail-to-find rule.

Choices carry an ID, type, cardinality, bounded candidates, supplied selections,
constraint and rejection reason. Missing selections return NEEDS_CHOICE, beginning
with payment, then search, then shuffle resolution. Search candidates are not exposed
before a valid cost proposal and are sorted by opaque ID, not hidden deck position.
These are isolated trusted-engine proposals, not an implemented interactive search
session or cancellation/rollback protocol for a real game.

The explicit shuffle input is an exact permutation of every remaining own deck
instance. Duplicates, foreign/missing/extra instances reject the entire transition.
An empty remaining deck still requires an explicit empty permutation. No random
generator is called. **The permutation belongs to a trusted resolver, not a player's
choice of deck order.** This proof checks permutation completeness, not randomness
quality or fairness. Positions define deck order (lowest position is top); gaps are
allowed. Ultra Ball packs affected hand/discard/deck positions; Gumshoos swaps slots.

**Gumshoos, me01-110:** `gumshoos.evidence-gathering` version 1, handler
`evidence-gathering` version 1, scope `evidence-gathering-only`. The exact cached
Ability is “Once during your turn, you may use this Ability. Switch a card from your
hand with the top card of your deck.” Only that Ability is executable; Bite is not.
An own in-play source exchanges the chosen hand instance with the top own deck
instance. All other slots are preserved. Empty hand/deck cannot perform this exchange.

The reviewed restriction is **instance-scoped**, keyed by external turn token,
player, source instance and named effect. A second source has its own availability.
The ledger distinguishes instance/player/named-effect scopes; a conflicting scope
for this Ability fails closed rather than silently applying a generic rule. First
use adds one entry atomically; repeat in that turn is blocked. An authoritative host
can supply a fresh turn token and advance revision to demonstrate later availability.
The package cannot authenticate turn progression and does not implement leave/re-enter
resets, evolution, turn history or general Ability timing. Callers must not declare
isolation when such dependencies are unresolved.

## Pass C privacy and atomicity

Raw Scenario, Action, Evaluation and ApplyResult objects contain trusted hidden
information. **Never serialize them directly to a player.** The host selects the
authenticated perspective; these helpers are filtering, not an authentication layer.
Only evaluator-produced results are appropriate inputs, not client-forged receipts.

- `state_view`: public zones show instances/printings; own hand is visible; opponent
  hand and all decks expose counts only. No private hash, deck order or hidden IDs.
- `evaluation_view`: an opponent sees only a private-pending marker, including on
  failed proposals. The actor sees choice/check information, but no delta, top-deck
  card, state hash or shuffle permutation. Authorized search candidates are available
  after a valid cost proposal. No proposed reveal is published to an opponent.
- `apply_view`: state projection plus committed reveal events. Successful Ultra Ball
  reveals only its selected Pokemon; cost cards appear in the public discard zone.
  Gumshoos publishes no reveal: only the acting hand view sees the received top card.
  Failed applications publish no reveal. Events are not a persistent knowledge ledger.

Pure evaluation and complete receipt comparison are retained. Apply recomputes the
entire cost/effect/usage delta against the expected revision/hash and current reviewed
source. Changed choices, forged moves/steps/usage, changed state or stale evidence
cannot apply the old receipt. No intermediate cost state is emitted or persisted.
Schema-invalid inputs raise validation errors before mutation; semantically invalid
valid-model inputs return an unchanged state with a scoped rejection.

Both new profiles use the existing fingerprint/evidence gate and versioned reviewed
interpretations. Exact local source fields were inspected; real-cache demo resolves
both as REVIEWED. Unknown source retrieval/effective dates remain null. No online
rulebook or rulings were imported and no official-complete legality is asserted.

## Pass C PM review commands

From PowerShell:

```powershell
Set-Location 'C:/Users/Mike/Documents/Codex/2026-09-25/referenced-chatgpt-conversation-this-is-an/work/phase5'
$env:PYTHONPATH = Join-Path $PWD 'src'
$env:PYTHONIOENCODING = 'utf-8'
& 'C:/Users/Mike/Documents/pokemon-tcg-lab/.venv/Scripts/python.exe' examples/rules_costs_choices_demo.py
& 'C:/Users/Mike/Documents/pokemon-tcg-lab/.venv/Scripts/python.exe' examples/rules_costs_choices_demo.py --cards 'C:/Users/Mike/Documents/pokemon-tcg-lab/data/cards.sqlite3'
& 'C:/Users/Mike/Documents/pokemon-tcg-lab/.venv/Scripts/python.exe' -m pytest tests/test_rules_foundation.py tests/test_rules_costs_choices.py -q
```

Expected checkpoint: `PASS C DEMO PASSED — NOT PM CERTIFICATION`. Inspect the pinned
provenance, payment/search choice stages, ordered cost/effect steps, successful
application and invalid-cost atomicity. Bob's Ultra Ball view reveals only the
selected Pokemon plus public discard cards. Bob's Gumshoos view contains no exchanged
IDs; Alice sees the received card. Repeat reports ALREADY_USED; fresh external turn
reports SUPPORTED_LEGAL; stale replay is rejected; original state remains unchanged.
The JSON includes explicitly labelled trusted evidence/steps for PM inspection; it is
not a player response format.

Verification: 81 foundation tests (36 existing A/B, 45 Pass C) and 23 focused existing
Deck Builder/research-copy regressions passed, **104 total**. Two existing third-party
deprecation warnings. No frontend/browser/build work is warranted for this disconnected
backend package. No database schema, migration, runtime revision or certified system
semantics changed; all state exists only in caller-owned memory.
Fixture and real-cache C demos passed, as did the A/B real-cache demo. SHA-256 hashes
of card, collection and competitive databases were unchanged across these read-only
checks. Additional focused receipt assertions (serialized round-trip, forged steps
and removed usage entries) passed in the final 45-case C run.

Changed files: `rules/models.py`, `rules/registry.py`, `rules/evaluate.py`,
`rules/__init__.py`, this document. Added: `rules/interactions.py`,
`rules/perspective.py`, `tests/test_rules_costs_choices.py`,
`examples/rules_costs_choices_demo.py`.

At the C checkpoint the architecture was suitable for a separately scoped Pass D,
subsequently authorized after Mike's acceptance. Broad card coverage,
global Trainer/Ability timing, automatic parsing, Energy solving, damage/KO/prizes,
conditions/evolution/retreat, battle loop, Agent integration, corpus ingestion and
historical rulesets remain unsupported. Certified collection, printing, deck,
analytics, research, copy and gallery behavior is untouched.

## Pass D — persistent conditional modifier proof

Architecture outcome **B: a small justified reusable modifier primitive**, extending
the existing Scenario, registry, evaluation receipt, status and perspective contracts.
No parallel evaluator, material redesign or retreat transition was needed.

Exact cached source: **Rescue Board, sv05-159**, Trainer / Tool, Uncommon,
regulation H, cached standard/expanded flags true. These are source fields, not a
current tournament-legality determination. CARD_TEXT `/effect` is pinned verbatim:

> The Retreat Cost of the Pokémon this card is attached to is {C} less. If that Pokémon's remaining HP is 30 or less, it has no Retreat Cost.

The condition is **remaining HP**, not simply the presence of damage counters.
The profile `rescue-board.retreat-cost` v1 / handler `attached-retreat-cost` v1 binds
printing, existing functional identity, mechanics fingerprint, source evidence and
engineering-reviewed interpretation. The real-cache demo verifies all of them.
Changing effect/classification or any included fingerprint field marks it STALE.

An attached gameplay CardInstance has `attached_to` referencing an in-play host and
an `attached` location. Its unique ID, owner/controller, printing and profile remain
intact. Attached positions are unique within the player's attached zone, not separate
per-host slot numbers. Missing/non-in-play hosts, duplicate IDs/slots, and mismatched
host/attachment ownership or control are schema-invalid. Provider verification rejects
non-Pokemon hosts and source identity/profile mismatches. This validates only the
bounded existing relationship; it never authorizes attaching a Tool. Existing A/B/C
transitions fail explicitly if attachments are present, rather than ignoring newly
representable attached effects.

Optional `damage_counters` lives on the gameplay instance; unknown is distinct from
zero. Printed HP and retreat are read from the local host record, whose fingerprint
is included in the derivation. In the explicitly isolated unmodified-HP context:
remaining HP = printed HP minus 10 per damage counter. More than 30 HP applies
subtract-one with floor zero. At 30 HP or less the operation is set-zero instead.
Nonpositive remaining HP fails as an unsupported knockout boundary. Missing/invalid
printed values or unknown damage counts return INSUFFICIENT_INFORMATION.

`PersistentModifier` identifies source instance/profile, affected host/value,
condition/threshold/result, selected arithmetic operation and amount, while-attached
duration, single-modifier scope, evidence and unsupported dependencies.
`RetreatDerivation` records base cost, printed HP, counters, remaining HP, modifier,
result, host printing/fingerprint and `executable=false`. It is recomputed from current
state, never persisted as a changed printed stat. Off-turn derivation is allowed:
persistence does not grant permission to initiate retreat.

A SUPPORTED_LEGAL result means only **attached-retreat-cost-only derivation**, with
check DERIVED_VALUE_ONLY. It does not mean legal retreat. No delta is produced;
calling apply returns applied=false and unchanged state. Unknown declared relevant
effects (including HP modifiers) block any definitive derivation through the existing
dependency gate. Multiple attachments on the affected host fail UNSUPPORTED; no
relevance, stacking or ordering rules are guessed. The host must honestly declare
isolation and relevant dependencies, as in A/B/C.

The public derivation projection contains only the in-play host/source inputs and
evidence. Neither player's projection includes hidden hand/deck instances, choices,
private state hashes or unrelated card data. Raw receipts remain trusted-engine data.
New optional instance fields preserve prior A/B/C hashes when absent; all declared
attachment and damage state is hashed when present. No database schema or migration.

### Pass D PM command

```powershell
Set-Location 'C:/Users/Mike/Documents/Codex/2026-09-25/referenced-chatgpt-conversation-this-is-an/work/phase5'
$env:PYTHONPATH = Join-Path $PWD 'src'
$env:PYTHONIOENCODING = 'utf-8'
& 'C:/Users/Mike/Documents/pokemon-tcg-lab/.venv/Scripts/python.exe' examples/rules_modifier_demo.py --cards 'C:/Users/Mike/Documents/pokemon-tcg-lab/data/cards.sqlite3'
```

Omit `--cards ...` to run against deterministic cached excerpts. The host is Bulbasaur
me01-001: printed HP 80, retreat 2. At zero counters, 80 remaining HP produces cost 1.
At five counters, 30 remaining HP produces cost 0. Its attack is not implemented.
Inspect profile/provenance and both typed derivations, then unknown-modifier
UNSUPPORTED, changed-source STALE, no delta and no mutation. The command ends:
**PASS D DEMO PASSED — NOT PM CERTIFICATION**.

Verification: **136 passed** — 32 Pass D, all 81 A/B/C tests, and 23 targeted existing
Deck Builder/research-copy regressions. Two existing third-party deprecation warnings.
Coverage includes both threshold paths, zero floor, missing/malformed attachment and
host inputs, identity/fingerprint changes, duplicate and multiple attachments,
unknown effects, deterministic immutable evaluation, no executable delta, off-turn
persistence and private-information filtering. No broad suite, frontend or browser run.
Both fixture and real-cache demos passed. Card, collection and competitive database
SHA-256 hashes were unchanged across the demo runs.

Files: modified rules models/registry/evaluator/exports/perspective, prior C hash
compatibility test and this document; added `rules/modifiers.py`,
`tests/test_rules_modifiers.py`, `examples/rules_modifier_demo.py`.

The A/B/C/D foundation has passed Mike's final PM QA and is certified as recorded
above. The following implementation exclusions remain unchanged. No actual
retreat, Energy payment, retreat-use tracking, general Tool legality/removal/replacement,
modifier stacking/order, attacks, damage/healing/KO/prizes, additional mechanic,
Phase 7, Agent, UI/API or rules-corpus work was implemented. Certified deck, collection,
printing, competitive and research systems remain unchanged.
