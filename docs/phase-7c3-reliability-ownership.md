# Phase 7C.3 reliability: deterministic facts and optional synthesis

Verified clean starting branch `phase7c3-alternative-card-research`, SHA `6b3e8e4647debdf9f5fff715830a8d57c9fa83b4`. Ending SHA is the single commit containing this report, supplied in the final handoff.

## Architecture

Card-pool research now uses `pokelab-card-pool-answer-v2` for provider output. It has five required fields: version, outcome, candidate evidence IDs, synthesis items, and optional limitation strings. Each synthesis item has text, evidence IDs and a required boolean. There is no provider factual-prose field. Extra fields, including attempted generated card data, fail schema validation.

The existing builder and evidence packet are unchanged. Before inference, the server validates the candidate records and their provenance references and makes transient typed views of their existing printed fields. This is not a database, migration, second card source, or new retrieval representation. Gemini receives the new response schema through the existing provider-neutral structured-output boundary; other providers receive the same explicit system contract.

The provider selects up to five supplied candidate IDs and explains them. The server resolves those IDs to its already-validated facts and returns source-owned card facts alongside accepted synthesis. The evidence envelope is still supplied unchanged to the provider. Its hash semantics, ranking, taxonomy, caps and source facts do not change.

The new frontend presents accepted synthesis first, then card names, printings, source-marked Standard status, component names, Energy symbols, supplied damage and exact printed effect text. Absent values remain absent; missing damage does not become zero. Existing card-name hover/focus and click-to-evidence behavior is reused. One collapsed supporting-evidence area maps statements and cards to their references; the existing detailed coverage/snapshot view retains debug metadata and an omission count.

Selected-card and deck research keep their existing Answer contract and generation path. The old pool prompt remains explicitly named LEGACY_POOL_SYSTEM for historical regression coverage; production card-pool calls use the v2 prompt. Frozen qualification records are untouched.

## Exact degradation boundary

All output structure and all candidate/citation references are validated before any item can be omitted. Unknown IDs hard-fail even in an optional synthesis item. Core selected IDs must uniquely identify supplied card-pool candidates, not provenance or reference-card records.

Each synthesis item is assessed atomically by the unchanged strict grounding checks. If an optional item fails, its entire text is omitted; no sentence repair, citation stripping or partial-clause salvage occurs. Independently valid items and deterministic selected facts remain. An item marked required failing any check hard-fails the entire answer. This flag denotes a conclusion necessary to the answer, not permission for unsupported competitive conclusions.

Optional limitation text is checked for uncited factual claims and the existing card-pool numeric/catalog/competitive boundaries. Failed items are omitted. A server-owned mechanical-research boundary always remains. Rejected prose is never returned or persisted. Omission diagnostics contain only field, index and bounded reason code.

Hard failures also include malformed JSON/schema, duplicate selected candidates, invalid outcome combinations, answered with no selected facts, synthesis without selected facts, unusable factual evidence/provenance, truncation, unsuccessful transport, secret quarantine and internal assessment exceptions. An internal error is not converted to a successful degraded answer. When all optional synthesis is removed, source-backed selected facts still provide the mechanically useful result; this is not arbitrary surviving model prose.

The sole provider call remains at the existing transport boundary. No retry, repair call, fallback, routing, new qualification or live inference was added.

## Proof and tests

The historical rejected sentence is unavailable. This pass addresses the architectural dependency on generated factual prose rather than claiming to reconstruct that sentence.

The five-card frozen opponent-mill packet produces five factual cards whose names, printings, Energy arrays, damage and printed effect text equal their source fields. Its hash remains `e12ca2b923f1b1b1523b9e8d92c8df6b8c12ccbf14ab890cd8b075ade0f0afa9`; both historical envelope/hash regressions pass.

Service tests supply a valid multi-card comparison plus an outside-card claim, invented 999 HP, or a proven-tournament-staple claim. Optional invalid items are absent from the entire returned response while five facts and the valid comparison remain; required versions hard-fail. An uncited factual limitation and an unsupported competitive limitation are omitted. Unknown candidate/citation IDs, empty citations, injected facts, obsolete provider schema and invalid core outcome hard-fail. Every one-call service test asserts exactly one fake provider request. An unusable provenance test asserts zero requests; an internal-exception test asserts no degraded success.

Focused backend run initially passed 115/116 with one test fixture using the wrong fake response class; after correcting that fixture, all 19 new ownership tests passed in 6.67 seconds. The unchanged surrounding tests were then included in the single final gate.

Single final relevant backend gate: **433 passed**, 44.08 seconds, two existing dependency deprecation warnings. It covered 13 modules: the new ownership contract; numeric interpretation; both prior remediations; card-pool service; selected-card research and contracts; deck-agent research; QA and limitation regressions; deck research; retrieval; mechanics. External socket connections were blocked before pytest, with loopback allowed for test infrastructure. Providers were fake.

Frontend: **30 passed**, four relevant files, 2.60 seconds; TypeScript passed. Browser: **3 passed**, 5.4 seconds at 1440/900px with mocked API/artwork and blocked external requests. Tests cover synthesis-first display, all five factual cards even with no surviving synthesis, missing damage, hover, hidden citations, inspection and no extra research submission. The responsive screenshot was visually inspected. One development assertion initially matched both normal text and its collapsed evidence copy; it was corrected without changing product behavior.

Focused backend command used the existing canonical Python environment, `PYTHONPATH=src`, and unique cache basetemp:

```powershell
python -m pytest -q tests/test_card_pool_answer.py tests/test_card_pool_research.py tests/test_card_pool_remediation.py tests/test_card_pool_final_remediation.py tests/test_card_pool_interpretation.py --basetemp $testTemp
```

From `web`:

```powershell
npm test -- src/CardPoolResearch.test.tsx src/ResearchCardText.test.tsx src/ResearchAgent.test.tsx src/DeckResearchAgent.test.tsx
npm run typecheck
$env:POKELAB_TEST_PYTHON='C:/Users/Mike/Documents/pokemon-tcg-lab/.venv/Scripts/python.exe'
$env:TCG_CARDS_DB_PATH='C:/Users/Mike/Documents/pokemon-tcg-lab/data/cards.sqlite3'
$env:NO_UPDATE_NOTIFIER='1'
npm run test:integration -- integration/card-pool-research.spec.ts
```

## Changed files

- `src/pokelab/card_pool_answer.py`: scoped provider schema/prompt, deterministic fact views, assessment/degradation.
- `src/pokelab/agent_research.py`: pool-only dispatch and safe diagnostics; non-pool contract retained.
- `tests/test_card_pool_answer.py`: new ownership, hard-failure, no-leak and one-call tests.
- `tests/test_card_pool_research.py`, `tests/test_card_pool_remediation.py`: test-only v2 adaptation of old authored service fixtures; strict historical assessor coverage retained.
- `web/src/ResearchAgent.tsx`: synthesis-first deterministic factual display and inspectable evidence.
- `web/src/CardPoolResearch.test.tsx`, `web/integration/card-pool-research.spec.ts`: v2 UI/browser regressions.
- This report.

## PM handoff and limits

**READY FOR PM LIVE QA.** No live provider/network calls, main changes, merges, tags, certification, Phase 7D, data writes or new memory/routing features. Working-tree state and ending commit are in the final handoff.

Printed facts no longer depend on the model's prose. Free-form synthesis still uses the existing bounded grounding checks, which are not a universal semantic entailment proof. Some sound optional synthesis can still be omitted conservatively, and arbitrary hallucination detection is not mathematically guaranteed. Actual usefulness, coherence and provider compliance remain PM live-QA judgments. Items are instructed to stand independently; no conversational dependency model was added. Core integrity failures intentionally still produce no answer.

Use the existing explicit $0 provider configuration; no environment-variable changes are required. Restart the QA runtime, verify status, then after PM authorization ask the opponent-mill question. Inspect that source-owned cards appear, synthesis comes first when valid, and the debug omission count does not hide the factual result.

```powershell
Set-Location 'C:\Users\Mike\Documents\Codex\2026-09-25\referenced-chatgpt-conversation-this-is-an\work\phase5'
.\scripts\Start-Phase5-QA.ps1 -Action Restart -SourceRepository 'C:\Users\Mike\Documents\pokemon-tcg-lab' -ApiPort 8003 -WebPort 5175 -PhaseLabel 'Phase 7C.3 reliability ownership'
Invoke-RestMethod 'http://127.0.0.1:8003/api/v1/agent/status' | ConvertTo-Json -Depth 5
```
