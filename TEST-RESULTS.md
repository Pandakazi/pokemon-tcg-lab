# Release verification — 0.1.1

## Post-Phase-6 — Deck Builder integration PM acceptance closeout

Mike manually passed and accepted Copy to Deck Builder and Deck Tray List/Gallery.
Base: `348a6968ebc5b25e49ac9ea82b77379a40fede25`.
Accepted Copy commit: `8396d3230b1aa317cea5b2c58d6e6c9b031d8b2a`.
Accepted Gallery commit: `b098275afd2d6d15931d9b549aad586d65398aae`.
Tag: `phase-6-deckbuilder-integration-2026-09-25`.
The results below were already completed before acceptance; no broad suite rerun
or production change was performed for this documentation/Git closeout.

- 9 new backend copy tests passed; 42 existing research/deck/allocation boundary
  tests passed (51 cases across focused runs). Two existing dependency warnings.
- 10 Deck Builder/frontend component tests passed.
- 13 real-browser checks passed: four new copy checks, three research checks and
  six existing Deck Builder checks. Mutation checks used isolated databases.
- TypeScript and production build passed.
- Copy fresh runtime verified schema 2 / revision 118.
- Gallery: 10 frontend tests, five targeted browser checks and copy-to-Gallery
  artwork verification passed; TypeScript/build passed. Frontend-only; permanent
  QA workspace preserved at schema 2 / revision 129. PM manual QA passed both features.
- Coverage includes preferred alternate printing/reverse finish, atomic rollback
  after writes, faithful invalid tournament copying, dirty/stale guards, source and
  ownership preservation, copied-deck reload/editing, and incomplete evidence refusal.

See [copy operation, safeguards and PM QA steps](docs/research-copy.md).
The certification records below remain historical and unchanged.

## September 25, 2026 — Phase 6 PM certification closeout

Status: **Phase 6 — Archetypes & Decklist Research ✅ CERTIFIED** by Mike.
PM manual QA: **PASS**. Accepted implementation commit:
`203f9cab0e2470ce82b97598113b3f3c2a47834a` on `phase6-archetype-research`,
based on certified Phase 5 `82df554`. Tag: `phase-6-certified-2026-09-25`.
This closeout changes documentation only; results below are the final accepted
pre-certification runs, not newly rerun suites.

- Full backend regression: **239 passed**, two existing upstream dependency warnings.
- Full frontend component regression: **70 passed** across six files.
- Full browser regression: **32 passed**, including the real Card → Archetype →
  Tournament Deck → Card → back research loop, URL/reload/context preservation,
  sparse evidence, unavailable Format, and an unmapped source fixture.
- TypeScript checking and production Vite build: **passed**.
- Fresh runtime: **schema 2 / revision 118 verified**, preserved active/saved decks,
  collection and source data; PM manually accepted the research experience.
- Real cached Dragapult evidence: 159 mapped entrants across three events, 67 core
  functional cards; deterministic validated 60-card composite (19 Pokémon,
  33 Trainers, 8 Energy). No ingestion or AI calls.
- Browser tests use isolated test databases; permanent PM QA data is never used
  for mutation tests. Fresh-runtime read-only verification is recorded separately
  in `.cache/manual-qa/phase6-runtime.json` after the final implementation commit.

See [Phase 6 architecture, algorithm and QA scope](docs/phase-6-research.md).
The certification entries below are historical and remain unchanged.

## September 25, 2026 — Phase 5 PM certification closeout

Mike explicitly certified Phase 5 Deck Builder, passed the Variation Family
correction, and accepted current finish visualization/persistent shimmer for this
milestone. Phases 1–5 are certified; Phase 6 — Archetypes & Decklist Research is next
and has not begun. Cosmetic polish remains non-blocking in the README backlog.

Accepted implementation history, in order:

- `165bce81801df7361d5f3ba9be5351dea48dceb1`: initial persistent Deck Builder.
- `69c39cacccfc20bc653e64944e22e8615b0bfbb6`: allocation/default/artwork/hover QA fixes.
- `977cee03cbb069bd04db9c0c966c7e416c99af56`: QA launcher checkout identification.
- `62046f35224ae4d9f88d1543ce0d3c4ebd21fa08`: centered, framed variation cards.
- `81a00bc0fe35720415fce824a2e85635452ab7a8`: compact variation polish and background preferred printing.
- `ea135c401faea75e1567322b3135c3f9fc15e24b`: conservative Variation Family discovery.
- `de066ea087e21873f94b917321c308d0b1eca5a2`: reusable exact-finish visualization.
- `e87631427d6b46ae3731cdc77941f350a41df4d8`: stronger static/pointer finish light.
- `3fc3b8d9b9ce40f292318f8d15c65ef736be0e2d`: persistent staggered shimmer.

The final shimmer pass passed production typecheck/build, 11 focused component
tests and four real-browser checks, including reduced motion, touch, pointer
return, navigation, enlargement, multi-card rendering and image-only 500ms hover
coverage. The preceding family correction passed 25 new Python cases and 104
affected API/collection/deck boundary cases. These are recorded prior runs, not
tests newly rerun for documentation closeout.

The accepted QA runtime uses deck schema 2, revision 118, four functional entries
and two saved decks. Read-only verification confirmed unchanged deck/preferences,
collection and source data. Runtime/cache files and screenshots remain local-only.
The closeout verifies clean worktrees, accepted ancestry, documentation-only changes,
and preserved tags; it does not change behavior or rerun unrelated expensive suites.

The entries below are historical implementation-time records. Their original
pre-certification wording, schema 1 and earlier hover timing are not current status.
See [the certified Phase 5 architecture](docs/phase-5-deck-builder.md) for current behavior.

## September 25, 2026 — Initial Phase 5 Deck Builder implementation (historical)

Status: **READY FOR PM QA**, not certified. Baseline `22a229b` matches the
`phase-4-certified-2026-09-24` tag; historical entries below retain their original
pre-certification wording.

- Full Python regression: **186 passed** (172 existing + 14 Phase 5), with the
  same two upstream test-client deprecation warnings.
- Full frontend suite: **51 passed** (45 existing + 6 Phase 5).
- TypeScript and production build passed.
- Browser coverage: **17 distinct scenarios passed** (11 existing regressions
  and 6 Phase 5 scenarios). Initial new-test locator ambiguities were corrected;
  failed scenarios passed on rerun. Final affected persistence/dense checks were
  rerun after the unfinished-rename guard. No existing test was removed/weakened.
- Real local cache: **23,736 cards**, competitive evidence **734 eligible lists**
  observed in the retained research dashboard. No card synchronization/ingestion
  was initiated. Browser API tests disallow outbound card-data connections;
  artwork loads from the existing allowlisted asset service.
- Browser checks cover one-second hover, read-only ownership throughout Builder,
  queued deck edits, full research and navigation state, save failures, saved
  incomplete drafts, selected finish, real-artwork desktop layouts, 20-entry deck
  scrolling, keyboard enlargement, long names and restored gallery scroll.
- Manual-QA launcher Start and Restart verified on ports 8003/5175. Process command
  lines point to this checkout. A real unsaved draft survived an API/frontend
  restart, then the isolated QA workspace was returned to EMPTY. The frontend proxy
  reports deck schema version 1. The certified app's collection is not used for
  QA writes; the launcher uses a SQLite backup snapshot and separate deck database.

See [the completed QA Scope Matrix and limitations](docs/phase-5-deck-builder.md).

## September 24, 2026 — Phase 4 Manual QA Fix Pass #2

- Root cause reproduced at both port 8001 and the port-5173 frontend proxy: the
  Uvicorn process had started at 20:58:34, before Fix Pass #1. It still used the
  original 100-deck threshold and returned Associated Card rows without
  `printing_id`/`image_url`. The frontend had hot-reloaded; Python had not.
  No precomputed statistics path was found: aggregates are computed locally from
  normalized evidence, with only card-catalog metadata cached.
- One authoritative `ARCHETYPE_PREVALENCE_MIN_DECKS=15` is now exposed in the API
  as `archetype_prevalence_min_decks`; frontend explanatory text consumes it.
  Missing current contract fields produce a clear stale-API restart error rather
  than rendering misleading insufficient-sample or missing-artwork results.
- Preview resolution uses the existing canonical identity/catalog and shared
  Library representative ordering (release date, regulation, ID and Basic Energy
  image priority), selecting an eligible Standard printing with usable image
  metadata. Curated Basic Energy can reuse its existing Library presentation
  group for artwork without merging canonical identities or changing quantities.
- Full Python suite: **172 passed**, including **37 competitive tests**; two
  unchanged upstream test-client deprecation warnings. Frontend: **45 passed**.
  TypeScript/production build passed. Browser regression: **11 passed**.
- Explicit API coverage: 14 decks insufficient; 15 decks with zero or nonzero
  appearances; more than 15 decks with zero or nonzero appearances. Representative
  tests cover release-date ordering, eligible prints, missing images, Basic Energy
  presentation, unchanged exact-printing quantities, and no card/state writes.
- Fresh-process sanity check against the original 734-list Budew evidence:
  Dragapult Dusknoir 55/55=100%, Dragapult Blaziken 46/46=100%, N's Zoroark
  16/60=26.6667%, Slowking 9/56=16.0714%, Crustle 1/36=2.7778%, Mega Excadrill
  1/29=3.4483%; Festival Lead 0/17, Basic Box 0/65 and Dhelmise 0/22 all report
  observed 0%. Below-15 groups remain insufficient. Common associated cards return
  valid allowlisted high-resolution image URLs.

Restart the local API after Python changes; frontend hot reload alone is not a
backend deployment. Phase 4 remains **uncertified** pending Mike's manual QA.

## September 24, 2026 — Phase 4 Manual QA Fix Pass #1

- Python regression suite: **166 passed**, including **31 competitive tests**;
  two unchanged upstream test-client deprecation warnings.
- Frontend regression suite: **43 passed**. TypeScript and production build passed.
- Chromium browser regression suite: **11 passed**, including the existing Phase
  1–3 regressions and a new artwork-only Associated Card preview check.
- Added/updated assertions cover Variations next to primary ownership and outside
  Research; section order; simultaneous trend series independent of timeframe;
  explicit Format extent and historical observed dates; fallback 90-day extent;
  14/15 archetype threshold and ungated 3/734 field usage; singular/plural grammar;
  image metadata bound to functional identity; hover/focus artwork preview without
  analytics fetch or navigation; maximum two-decimal display in dashboard, popup
  and chart tooltip; unchanged Library one-second delay and primary artwork behavior.
- Read-only inspection of the original local evidence confirmed Worlds on
  **2026-08-28 (143 lists)** and Baltimore/Indonesia PBL on
  **2026-09-19 (559 + 32 lists)**. The two plotted dates are genuine. No additional
  evidence was ingested and no observations were manufactured.
- Association values, conservative ordering and minimum 5 A / 3 joint observations
  remain unchanged; the prevalence-only minimum is now 15 eligible archetype lists.
- Variations placement follows the QA intent: toggle under artwork ownership,
  expanded full-width chooser before Research. Collection/finish logic is untouched.
- Preview artwork depends on the existing TCGdex asset URL; failed/missing artwork
  shows an unavailable state. Format still needs explicit configuration.

**Not certified. Mike continues manual Phase 4 certification.**

## September 24, 2026 — Phase 4 Competitive Analytics

Implemented on `phase-4-competitive`, based on Phase 3 commit `411b78d`.
**Awaiting Mike's manual certification.**

- Full Python regression suite: **164 passed**, two existing Starlette/httpx/anyio
  deprecation warnings. Includes 29 Phase 4 parser, source separation, deterministic
  metric, threshold, normalization, provenance and API tests.
- Frontend: **39 passed**, including eight Phase 4 cases covering exact 1,000 ms
  delay, cancellation/180 ms grace, popup crossing, top five, window changes,
  four-series rendering, missing Format, zero usage and frozen artwork behavior.
- TypeScript validation and production build: **passed**.
- Full Chromium browser suite: **10 passed**, including all eight Phase 1–3
  regressions and two new Phase 4 tests. Backend external sockets are blocked;
  new browser assertions use deterministic intercepted analytics responses and
  test the local API source/default contract. Collection state is temporary.
- Real bounded main-Limitless ingestion: Baltimore **559/559**, Indonesia PBL
  **32/32**, Worlds 2026 **143/143** published lists mapped, **734 total**. No Play!
  Limitless evidence is used. All initial unresolved cards were newer basic Energy
  artwork; verified same-set basic Energy mapping resolved them without changing
  canonical identities. Live evidence is an ignored local database, not a test
  dependency or committed dataset.
- Visual QA inspected the chart rendering. Browser coverage confirms all six
  research sections remain reachable in the continuous detail scroll.
- Parser fixtures retain source URLs and byte hashes. Structural failures preserve
  event cache; source errors are visible. Shared list URLs retain distinct entrants.
- Implementation definitions, limitations, configuration, ingestion command and
  green/yellow/white/frozen manual QA checklist: `docs/phase-4-competitive.md`.

Limitations: local dynamic aggregation, bounded cached published-list population,
manual ingestion/remapping, explicit Format boundary required; no production
materialization or additional sources. No certification or mobile/macOS QA claim.

## September 24, 2026 — Phase 3 final PM QA cleanup

Phase 3 functionality passed PM QA; these final presentation changes await PM visual confirmation.

- Full Python suite: **135 passed** in 22.22 seconds; two unchanged upstream deprecation warnings.
- Frontend: **31 passed**; TypeScript validation and production build passed.
- Full real-data Chromium suite: **8 passed** in 48.3 seconds, with backend external connections blocked and isolated temporary ownership storage.
- Regression coverage verifies explicit finish choices without synthetic unspecified tiles, preserved/editable unassigned ownership, exact mutations, stable primary dimensions after variation selection, centered frame controls, embedded +50px hover without reflow, bounded four-column artwork, and Collection separators beneath ownership controls.
- Existing identity, Basic Energy, MCP, category/history, ownership persistence and artwork-preference regressions remain passing. Canonical identity and MCP implementation files are unchanged.
- Screenshot review covers primary framing, wide-screen variations and complete Collection rows. No mobile/macOS certification is claimed; upstream artwork can still use the existing unavailable-image fallback.
- No schema migration, ownership rewrite, artwork-group expansion or Phase 4 work.

See the updated [Phase 3 QA scope matrix and PM walkthrough](docs/phase-3-collection.md).

## September 24, 2026 — Phase 3 Collection & Variations

Phase 2 is PM-certified at `df02a1d`. This Phase 3 implementation awaits PM QA.

- Full Python suite: **133 passed** in 23.58 seconds. Two pre-existing upstream
  test-client deprecation warnings remain. Existing MCP, Qt, snapshot, card-data
  and Phase 2 behavior remain covered.
- Frontend: **29 passed**. TypeScript validation and Vite production build passed.
- Chromium real-data suite: **7 passed** in 43.3 seconds. The new acceptance flow
  uses real Ultra Ball printings and tests Gallery keyboard +/−, canonical rollup,
  exact Card Detail quantity, full-opacity variations, variation inspection,
  no preference mutation from inspection, hover/enlarge/Escape, Owned/Unowned,
  saved Library artwork, zero-quantity minus disabling, reload/new page persistence,
  exact Collection Gallery/List and return navigation. Earlier Phase 2 browser
  tests remain, including all eight Basic Energy images and category/history state.
- Backend tests cover exact quantity bounds and zero, concurrent atomic increments,
  restart persistence, rollup across printings/finishes, ownership plus existing
  filters, canonical variations and pagination, persisted/invalid preferences,
  read-only source bytes, one-time legacy migration, unsupported schema safety,
  state/cache path separation and the PM-approved Basic Energy Library rollup.
- Browser user state is isolated in a temporary ignored directory. PM ownership
  was not modified. Backend external connections stayed blocked; no browsing sync.
- Inspected rendered Collection list and Card Detail/Variations screenshots.
  Gallery artwork remains full-color regardless of ownership; magnification is
  confined to Card Detail. No mobile/macOS certification is claimed.
- No new runtime dependencies, no canonical-identity changes, no card-cache writes,
  no authentication/analytics/Agent/Conditions and no Phase 4 work.

See [Phase 3 contracts, storage migration, PM walkthrough and mandatory QA matrix](docs/phase-3-collection.md).

## September 24, 2026 — Basic Energy representative images

Diagnosis: all eight newest selected `mee-001` through `mee-008` records lacked
source image metadata. Date-only ranking displaced older legal image-bearing cards.
The Library now prefers usable allowlisted image metadata for recognized Basic
Energy only, then chooses the newest eligible printing. Standard legality and active
query filters are applied first. No eligible image means the correct newest card
keeps its fallback; Special Energy ranking and canonical identities are unchanged.

- 116 Python tests passed (two existing upstream warnings); 23 frontend tests,
  TypeScript and production build passed.
- Six real-data browser tests passed, including actual image decoding for each of
  the eight Basic Energy representatives, with backend external connections blocked.
- New regression verifies newest image-bearing selection, rejection of unsafe URLs,
  no fallback to illegal image-bearing cards, image-less fallback, unchanged Special
  Energy selection, exact detail IDs, stable IDs with image opt-out, and read-only DB.
- Selected cache IDs: Lightning `sv01-257`, Fighting `sv01-258`, Grass `sv02-278`,
  Water `sv02-279`, Fire `sv03-230`, Psychic `sv03.5-207`, Darkness `sv06.5-098`,
  Metal `sv06.5-099`. All eight decoded real TCGdex images in Chromium.
- Browsing uses stored metadata, not network availability probes. Asset-host outages
  can still produce the existing fallback. No sync, migration or image packaging.

## September 24, 2026 — final Phase 2 cleanup

- **115 Python tests**, **23 frontend tests**, **6 real-data Chromium tests** passed.
  Explicit TypeScript validation and production build passed. Python: 18.01 seconds;
  browser: 31.1 seconds. Two existing upstream Python deprecation warnings remain.
- Library-only Basic Energy identity merges historical/source variants by curated
  Energy type and selects the newest eligible Standard printing. Regression fixtures
  preserve canonical identity, distinct Special/ambiguous Energy, exact old detail
  lookup, MCP exact search and unchanged database bytes.
- Real cache/browser verification found exactly eight recognized Basic Energy
  representatives. Source-labeled Normal also includes 12 distinct non-Basic/ambiguous
  groups; these retain functional identity and source classification rather than
  being merged or silently corrected. Overall Energy totals: 27, Normal 20, Special 7.
- Ability Yes/No tested for neither, Yes, No, both, repeated values, invalid values,
  Stage/Type combinations, legacy shared URLs, group placement, pagination,
  category memory and browser reload. Detection remains structured and server-owned.
- Entire previous regression suites passed, including Gallery/List, search, history,
  keyboard, images, exact details, MCP, Qt and snapshot behavior. Browser backend
  outbound connections remain blocked. No upstream sync occurs during browsing.
- Updated QA scope matrix in [Phase 2 documentation](docs/phase-2-library.md).
  PM confirmed the preceding five QA fixes; this cleanup awaits final certification.
  No Phase 3 work and no canonical identity or collection-state changes.

## September 24, 2026 — Phase 2 QA fix pass

- Full Python suite: **114 passed** in 18.04 seconds; includes preserved MCP,
  snapshot, Qt and all new API regressions. Two existing upstream deprecation
  warnings remain. A fresh workspace `--basetemp` avoided a Windows permission
  error in pytest's default temporary directory; no application test was skipped.
- Frontend: **22 passed**. Added category-specific query/page restoration,
  consecutive repeated filter changes, Has Ability URL behavior and cumulative
  progress for full pages, partial final pages, small and empty result sets.
- Explicit TypeScript validation and production build passed.
- Real-data Chromium: **5 passed** in 26.1 seconds. Verified representative IDs
  against independently grouped SQLite records, decoded real images, Energy
  empty/Normal/Special/both, Supporter H/H+J, Ability text/kind, pagination,
  independent category queries, view/detail/keyboard and Back/Forward/reload flows.
  Backend non-loopback connections remained blocked; browsing did not synchronize.
- One earlier image decoding check timed out; the unchanged image assertion passed
  on the final full rerun. A narrow Ability query shrank to 22 representatives; the
  browser test now checks that partial page, then broadens the type family to test
  multi-page Basic + Ability results. It does not assume duplicate printings exist.
- Initial diagnosis: both the baseline code and running API already returned
  316 exact Energy printings without filters, 308 Normal, 8 Special; Supporter H
  returned 109 and H+J returned 143. The alleged SQL union defect was not reproduced.
  Explicit empty query entries are now normalized and client consecutive edits
  retain the latest query. Special Energy was on later ID-sorted pages.
- PM clarified representative behavior. Neither baseline browser used the existing
  functional identity for deduplication; PM explicitly approved reusing it and
  selecting the newest eligible Standard printing. Grouping now precedes Library
  count/pagination. Fixtures with 30 old reprints across every category prove that
  empty filters do not expand into printing spam, distinct gameplay stays separate,
  exact detail URLs remain valid, MCP stays exact, and SQLite remains unchanged.
- Current representative totals: Energy **73** (Normal **66**, Special **7**);
  Supporter H **36**, H+J **52**. Source differences remain distinct under the
  existing conservative identity rule; no new curated equivalence rules were added.
- Gallery/list/detail screenshots inspected. Current card-detail layout retained.
  No architecture change, credentials, collection writes or Phase 3 work.

The QA scope matrix and PM recheck steps are in [Phase 2 documentation](docs/phase-2-library.md).
This section records the latest QA pass; historical milestone results follow.

## Automated tests

35 tests passed on Windows with Python 3.12. Tests cover the existing seven tools, deck counts and legality limitations, version persistence/concurrent writes, real HTTP MCP requests, `/health`, the read-only check, launcher setup/repair, preserving settings, failed installation, occupied ports, already-running detection, malformed status files, and ZIP exclusions/line endings.

## Fresh ZIP installation

A clean archive was extracted into a new folder whose path contained spaces. It had no `.venv`, `.env`, cached installation state, or saved decks. The documented Windows command with the one-process execution-policy fallback was run under Windows PowerShell 5.1.26100.9444. The launcher discovered installed Python 3.13.15 through `py`.

Verified outcomes:

- Created `.venv`, downloaded/installed runtime dependencies and the project, and created `.env` automatically.
- Started the server and printed readiness only after its own `/health` endpoint answered.
- Port 8000 was occupied. The launcher used 8001, and the existing port owner was left running.
- `/health` reported version 0.1.1 and `/mcp` responded to a real MCP client.
- `pytest` was not installed in the fresh environment; ordinary startup and both checks succeeded without it.
- The beginner read-only check discovered all seven tools and retrieved Mimikyu.
- The full smoke test called all seven tools, validated a 60-card Bully Box demo, saved/read two versions, compared their exact changes, and analyzed the opening hand.
- Repeating the launcher did not reinstall healthy dependencies or start a duplicate. It reported the running address.
- Test processes were stopped after testing. Pre-existing processes and the original project's deck database were not modified by the clean-copy test.

This simulates a new user extracting the ZIP on an existing Windows host with Python installed; it is not a fresh Windows virtual machine or a test of Python's installer UI. No global package installation was used for the app.

## Distribution inspection

The ZIP builder includes only release source, tests, documentation, the two launchers, `.env.example`, and intentional card/deck samples. There is one `pokemon-tcg-lab/` top-level folder. No `.venv`, `.env`, saved-deck database, log, cache, temporary file, build output, or egg-info is included. ZIP CRC verification passed. PowerShell is packaged with CRLF; the Mac launcher uses LF and an executable permission bit. Commands contain normal underscores without Markdown escapes.

## Known limitations

- No Mac runtime was available. The Mac launcher was reviewed statically for built-in Bash compatibility, quoted paths, Python version detection, Python.org install locations, LF endings and Intel/Apple Silicon usage. Actual Mac execution, installer/Gatekeeper behavior, and architecture-specific dependency installation remain unverified.
- Python 3.11 and 3.14 were not runtime-tested. The declared supported range remains Python 3.11+ within Python 3.
- A port can be taken between checking and binding. The launcher reports the failed start and asks for a retry; it does not terminate another application.
- First installation, repair and changed requirements need internet access. Corporate package proxies, organization PowerShell policies and offline first installation were not end-to-end tested.
- ChatGPT connection guidance was checked against current official OpenAI documentation. No tunnel/account registration or end-to-end ChatGPT installation was performed.
- V0 remains a single-owner, loopback-only server without OAuth. The sample is a demo, and passing supported deck checks is not tournament certification. See README.md for validation scope.

## September 24, 2026 — web Phase 1

- 94 Python tests passed, including all 82 pre-pivot tests and 12 new API cases.
- 6 frontend tests passed: loading, real response rendering, unavailable database/retry,
  network failure, pagination, image fallback and malformed response handling.
- TypeScript type-check and Vite production build passed.
- 1 Chromium real-data integration test passed: compared 48 exact printings across
  two pages to synchronized SQLite; verified actual image decoding. Backend external
  socket connections were blocked. Browser TCGdex data-API calls were prohibited.
- Live cache contained 2,584 Standard Pokémon printings (a subset of 3,345 Standard
  printings across categories); source sync dated September 23, 2026.
- Two upstream Python test-client deprecation warnings; no test failures.
- npm audit reported zero vulnerabilities for the installed dependency lock.
- Windows tested; macOS run instructions not executed. Qt EXE remains uncertified
  with the preserved DLL startup failure. No later web phases implemented.

## September 24, 2026 — Phase 2 final validation

Phase 1 was manually certified by PM; Phase 2 awaits its own PM QA.

- Full Python suite: 109 passed in 19.97 seconds. Existing MCP, Qt and snapshot
  regressions remain included; two upstream test-client deprecation warnings remain.
- Frontend: 14 tests passed, including URL query/view preservation, direct detail,
  errors, multi-select request construction and immediate removal of stale card links.
- Explicit TypeScript validation and Vite production build passed.
- Chromium: all 3 integration tests passed in 15.5 seconds. Verified actual decoded
  card images, exact IDs against SQLite, categories, search, OR/AND filter selections,
  page 2, Gallery/List, keyboard Enter navigation, detail text, Back/Forward, direct
  reload and missing-printing handling. Backend external connections remained blocked.
- Read-only model audit: all 23,736 cached records validated against the detail model.
- Rendered filtered list and detail inspected; screenshots retained as local QA outputs.
- An earlier browser run exposed delayed router state and briefly stale result links.
  Query navigation now commits synchronously; previous-query links are hidden while
  loading. A regression test covers the stale-link case.
- One intermediate external-image check timed out; the final complete run decoded
  real images successfully. Image-host availability remains an external dependency.
- The usage-limit interruption declined build/test and browser commands before
  execution. Both were later executed successfully through normal approval review.
- No Phase 3 work, production deployment, live Agent call or mobile certification.
