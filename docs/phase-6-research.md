# Phase 6 — Archetypes & Decklist Research

**Phase 6 — Archetypes & Decklist Research ✅ CERTIFIED** by Mike on September 25,
2026. PM manual QA: **PASS**. Accepted implementation:
`203f9cab0e2470ce82b97598113b3f3c2a47834a` on `phase6-archetype-research`.
Certification tag: `phase-6-certified-2026-09-25` (includes documentation closeout).
Based on certified Phase 5 commit
`82df55414e0b92d02b3a85ba566f69a4c42c35c1` / `phase-5-certified-2026-09-25`.
No Phase 6.5, Agent integration, new source ingestion, or rules-engine expansion.

Certified capabilities: internal Card → Archetype research; small-sample deck
discovery with the unchanged 15-deck prevalence confidence threshold; internal
Tournament Deck Research; deterministic Archetype Composite; the internal
Card → Archetype → Tournament Deck → Card research loop; main-Limitless evidence
provenance; and preservation of the Phase 5 active deck during research.
Copy to Deck Builder remains intentionally deferred.

Final pre-certification verification: 239 backend tests, 70 frontend tests and
32 browser tests passed; TypeScript and production build passed. Fresh runtime
verified schema 2 / revision 118. These are the accepted implementation results,
not expensive suites rerun during the Git/documentation-only certification closeout.

## Shared architecture and delivery slices

6A makes Card Detail archetype names and positive **Explore X decks** counts internal
links. 6B supplies archetype research, timeframe controls, functional card statistics,
and paginated observations. 6C presents actual published tournament decks, preserving
their original source lines and provenance. 6D supplies a deterministic, validated
Archetype Composite near the top of the archetype page. All use the same `Research`
service over the existing `Competitive` main-Limitless database and mapping results.

Routes are `/archetypes/:key` and `/tournament-decks/:key`; corresponding
`/deck-builder/archetypes/:key` and `/deck-builder/tournament-decks/:key` routes keep
the existing active deck tray/context. Existing Card Detail routes remain the entry
point. No separate card browser or top-level Analytics workspace was introduced.

Read-only typed resources:

- `GET /api/v1/research/archetypes/{key}` — header, timeframe and dataset accounting.
- `GET /api/v1/research/archetypes/{key}/cards` — functional-card statistics.
- `GET /api/v1/research/archetypes/{key}/decks` — paginated entrant observations.
- `GET /api/v1/research/archetypes/{key}/composite` — synthesis or truthful unavailable state.
- `GET /api/v1/research/tournament-decks/{key}` — one observed deck and archived-page hashes.

Archetype resources accept `window=7|30|90|format` (default 30). Evidence supports
`page`, `page_size` (1–50; default 20) and `include_excluded` (default false).
Invalid query values return 422; missing identities return 404; unreadable local
storage returns 503 without replacing data. No browser-time Limitless requests.

## Identity, mapping and provenance

Archetype keys are the first 24 hex characters of SHA-256 over
`limitless-main:archetype:<source archetype ID>`. Source IDs retain `/decks/N` and
their `?variant=N` distinctions. Labels are never identity. Tournament deck keys
use `limitless-main:result:<event ID>:<rank>`, matching the certified evidence unit
and primary key. Shared published-list URLs **do not deduplicate entrants**.

No schema or ingestion changes. Phase 4 normalized functional IDs, mapped quantities,
resolution flags, event JSON, result JSON and source-page URL/hash/parser records
are reused. A result is excluded from aggregates/composites in full if unresolved.
The evidence list can include excluded observations explicitly; their detail page
shows mapped cards plus all original lines and the unmapped lines, without claiming
the mapped subtotal is a complete deck. Even fully mapped decks expose original
names/set codes/numbers/counts. Finish is not inferred from source set/number lines.

Artwork reuses `representative_printings` and Library ranking, with an exact cached
historical fallback when no current Standard representative exists. Presentation
does not rewrite functional IDs. Inventory is a read-only functional total; research
tiles have no ownership/default/deck-edit controls. Existing explicit Card Detail
editing remains available after navigation in the appropriate certified context.

The stored corpus has per-event results/published counts but does not persist
individual unlisted results' archetypes. Therefore results-without-lists accounting
is explicitly **all selected tournaments**, not an invented archetype-specific count.
Source links, fetched timestamps, page hashes and parser versions remain inspectable.

## Timeframes and confidence

UTC today and inclusive `today - (days - 1)` through today match Phase 4. Format
requires an explicit configured start that is not in the future. An unavailable
Format URL remains truthful and empty; the Format control is disabled. No guessed
rotation date. Event counts and dates correspond to the selected evidence/window.

The confidence threshold remains **15 eligible mapped archetype entrant decklists**.
At 1–14, counts, copy distributions and exploratory synthesis are available, but
prevalence percentages are null and the UI says **Insufficient sample for prevalence**.
At 15+, classified archetypes may show inclusion/prevalence percentages. Unknown
archetypes remain unclassified and never get prevalence claims. Positive eligible
counts always have an Explore link; zero has no fabricated action. The Explore
count is the same eligible archetype denominator as its destination, not the number
of those decks containing the originating card.

Statistics use functional identities and whole eligible entrant observations:

- Included decks = count with quantity > 0; inclusion = included / eligible.
- Total copies = sum of observed quantities.
- Average when included = total / included; average across all = total / eligible.
- Distribution includes zero for absent decks. Median includes those zeros.
- Backend division is not rounded for display; the frontend formats to two decimals.
- Core order: descending inclusion count, descending total copies, functional ID.

These calculations extend research; existing Phase 4 usage/share/association/trend
math and source boundaries are unchanged. Sparse evidence is never called bad or weak.

## Composite algorithm: validated-observed-medoid-v1

This is a constrained deterministic synthesis, **not a tournament observation, AI
generation, optimality claim or independently rounded average deck**. It may coincide
with an observed list; it does not claim that list's entrant/event identity.

1. Select fully mapped published entrants for the archetype and timeframe, including
   small samples. Each entrant contributes separately even if lists are identical.
2. Build per-functional-card quantity histograms including zeros. Candidate vectors
   are the unique whole 60-card quantity vectors actually observed in this evidence.
3. Score each candidate by summed absolute copy-count distance to every eligible
   entrant, computed exactly using integer quantity histogram frequencies. Lower is
   more representative of the observed distribution.
4. Ties favor the larger sum of inclusion counts for present cards, then the sorted
   functional-ID/quantity vector lexicographically. Names, input enumeration, player,
   rank and source-list URL do not break ties. No randomness or model calls.
5. In this stable order, validate candidates with the existing `Lab.validate` and
   Phase 5 `DeckProvider`, requiring a complete deck. Use existing curated Basic
   Energy type keys only for validation; evidence/statistics retain canonical IDs.
   Aggregate Energy keys before validation. Ambiguous/Special Energy does not gain
   the unlimited Basic exemption.
6. Return the first candidate passing supported checks. Whole-vector selection is
   the 60-card reconciliation: no fractional rounding, padding or unseen cards.
   If none passes, return an empty composite with reasons; never fabricate one.

Legality uses current cached Standard evidence and inherited limits: 60 cards,
name-based copy limits, Basic Pokémon and ACE SPEC. This does not certify historical
tournament legality, bans or every card-specific exception. No passing observed
candidate does **not** prove that no other synthetic combination could be valid;
the algorithm deliberately stays within observed structures. This conservative
candidate-space limitation is exposed in the UI. Fewer than 15 decks does not block
construction; the result is labeled **Limited evidence** with its exact sample count.

## Navigation, performance and copy status

Research timeframe, Gallery/List mode, evidence page and excluded toggle live in
URLs (`window`, `view`, `page`, `excluded`) and survive reload/deep links. Router state
retains the originating URL/context; a bounded-to-session research scroll map restores
scroll on return. Existing Library filters/category/page/view memory is reused.
Deck Builder prefix routes retain its active provider and tray. Card tiles reuse
the existing image-only competitive hover (500 ms) and Card Detail navigation.
Research itself does not mutate the active deck, saved decks or collection.

Copy Tournament Deck / Copy Composite to Deck Builder is **deliberately deferred**.
The typed functional-ID/quantity payloads support a future copy boundary, but no
bulk mutation is added to Phase 5's transactional API and no loop of quantity writes
pretends to be an atomic copy. A later implementation must explicitly handle dirty
work, revision checks, preferred-printing resolution and preservation of evidence.

SQL selects the archetype/timeframe before parsing deck JSON. Only the selected
window's archetype observations are aggregated, and only a page of observations
is sent to the browser. Tournament lookup scans compact event/rank columns before
loading a single deck. Artwork resolution is batched; validator card reads are
cached within a composite request. Normal browsing has no upstream requests or
per-card statistics API loop; competitive hover remains on demand.

## Runtime discipline and PM startup

Permanent rule: after backend/API changes **stop the old runtime, start fresh, hard
refresh, verify commit/schema/revision, then QA**. Check runtime/version/cache state
before diagnosing a defect. From this checkout:

```powershell
.\scripts\Start-Phase6-QA.ps1 -Action Restart
git rev-parse HEAD
```

Open `http://127.0.0.1:5175/deck-builder`, hard-refresh with Ctrl+Shift+R, inspect a
card, then open Competitive Research → archetype / Explore decks. API port is 8003.
`GET /api/v1/deck-workspace` must report the checkout HEAD, schema 2 and the preserved
workspace revision. The wrapper reuses the guarded launcher and existing isolated
`.cache/manual-qa` databases; it does not reset the Phase 5 QA deck or collection.
The real source/card/competitive databases remain read-only during browsing.

## QA scope matrix

### 🟢 WIRED

- Card → Archetype and positive Explore counts, including samples 1–14 and 15+.
- Archetype headers, four timeframe choices with truthful unavailable Format,
  functional inclusion/count/average/distribution/median statistics.
- Paginated entrant evidence, shared-list entrant preservation, excluded-list toggle.
- Tournament Deck Gallery/List, exact published source lines, metadata and hashes,
  informational ownership, image-only hover, Card Detail and internal research links.
- Reproducible 60-card supported-check-valid medoid composite or explicit unavailability;
  small-sample labeling, no invented cards, Basic Energy validator compatibility.
- Builder-context tray preservation; research URL state, back context, session scroll,
  deep links/reloads; unchanged ownership/deck data during browsing.

### 🟡 PARTIAL — deliberate limits

- Copy-to-Deck-Builder payload architecture exists; the UI action/mutation is deferred.
- Composite searches observed whole-deck vectors, not every possible combination.
- Results without lists have dataset-level counts, not stored per-archetype identity.
- Scope is locally cached published main-Limitless international Standard evidence;
  source/validator limitations and missing mappings remain visible.
- Scroll context is session memory; URLs persist timeframe/view/page/filter state.

### ⚪ NOT WIRED

- Phase 6.5, Agent/AI calculations, new ingestion/sources, automatic deck optimization,
  expanded rules engine, hosted accounts, source deck rewriting or ownership import.

### 🧊 FROZEN

- Certified Phases 1–5 identities, Variation Family rules, exact finishes/allocations,
  preferred printing, collection writes, validation, save/open persistence, foil masks
  and shimmer, source mapping/ingestion, competitive calculations and hover timing.
