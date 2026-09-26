# Phase 7A — deterministic Agent Evidence Packet

Implementation awaiting Mike's PM QA. Certified base:
`88e3675d4844bbc70543aab97b5e2983b8348eda`; branch `phase7-agent-context`.
No merge, tag or certification closeout. No Phase 7B work.

## Authority and implementation

The agent will eventually reason over evidence. This pass has no model, provider,
transport, API, UI, actions or memory. It assembles a bounded immutable packet from
an explicit selected-card retrieval intent, not a natural-language planner.
Question text is data, never SQL, URLs, instructions to tools or authorization.

- `agent_context_models.py`: frozen, extra-forbidden Pydantic contracts with nested
  frozen models and tuples. Four classifications: SOURCE_FACT, DERIVED_FACT,
  EMPIRICAL_EVIDENCE, RULES_RESULT. Support/availability remains separate.
- `agent_context_sources.py`: host-supplied distinct paths; SQLite `mode=ro`,
  `query_only=ON`, read transactions and schema/table checks. Request-owned leases
  let certified services reuse the same transactions without closing them early.
  Missing/old/incompatible stores are unavailable, never initialized or migrated.
- `agent_context.py`: certified catalogue identities, deck allocation checks and
  Decks.validation; certified main-Limitless Competitive.stats; bounded Research
  observations and optional composite. No duplicate statistics implementation.
- `agent_rules_view.py`: profile availability or recomputed, receipt-matching,
  explicitly supplied host-only scenario context. No scenario is inferred from a
  deck or question. The certified rules package is unchanged.

The read-only collection adapter builds the existing CollectionSnapshot shape from
read-only rows, omitting preferences. It never calls Collection.initialize or the
initializing Collection.snapshot. Deck context reads only the existing active row;
it does not call Decks.read/initialize/response. Deck validation reuses its certified
pure calculation. Source connections deny writes even if an inherited service method
were accidentally called. Only final packets are intended for a future Agent; source
objects and trusted rules inputs remain host-owned implementation details.

Each store is transactionally consistent. Main-file/WAL/journal size and timestamp
checks before/after retrieval reject concurrent changes as inconsistent_snapshot and
discard all assembled evidence. This is conservative local consistency detection,
not a distributed atomic transaction across stores; deliberate timestamp-preserving
file replacement is outside this local single-user boundary. Hosts must supply the
correct paired workspace/collection; there is no fallback or stored pairing identity.

## Contract and selection

Request: bounded question, fixed intent, exact printing, optional finish/archetype/
observation, optional composite, timeframe and pinned as_of. No provider config.

Packet: schema/builder versions, canonical content hash, typed evidence, compact
references, requested/included/omitted/unavailable coverage and measured budget.
Card includes exact printing plus canonical functional and deck keys. Basic Energy
uses existing deck-type identity. Exact ownership remains separate from functional
totals. Deck includes revision/hash, dirty flag, functional-entry count, selected-card
quantity and authoritative supported validation/limitations. It does not expose all
allocations, preferences, saved decks, private notes or the full collection.

Competitive values retain numerator, denominator, nulls, exclusions, source error,
window, threshold and observational limitations. The selected archetype is preferred
when explicitly focused, then existing deterministic ranking. Default caps: 3
archetypes, 5 associations, 3 observations, 3 event references, 1 rules item. No trends.
References beyond caps are omitted explicitly; aggregate provenance has a content
fingerprint. Observation quantities are facts about one published list, not advice.
Optional composite remains DERIVED_FACT with its existing algorithm, sample size,
limited-evidence status and non-optimality limitations. No AI inference is generated.

Evidence IDs derive from classification, payload and reference IDs. References retain
source/resource IDs, applicable checked/event dates, URLs, source content hashes,
parser/profile/algorithm versions and bounded excerpts/page-hash metadata. Missing
timestamps remain null. Collection/deck references are content snapshots rather than
invented retrieval timestamps. Read sources may scan the local catalogue/corpus in
memory; none of those full datasets are serialized to the packet.

Canonical serialization is sorted UTF-8 JSON with compact separators. Packet hash
covers all content except its own field, including budget and coverage. Size accounting
converges to include the entire serialized packet. Estimated tokens = ceil(bytes/4),
explicitly approximate rather than a tokenizer count. Hard ceiling 24 KiB, configurable
down to 4 KiB for tests. Optional observations, composite and competitive sections
are dropped whole in that order when needed; associated references are removed too.
Never remove a denominator, status or limitation from a retained evidence item. If
mandatory content still cannot fit, return budget_exceeded with no evidence. No
attempt is made to fill the budget. Large questions remain bounded to 2,000 characters.

## Rules and privacy

Without a scenario, Ultra Ball returns REVIEWED profile availability but
INSUFFICIENT_INFORMATION / profile-only / execution_authorized=false. The registry's
source text and reviewed interpretation explain the bounded cost/search effect.
Profile and interpretation share the existing profile version; handler version is
retained separately. A stale profile never grants approval.

Trusted scenario input is a host-only tuple of action, scenario, receipt and
authenticated perspective. The adapter re-evaluates and compares the receipt before
projection. This is not authentication and must not be filled from arbitrary client
input. Raw action/scenario/receipt, state hashes, shuffle permutations and private
choice IDs are never serialized. Opponent pending results are withheld. Public
Switch targets/location summaries may be included; private cost/search/exchange
steps expose operation names only. Oddish remains a non-executable preview; Rescue
Board remains a non-executable derivation. No packet authorizes execution, even when
the preserved scoped status is SUPPORTED_LEGAL.

Known public dependency labels (e.g. energy-payment and weakness-resistance) survive.
Unrecognized dependency text may embed concealed IDs, so it is replaced with an
explicit additional-private-or-unreviewed-dependency marker. This is intentional
privacy redaction, not an assertion that the dependency is resolved. Raw diagnostic
detail remains in the trusted gameplay system. No new rules capability was added.

## Validation and observed real-data demo

Stable run: **178 passed**, with two existing third-party deprecation warnings:

- 26 new focused cases: 22 storage/service integration and 4 rules-adapter unit cases.
- 113 unchanged A/B/C/D rules regression cases.
- 39 unchanged regressions: 23 Deck Builder/research-copy and 16 research cases.

Tests cover blocked network/writable connections and rejected SQL writes, missing and
incompatible stores, missing card, format unavailable/nulls, 15-deck threshold,
service parity, Basic Energy, mixed allocations, exact/functional ownership,
immutability, deterministic bytes/hash/references/budget, stale rules, illegal/preview/
derived results, hidden identifiers and concurrent-source change rejection.

Fresh-process real demo observed on the explicitly selected QA stores:

- Packet v1: 10,105 bytes; approximately 2,527 tokens; 6 evidence items.
- Packet hash: `a98e533dc169fa6d7aa559181622ade13d11508c0b87906ef349b00491eaac3e`.
- Window: 2026-08-27 through 2026-09-25; 3 events, 734 eligible/published lists.
- Ultra Ball: 648/734, 88.2834%; average copies when included 3.2269.
- Dragapult: 159/159; no unmapped exclusions or results without lists in this window.
- Active QA deck revision 155, VALID, clean, 60 cards, 29 functional entries, 4 Ultra Ball.
- Paired QA collection: Ultra Ball functional ownership 0; this printing normal 0,
  reverse 0, unspecified 0. Deck inclusion does not imply ownership.
- Selected tournament observation has 3 Ultra Ball; this is evidence, not a suggestion
  to reduce the active deck from 4.
- Ultra Ball profile `ultra-ball.cost-search` v1, handler v1, REVIEWED;
  `ultra-ball-effect-only`, profile-only, missing explicit gameplay scenario,
  INSUFFICIENT_INFORMATION, execution_authorized=false.
- All references resolved. Ranked-cap omissions recorded for archetypes/associations;
  no budget-forced omissions. Zero network/model calls and writable connections.
- SHA-256 of all four database files and any existing WAL/SHM/journal sidecars remained
  unchanged across two deterministic builds. No live QA server restart was needed.

These values describe the inspected snapshot, not hardcoded permanent expectations.
The demo queries current ownership and service results. A changed dataset/workspace
may legitimately change its values/hash; it must still pass structural and safety checks.

## Exact PM QA steps

From PowerShell, use a fresh process:

```powershell
Set-Location 'C:/Users/Mike/Documents/Codex/2026-09-25/referenced-chatgpt-conversation-this-is-an/work/phase5'
$env:PYTHONPATH = Join-Path $PWD 'src'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONIOENCODING = 'utf-8'
& 'C:/Users/Mike/Documents/pokemon-tcg-lab/.venv/Scripts/python.exe' examples/agent_context_demo.py --cards 'C:/Users/Mike/Documents/pokemon-tcg-lab/data/cards.sqlite3' --collection '.cache/manual-qa/user-state.sqlite3' --workspace '.cache/manual-qa/deck-workspace.sqlite3' --competitive 'C:/Users/Mike/Documents/pokemon-tcg-lab/data/competitive.sqlite3'
```

Inspect REQUEST, PACKET, SELECTED CARD, ACTIVE DECK, COLLECTION, COMPETITIVE EVIDENCE,
TOURNAMENT REFERENCE, RULES, PROVENANCE, BUDGET and SAFETY. Ensure the ownership is from
the intended paired QA store and that no scenario legality is claimed. Success ends
`PASS 7A DEMO — NOT PM CERTIFICATION`. Missing storage, mismatched hashes, privacy/
determinism assertions or unavailable required sections prevent the success marker.

Focused repeat, if needed:

```powershell
& 'C:/Users/Mike/Documents/pokemon-tcg-lab/.venv/Scripts/python.exe' -m pytest tests/test_agent_context.py -q
```

No provider/API keys, API/UI, MCP coupling, Agent action, memory, database migration,
new mechanics, analytics changes or hover changes. The requested deterministic
competitive-hover hierarchy is recorded in README's future polish backlog only.
No Phase 7B, merge, tag or certification work is part of this implementation.
