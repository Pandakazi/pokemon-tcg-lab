# Release verification — 0.1.1

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
