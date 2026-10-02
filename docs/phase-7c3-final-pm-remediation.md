# Phase 7C.3 final PM remediation

Branch: `phase7c3-alternative-card-research`.
Verified clean starting SHA: `10300cf9ab9e306749da3a587743791e108958e0`.
Ending SHA: the single commit containing this report, supplied in the final handoff.

## Numeric diagnosis

PM's historical diagnostic establishes `unsupported_numeric_card_claim`, `facts[1].text`, clause 0, with Coalossal evidence `ev-pool-7fbabe85eaf68085a28fdf9b`. The actual rejected sentence was not retained. Its exact wording and which number triggered rejection cannot be recovered from those diagnostics. No historical prose is fabricated here.

The locally established defect is that the checker searched for every numeral in serialized source JSON. A cost array records Energy symbols, not a numeral for each symbol count. This supported synthetic claim reproduced the rejection on the frozen Coalossal packet:

> Coalossal's Cragalanche does 150 damage and requires 1 Fighting and 3 Colorless Energy.

The source contains `[Fighting, Colorless, Colorless, Colorless]`, 150 damage and a two-card discard effect. Literal `1` and `3` need not occur as standalone JSON numbers. Conversely, the old checker accepted “Coalossal has 150 HP” because 150 appeared in the damage field, although its HP is 180. Both behaviors were reproduced before editing.

The correction checks bounded known quantities against their own fields: HP, damage, total/type-specific Energy cost, explicit discard quantities, and coin counts. Number words are normalized; printed “the top card” supports one card. Structured cost arrays support total and symbol counts. Damage counters remain quantities in effect text rather than attack damage. Unsupported or ambiguous values still reject; missing attack damage is not invented as zero. Unknown wording retains conservative source-number checking. This remains bounded validation, not universal natural-language entailment or an executable mechanics engine.

Supported regressions include two-card mill, one-card mill, 150 damage, 180 HP, four total Energy, the mixed 1 Fighting/3 Colorless requirement, and two coin flips. Negative regressions include 150 HP borrowed from damage, 180 damage borrowed from HP, incorrect mixed costs, three-card mill, three coin flips, and another cited card's damage borrowed for Centiskorch.

## Synthesis and presentation

The pool-only provider prompt now asks for an early practical answer, supported comparisons and roles, explanation of why differences matter, and no repetition of facts in interpretation. Quantities, explicit conditions and attack requirements are permitted comparison axes. It contains no fixed card names/rankings. Mechanical differences do not establish tournament superiority or guaranteed synergy. Simple and flagship frozen packets accept an authored comparative fixture with citations; unsupported competitive comparisons still reject.

Normal card-pool answers now show cited card names as understated inline preview buttons. Repeated per-paragraph Evidence buttons are moved into one collapsed **Inspect supporting evidence** section, preserving the exact statement-to-reference mapping. Card-name click also opens the existing evidence viewer. Facts and qualified interpretation remain separate. Snapshot, provenance, omissions and hashes remain in the existing detailed evidence section.

Reused **AssociatedCardPreview**, its readable approximately 350px artwork popover, focus/hover handling, Escape dismissal, viewport positioning and unavailable-image state. No new card viewer or settings subsystem was built. Artwork is looked up lazily through the existing `loadDetail` helper using the exact printing from the submitted cited packet. No name guessed from model prose can initiate a lookup unless it matches cited evidence. Names not present in cited evidence remain plain text. The shared preview now stays open when lazily loaded artwork arrives. Clicking opens evidence; deeper card navigation was not added because the reused name-preview component did not have it.

This is artwork preview, not competitive analytics hover. Existing 500ms artwork-only competitive hover remains unchanged and passes its tests. Hover/focus does not resubmit research, change selected context or mutate the deck. Touch/keyboard users retain the button and expandable evidence access.

## Files changed

- `src/pokelab/card_pool_research.py`: numeric checks and comparison-clause scoping.
- `src/pokelab/agent_research.py`: pool synthesis wording only.
- `tests/test_card_pool_final_remediation.py`: 17 new deterministic regression cases using frozen real evidence.
- `web/src/ResearchCardText.tsx` and its test: cited-name matching and lazy reuse of existing preview.
- `web/src/AssociatedCardPreview.tsx`: optional evidence-click callback and preservation during image arrival.
- `web/src/ResearchAgent.tsx`: consolidated citation inspection and contextual section wording.
- `web/src/index.css`: inline-name presentation scoped to Research.
- `web/src/CardPoolResearch.test.tsx`: collapsed evidence access.
- `web/integration/card-pool-research.spec.ts`: responsive preview, image loading, citations and no duplicate call.
- This report.

Retrieval, taxonomy, ranking, candidate/component caps, projection, Answer schema, citation membership, provider transport, price policy and source databases were not changed. Frozen 7A/7B artifacts and prior qualification results remain untouched. Historical card-pool envelope hash regressions still pass.

## Verification

Focused backend: **76 passed**, 14.12 s. The initial development run caught a damage-counter phrase being interpreted as attack damage; the bounded unit matcher was corrected before the final gate.

Focused frontend: **39 passed**; TypeScript passed.

One final relevant network-blocked backend gate: **393 passed**, 39.81 s, two existing dependency deprecation warnings. Files: final remediation, previous remediation, card pool, selected-card research, answer contract, deck-agent research, PM correction/limitation regressions, deck research, alternative retrieval and mechanics discovery.

Final relevant frontend: **46 passed** across five files, 2.69 s; TypeScript passed. Browser: **3 passed**, 4.4 s, including 1440px and 900px layouts. Browser/API requests were mocked or local; external browser requests and backend socket connections were blocked. Browser artwork is an explicitly labelled synthetic test image; it verifies loading, size and positioning, not an actual card's printed text. The 900px screenshot was visually inspected, then inline button styling was refined and the focused browser checks repeated. No broad backend gate was repeated.

Commands from the repository root (Python environment: `C:/Users/Mike/Documents/pokemon-tcg-lab/.venv/Scripts/python.exe`, `PYTHONPATH=src`):

```powershell
$testTemp=Join-Path (Get-Location) ('.cache/pool-final-focused-'+[guid]::NewGuid().ToString('N'))
& 'C:/Users/Mike/Documents/pokemon-tcg-lab/.venv/Scripts/python.exe' -m pytest -q tests/test_card_pool_final_remediation.py tests/test_card_pool_remediation.py tests/test_card_pool_research.py --basetemp $testTemp
```

The final gate used `pytest.main` with `-q`, a unique `.cache/pool-final-gate-*` basetemp, and the above 11 test modules. Before pytest, both `socket.socket.connect` and `connect_ex` were replaced with a guard allowing only loopback and raising for external addresses, as in the previous remediation report.

From `web`:

```powershell
npm test -- src/ResearchCardText.test.tsx src/CardPoolResearch.test.tsx src/ResearchAgent.test.tsx src/DeckResearchAgent.test.tsx src/Competitive.test.tsx
npm run typecheck
$env:POKELAB_TEST_PYTHON='C:/Users/Mike/Documents/pokemon-tcg-lab/.venv/Scripts/python.exe'
$env:TCG_CARDS_DB_PATH='C:/Users/Mike/Documents/pokemon-tcg-lab/data/cards.sqlite3'
$env:NO_UPDATE_NOTIFIER='1'
npm run test:integration -- integration/card-pool-research.spec.ts
```

`git diff --check` passed. Zero live provider calls. No merge, tag, certification, main modification or Phase 7D work.

## PM handoff

**READY FOR PM LIVE QA.** Actual provider prose consistency remains a PM live-QA judgment; deterministic fixtures prove supported comparisons can pass but cannot guarantee every future response. Historical rejected wording remains unknown. Complex numeric/conditional prose may still be conservatively rejected. Tournament evidence is still absent. Preview artwork availability depends on the existing local card/image service.

Use the existing provider environment and restart command; no credential or model changes are needed:

```powershell
Set-Location 'C:\Users\Mike\Documents\Codex\2026-09-25\referenced-chatgpt-conversation-this-is-an\work\phase5'
.\scripts\Start-Phase5-QA.ps1 -Action Restart -SourceRepository 'C:\Users\Mike\Documents\pokemon-tcg-lab' -ApiPort 8003 -WebPort 5175 -PhaseLabel 'Phase 7C.3 final PM remediation'
Invoke-RestMethod 'http://127.0.0.1:8003/api/v1/agent/status' | ConvertTo-Json -Depth 5
```

After PM authorizes submissions, test the simple opponent-mill and flagship Standard/tournament mill questions. Check grounded comparisons, nonrepetitive synthesis, competitive qualification, inline card-name hover/focus, click-to-evidence and the collapsed supporting evidence section. No automatic retry or extra provider submission occurs from inspecting evidence.
