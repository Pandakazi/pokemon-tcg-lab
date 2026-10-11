# Final pre-Ally regression gate

Release hygiene only. No production behavior changes, merge, tag, Analytics activation, certification, or Phase 7D work.

## Candidate and results

1. Starting branch: `phase7c5-concrete-deck-resolution`; HEAD: `fa59840feb4f64a1a90a1ccbe1a7049427a8ad64`.
2. Starting working tree: only `scripts/Start-Phase5-QA.ps1` modified. It is excluded from this commit and preserved byte-for-byte (SHA256 `BB800264286E41FB5C080A817D7136A69F1796C79568CABFD5548C6782B32356`).
3. Initial unfiltered backend gate: 1,401 passed, 9 failed, 2 deprecation warnings (293.17s).
4. All nine backend failures are B: obsolete synthetic legality fixtures. The current H/I/J Standard policy deliberately rejects rotated regulation marks even when a source's legal flag says true. These synthetic cards inherited mark A. Historical baseline documentation already records these same nine failures. Browser failures were also B: retired Agent controls/copy, collapsed proposal details, artwork preview expectations, responsive drawer interaction, and state-dependent Collection expectations.
5. Test corrections: give intended-current-Standard synthetic cards mark H; add A/G negative cases so stale source flags cannot bypass legality. Update existing browser assertions to current UI, preserving validation, immutability, allocation, request-count, and navigation checks. Use the actual checkout's Python modules, temporary deck/user/settings state, fixture conversation responses, and local artwork placeholders. No test exclusions or quarantines.
6. Production-code corrections: none; `src/` and `web/src/` unchanged.
7. Final unfiltered backend gate: 1,412 passed, 0 failed, 2 deprecation warnings (304.75s). Focused research/legality/index checks: 86 passed.
8. Full frontend suite: 140 passed across 13 files (13.10s).
9. TypeScript typecheck: PASS (`tsc --noEmit`, included in build); additional integration-spec/harness typecheck also PASS.
10. Production frontend build: PASS (Vite, 115 modules).
11. Final browser/integration gate: 52 passed (3.3m), one worker; no skips, filtering, or quarantines. An interrupted run caught an accidental test assertion replacement; it was restored, all four focused competitive checks passed, and this final full run passed.
12. Collection/Gallery: ownership editing/filtering, illustrator filtering/grouping, Library/Gallery layout, tray and artwork/finish previews covered by frontend/backend/browser tests.
13. Agent/deck: backend gate covers routing, generated state, consensus/variants/custom builds, novice resolution, proposals/apply/recount, evidence budgets, identity/legality, read-only behavior and export. Browser fixtures cover selected card/deck context, sources, truncation/failure handling, proposal details and deck allocations/reload.
14. Sync/settings: backend/frontend suites cover provider/settings storage and failure paths, Gemini-only UI, masked input, connection state, appearance persistence, competitive status/sync and cooldown; browser settings/status checks included. Analytics remains disabled.
15. Static checks: diff whitespace, tracked PowerShell parser checks, QA verification JavaScript syntax, storage/schema/index startup and migration tests PASS.
16. Secret/config sanity: tracked-file credential-pattern and private-config scan finds no matches; values are never printed. Browser provider is disconnected and outbound sockets/remote browser requests are blocked.
17. Final working tree target: only the original QA-launcher edit remains after the local candidate commit; its checksum is unchanged and it is excluded from staging.
18. Ending SHA: the local commit containing this report and test corrections; obtain with `git rev-parse HEAD`.
19. Limits: no live Gemini/Limitless requests; no fresh network sync or live model-quality claim. Browser artwork placeholders verify geometry/interactions, not CDN artwork pixel fidelity. Existing deprecation warnings are nonblocking.
20. Freeze readiness: READY TO FREEZE ALLY PREVIEW. All final gates passed; no remaining unexplained failures. Freeze itself was not performed.

## Backend failure IDs

- `tests/test_research.py::test_confidence_is_not_discovery_wall[1]`
- `tests/test_research.py::test_confidence_is_not_discovery_wall[4]`
- `tests/test_research.py::test_confidence_is_not_discovery_wall[14]`
- `tests/test_research.py::test_confidence_is_not_discovery_wall[15]`
- `tests/test_research.py::test_confidence_is_not_discovery_wall[20]`
- `tests/test_research.py::test_composite_determinism_60_observed_only_and_validator`
- `tests/test_research.py::test_invalid_candidate_does_not_hide_valid_candidate`
- `tests/test_research_copy.py::test_copy_exact_new_saved_preferred_unowned_and_immutable[tournament]`
- `tests/test_research_copy.py::test_copy_exact_new_saved_preferred_unowned_and_immutable[composite]`

## Reproduce

Run from this checkout with its Python dependencies and local cached cards/competitive databases available. These are machine-local paths, not committed credentials.

```powershell
Remove-Item Env:POKELAB_GEMINI_FREE_TIER_CONFIRMED -ErrorAction SilentlyContinue
& 'C:/Users/Mike/Documents/pokemon-tcg-lab/.venv/Scripts/python.exe' -m pytest tests -q --tb=short --basetemp=.cache/ally-backend-reproduce
npm --prefix web test
npm --prefix web run build
$env:POKELAB_TEST_PYTHON='C:/Users/Mike/Documents/pokemon-tcg-lab/.venv/Scripts/python.exe'
$env:TCG_CARDS_DB_PATH='C:/Users/Mike/Documents/pokemon-tcg-lab/data/cards.sqlite3'
$env:POKELAB_COMPETITIVE_DB_PATH='C:/Users/Mike/Documents/pokemon-tcg-lab/data/competitive.sqlite3'
npm --prefix web run test:integration
git diff --check
```

Changed files: this report, `tests/test_research.py`, `tests/serve_web_acceptance.py`, `web/playwright.config.ts`, the new shared `web/integration/fixtures.ts`, and existing integration specs importing that fixture. Substantive browser assertion updates are in Agent research, card-pool research, competitive, Deck Builder, proposal, allocation, finish, and preview-polish specs; remaining spec changes only adopt the offline fixture.
