# Release verification — 0.1.1

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
