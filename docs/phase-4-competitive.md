# Phase 4 — Competitive Analytics (awaiting Mike's manual certification)

## Boundaries

Phase 4 uses **main Limitless**, source key `limitless-main`. It does not read the
legacy Play! Limitless tables. Card cache and collection storage remain unchanged.
Canonical playable identities reuse `functional_signature`, `normalized_name`, and
the existing SHA-256 `identity` function. No printing/finish identity is redefined.

The existing Qt analytics module remains intact for compatibility. Its Play!
Limitless refresh is not a Phase 4 ingestion mechanism. No AI, deck builder,
archetype workspace, tournament browser, ranking or weighting was added.

## Ingestion and provenance

Read-only inspection on 2026-09-24 examined:

- https://limitlesstcg.com/tournaments — `data-date`, `data-format`, event links,
  player counts and explicit pagination attributes.
- https://limitlesstcg.com/tournaments/441 — result rank/player/archetype attributes
  and links to published decklists.
- https://limitlesstcg.com/tournaments/441/decklists — text card rows with set,
  number, language, name and count. The saved fixture contains eight 60-card lists.
- https://limitlesstcg.com/cards/MEE/13 — basic Psychic Energy, with reprint links.

No documented structured feed was established in this short inspection. The
adapter uses the semantic HTML attributes rather than visual table positions.
Saved HTML fixtures under `tests/fixtures/limitless` are offline test inputs.
They contain source content; do not execute their scripts or open as trusted UI.

Only completed **international Standard** (`data-format=standard`) main Masters
results are included. Standard-JP and Expanded are excluded; their card pools
are not silently mixed. Time windows can include several set-release formats:
the source format labels are not inferred as a format-start date.

The operator command is the sole network ingestion entry point:

```powershell
$env:PYTHONPATH = 'src'
.venv\Scripts\python.exe -m pokelab.ingest_competitive --days 90 --max-events 25
```

Requests are sequential, two seconds apart, bounded by days/events, without
redirects. Any HTTP error (including 429) stops ingestion and records a visible
failure. Re-run later; successful prior event transactions remain intact. There
is no automatic scheduling and no browser refresh/scraping endpoint.

Each event atomically replaces its normalized evidence. Event IDs plus result
ranks identify participant decklists. Multiple participants may share a list URL
and still count separately. The parser checks required attributes, pagination,
duplicate ranks, all expected published-list ranks and exactly 60 cards per list.
A missing or malformed card/list aborts that event rather than manufacturing zero.
An empty published-list section is accepted only when results list no published
decklist links. Results without lists never enter the denominator.

The separate `data/competitive.sqlite3` holds source-keyed event metadata, result
details, raw card/count lists, normalized functional counts, unresolved card rows,
full fetched HTML, SHA-256 hashes, parser version and fetch timestamps. The API
exposes source URLs, event dates, fetch times, sample/exclusion counts and the last
ingestion failure. HTML is stored as evidence and never served as executable UI.

Resolution first uses source set code and collector number. If unavailable, a
unique same-set, same-name **basic Energy** identity is eligible (needed for MEE
9–16 artwork missing from the local cache). Otherwise only a globally unique
functional identity for the normalized card name is accepted, following the
existing resolver's conservative fallback. Ambiguous cards exclude the entire
list. No fuzzy matching, AI mapping or canonical identity merging occurs.

After updating the card cache, explicitly re-normalize evidence:

```powershell
.venv\Scripts\python.exe -m pokelab.ingest_competitive --remap
```

This uses saved normalized source lists without network access and preserves
original fetch timestamps. Re-ingest if a parser change requires re-reading HTML.

Configuration:

- `POKELAB_COMPETITIVE_DB_PATH`: evidence path; defaults beside card cache.
- `POKELAB_FORMAT_START=YYYY-MM-DD`: explicit inclusive format boundary. Without it,
  Format is unavailable. Future boundaries are unavailable until reached.
- Existing `TCG_CARDS_DB_PATH` and `POKELAB_USER_DB_PATH` retain their meaning.

## Analytics definitions

Calendar dates are UTC. Rolling N-day windows include today and the preceding
N−1 days. Future events are excluded. Format includes the configured start date
through the evaluation date. All metrics are unweighted deterministic counts.

- **Eligible sample:** fully resolved, published, 60-card participant decklists
  in cached main-Limitless international Standard events within the window.
- **Usage:** 100 × eligible lists with at least one copy / all eligible lists.
  A rare observation such as 14/5,000 is 0.28%, not insufficient sample.
- **Average copies:** total copies / lists containing the card; unavailable if
  none contain it. Counts are summed across printings of the same identity.
- **Copy distribution:** fraction of containing lists with 1, 2, 3 or 4+ copies.
  Basic Energy and other real counts above four are retained in 4x+.
- **Where played:** containing lists in an archetype / all containing lists.
  This descriptive distribution includes unclassified lists; top five ordering
  is count descending, then source archetype ID. Variants retain source labels.
- **Prevalence within archetype:** containing lists in that archetype / all
  eligible lists of that archetype. Below 15 eligible archetype lists, percentage
  is null and UI shows `Insufficient sample — N decklist(s)` with correct grammar.
  Unknown archetypes do not receive prevalence claims. Zero prevalence is valid
  at/above 15. The eligible count remains visible. Ordinary field usage is ungated.
- **Associated Cards:** field-level co-occurrence P(B|A), baseline P(B), and
  lift P(B|A)/P(B). Minimum five A-containing lists and three joint observations.
  Default ordering uses the 95% Wilson lower bound of P(B|A), divided by P(B),
  then lift and stable functional ID. Maximum 20 results. This favors supported
  association over universal staples. No archetype-specific association is offered.
- **Usage Trend:** one graph, rolling 7/30/90-day plus cumulative Format series,
  independent of the dashboard window. When Format is available, the axis spans
  its explicitly configured start through today; plotted dates are actual cached
  event dates in that period, including those older than 90 days. Otherwise the
  axis spans the available event dates within the last 90 calendar days.
  Earlier cached events still contribute to rolling
  windows/cumulative Format. Empty denominators are null and break lines. Lines
  between observed dates are visual guides, not invented daily observations.
  Tooltips expose percentages with at most two decimals and exact denominator counts.
  Average-copy and percentage formatting throughout the UI uses at most two
  decimals; stored values and internal calculations retain their existing precision.
  No change statistic is currently presented; any future change must be percentage
  points, not relative percentage change.

Overall states distinguish observed zero, no evidence, mapping failure, source
failure and unavailable Format. Archetypes/associations add insufficient-sample
states. A failed refresh with previous usable evidence retains observed statistics
with a prominent stale/incomplete-source warning.

## API / UI

`GET /api/v1/competitive/cards/{printing_id}?window=30&source=limitless-main&trend=true`
resolves the printing to its existing functional identity. Defaults are 30D and
main Limitless. `trend=false` omits trend points for hover. Unsupported sources or
windows return 422; missing printings return 404; damaged storage returns 503.
Pydantic response models and `schema_version=1` define the snapshot-independent
contract. GET requests do not initialize storage, scrape or call AI.

Library Gallery/List alone opt into the popup: 1,000 ms intentional pointer delay,
cancel on early exit, 180 ms exit grace, and pointer transfer into the popup keeps
it open. Scrolling/resizing dismisses it. Collection and variation tiles do not
opt in. Card Detail artwork is unchanged and still click-to-enlarge.

Card Detail appends one vertically scrolling research dashboard after the existing
details/variations. Four series share one graph, with distinct colors/dashes,
legend toggles, native point titles and focus-accessible sample readouts.

QA Fix Pass #1 places the Variations toggle directly below artwork ownership
controls. Its expanded grid remains full-width before Research, with the existing
quantity/finish behavior. Research section order is Overview, Copy Distribution,
Usage Trend, Archetypes, Associated Cards, Evidence/Dataset.

Associated Card names expose a separate reading preview on hover or keyboard
focus. The API supplies a deterministic representative printing and allowlisted
TCGdex high-resolution image URL from the same functional identity. The image
loads only when the preview opens. No additional statistics request or navigation
occurs. Missing/failed artwork displays an unavailable message. The primary Card
Detail artwork component and Library analytics hover behavior are unchanged.

## Known limitations

This is a cached published-list sample, not a tournament census or all entrants.
Publication selection and mapping coverage can bias it. Format evidence may be
partial until the operator ingests far enough back to the explicit start. Evidence
panels show the contributing events so that scope is inspectable. A bounded refresh
does not remove older cached events; window selection controls eligibility.

HTML is an upstream dependency, not a guaranteed API. Fixtures and validation
detect structural failures, but source semantic changes still require maintenance.
The command stops at the first failed event; later events need a successful retry.
Statistics are computed from local normalized SQLite evidence, without materialized
snapshots or production-scale caching. Manual remapping is needed after card sync.
The initial three-event live validation is 734/734 mapped published lists; broader
historical coverage has not been claimed.

## Mike's manual QA matrix

### Green — wired, verify before certification

- [ ] Ingest main Limitless; verify source URLs, timestamps and tournament/list counts.
- [ ] Compare a card's usage, copies, distribution and both archetype denominators
      with the cached evidence; verify 14 versus 15 archetype lists and rare usage.
- [ ] Check 30D default and 7D/30D/90D/Format controls. Without format configuration,
      confirm unavailable state; with an explicit start, confirm cumulative evidence.
- [ ] Gallery and List: leave before one second, wait a full second, cross into popup,
      leave both; verify top five, compact metrics, source and exclusion explanation.
- [ ] Click a card normally; scroll all six research sections without analytics tabs.
- [ ] Verify all four chart series together, legend toggles and percent/sample tooltip.
- [ ] Exercise zero usage, empty evidence, unmapped evidence and a failed ingestion.
- [ ] Regression: collection quantities/finishes, Library preferred artwork, filters,
      pagination and history retain Phase 1–3 behavior. Card Detail artwork has no
      competitive/magnification hover and click still opens the current artwork.

### Yellow — deliberately partial

- [ ] Stable source-aware API works over dynamic local calculations; production
      precomputation remains deferred.
- [ ] Additional sources are architecturally isolated but not enabled.
- [ ] Review documented deterministic association safeguards against broader samples.

### White — not wired

- [ ] No Play! Limitless statistics, archetype/decklist workspace, Deck Builder,
      Agent/AI interpretation, tournament weighting or custom date picker.

### Frozen

- [ ] Phase 1–3 collection/variation identities and Card Detail artwork interaction.

**Mike performs manual certification. Automated passes do not certify Phase 4.**
