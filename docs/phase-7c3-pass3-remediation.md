# Phase 7C.3 Pass 3 PM QA remediation

Starting branch: `phase7c3-alternative-card-research`.
Starting commit: `e94beaee5e43524ebd7c600abada1dbbe5279420` (clean).
The remediation commit containing this report is the ending commit; its exact SHA is reported in the handoff.

## Historical diagnosis and its limits

PM recovered one safe diagnostic: `condition=uncited_limitation_claim`, `json_parsed=true`, `schema_valid=true`.
It establishes that the shared limitation-hygiene guard rejected a factual-assertion form in limitations. It is not an evidence-ID membership error. The specific rejected text was intentionally not retained. PM did not identify which of the two requests supplied this diagnostic. Therefore the exact offending sentence and the individual reason for the other request remain unknown. Do not attribute this code conclusively to both, or conclude retrospectively whether the original sentence was a true claim or a guard false positive.

The production path is provider text → `Answer.model_validate_json` → citation membership → outcome/array rules → shared `research_grounding.violation` → pool-specific `violation` → accepted answer. The limitation check applies to all outcomes, including `unsupported_question`. Its exception becomes `invalid_answer_contract`, with `answer=null` and bounded diagnostics. The UI lacked labels for this condition and every pool-specific grounding condition, explaining the unhelpful “Detailed classification is unavailable” message.

Both exact historical envelopes were reconstructed locally, without inference, for 2026-10-02:

- Simple opponent-mill question: `e12ca2b923f1b1b1523b9e8d92c8df6b8c12ccbf14ab890cd8b075ade0f0afa9`.
- Flagship Standard/tournament mill question: `c11c463c60deaf422defe460d6d742d2015ef9d498403a8fd9ece090c8d501de`.

Their five candidates are Centiskorch, Coalossal, Cornerstone Mask Ogerpon, Crawdaunt and Deino. Each has addressable evidence, printed effect text and structured attack cost. The packets support a useful mechanical answer. They do not establish tournament strength, matchup plans or synergistic extra turns.

Separate local reproductions exposed three additional false rejections; these are **not established historical causes**:

- “Controlled Burn costs 1 Fire Energy” was mistaken for a recommendation of the catalog card named Fire Energy, outside projected candidates.
- “Controlled Burn costs 1 Energy” searched for the numeral in source JSON instead of using the one-element cost array.
- Two correctly cited sentences about Controlled Burn and Cragalanche applied each sentence's cost to both attacks.

## Correction and preserved boundaries

The pool prompt now explains the encoded field layout, containing-item citation targets, named cost claims, subject separation, supported mechanical relevance and epistemic limitations. Card/deck facts must remain in cited statements; unavailable tournament evidence does not prevent answering the mechanical portion. No card-specific conclusion is requested.

The pool cost guard validates explicit attack-cost operands against the structured cost arrays and any explicit Energy type. Only validated operands are excluded from the unrelated catalog-name/numeric checks. Other mentions of an unprovided Energy card still fail. Checks are scoped to explicit cited subjects per sentence/clause; ambiguous multi-attack cost assertions must agree with every named attack. A coordinating “but costs…” remains attached to its named attack; competitive qualifications are still checked separately across “but/however”. No unknown cost becomes zero/free.

The shared limitation guard, Answer schema, strict parser, citation membership, transport, execution gates and byte/token limits are unchanged. No invalid answer is repaired, partially exposed or retried. The service's existing secret quarantine still applies to diagnostics.

Safe diagnostics now display allowlisted reason codes and explanatory labels, plus bounded field/clause/count information for pool failures. API diagnostics include only already-supplied evidence IDs, not arbitrary rejected IDs, text or exception messages. Historical `uncited_limitation_claim` now has a useful UI label.

Evidence projection and Pass 2 retrieval/ranking did not change: no missing fields were needed for these answers. Candidate IDs remain unique and stable across serialization, match their content-derived IDs, and identify individual candidates. Components are traceable through each containing item's references; they are not independent citation targets. Source `ref-pool-*` IDs remain invalid answer citations. Budget pruning retains only used provenance references. Neither historical envelope hash changed.

## Files

- `src/pokelab/agent_research.py`: pool-only prompt clarification and bounded pool diagnostic forwarding.
- `src/pokelab/card_pool_research.py`: subject-scoped cost validation and safe diagnostics; builder unchanged.
- `web/src/ResearchAgent.tsx`: allowlisted diagnostic labels and bounded detail display.
- `web/src/ResearchAgent.test.tsx`: historical reason and pool diagnostic display/no-retry tests.
- `web/integration/card-pool-research.spec.ts`: mocked browser rejection/reason/no-answer check.
- `tests/fixtures/card_pool_pm_20261002.json`: reconstructed public local evidence; two historical packets plus an explicit Budew reference packet for the support example. Catalog names are test-only guard input, never provider payload.
- `tests/fixtures/card_pool_pm_answers.json`: authored synthetic direct-mill, direct-plus-support, flagship, invalid-ID and unsupported-competitive responses. These are not recovered provider answers.
- `tests/test_card_pool_remediation.py`: production assessment/service regressions, exact hashes, citation/provenance/budget invariants and negative cases.
- This report.

## Deterministic results and conversational quality

The simple and flagship packets both accept the golden answers through the production service with a fake transport. An accepted example opens:

> Centiskorch is a starting point for direct mill: its Controlled Burn costs 1 Fire Energy and discards the top 2 cards of your opponent's deck.

It then compares Coalossal's printed cost, explains why that distinction matters, and explicitly declines to infer tournament strength. The support fixture describes Budew's Item restriction as a different possible job from direct discard, without claiming proven synergy or guaranteed extra turns. It uses explicit reference context; no support candidate was invented or added to the historical packets.

These fixtures verify an acceptable conversational response is possible under the production contract. They are not evidence that the next live model answer will have this voice or depth.

- Simple opponent mill: accepted, grounded golden answer; exact historical hash preserved.
- Flagship tournament-play mill: accepted mechanical answer with natural uncertainty about tournament success; exact historical hash preserved.
- Self-mill: existing generalized service test passes; representation stays distinct from opponent mill.
- Budew/Tools: Tool intent preserved, Jamming Tower supplied, reference does not change query to Items.
- Damage-counter research: generalized service path passes.
- Unknown terminology: insufficient evidence, zero fake inference requests.
- Detailed Great Tusk versus Dragapult piloting: unsupported scope, zero fake inference requests.
- Invalid/missing/source citations, nonexistent active-deck reference, unsupported competitive strength, wrong costs/types/free claims, invented properties/cards and related-as-direct assertions: rejected.
- Recovered limitation reason: reproduced with clearly labelled authored prose through the service for both envelopes and both answered/unsupported outcomes. Epistemic creator-intent and tournament limitations remain accepted.

## Verification commands

Run from the repository root in PowerShell. All providers are fake; the final gate blocks non-loopback socket connections.

```powershell
$env:PYTHONPATH='src'
$testTemp=Join-Path (Get-Location) ('.cache/pool-remediation-'+[guid]::NewGuid().ToString('N'))
& 'C:/Users/Mike/Documents/pokemon-tcg-lab/.venv/Scripts/python.exe' -m pytest -q tests/test_card_pool_remediation.py tests/test_card_pool_research.py --basetemp $testTemp
```

Focused result: **59 passed**, 13.45 s, two existing dependency deprecation warnings. An earlier development run had four failures from splitting “but costs…” away from its attack; corrected before the successful focused run.

Single final relevant backend gate:

```powershell
$env:PYTHONPATH='src'
@'
import socket, uuid, pytest
from pathlib import Path
original = socket.socket.connect
def blocked(sock, address):
    if isinstance(address, tuple) and address[0] in ('127.0.0.1', '::1'):
        return original(sock, address)
    raise AssertionError('External network forbidden by final regression gate')
socket.socket.connect = blocked
socket.socket.connect_ex = blocked
files = ['test_card_pool_remediation.py', 'test_card_pool_research.py', 'test_agent_research.py', 'test_agent_research_contract.py', 'test_agent_deck_research.py', 'test_research_qa_corrections.py', 'test_research_limitation_retest.py', 'test_deck_research.py', 'test_alternative_retrieval.py', 'test_mechanics_discovery.py']
raise SystemExit(pytest.main(['-q', *['tests/'+f for f in files], '--basetemp', str(Path('.cache')/('pool-final-'+uuid.uuid4().hex))]))
'@ | & 'C:/Users/Mike/Documents/pokemon-tcg-lab/.venv/Scripts/python.exe' -
```

Result: **376 passed**, 39.95 s, two existing dependency deprecation warnings. No broad gate was repeated.

From `web`:

```powershell
npm test -- src/ResearchAgent.test.tsx src/CardPoolResearch.test.tsx src/DeckResearchAgent.test.tsx
npm run typecheck
$env:POKELAB_TEST_PYTHON='C:/Users/Mike/Documents/pokemon-tcg-lab/.venv/Scripts/python.exe'
$env:TCG_CARDS_DB_PATH='C:/Users/Mike/Documents/pokemon-tcg-lab/data/cards.sqlite3'
$env:NO_UPDATE_NOTIFIER='1'
npm run test:integration -- integration/card-pool-research.spec.ts
```

Frontend: **26 passed** across three files; TypeScript passed. Browser: **3 passed**, 4.3 s, covering the recovered diagnostic/no-answer/no-retry and existing 1440/900 px card-pool views. The initial browser startup and its diagnostic rerun timed out because the default card DB was absent (status 503); the explicit read-only card path above resolved startup. The first running browser pass found a missing version in the new mocked status response (Ask correctly stayed disabled); correcting that test fixture produced the final three passes. No product change was needed for either test setup issue.

`git diff --check` is part of final commit verification. Changed paths leave 7A/7B frozen artifacts, provider qualification records, Pass 1/2 sources/artifacts, main and existing tag objects untouched. No external provider/network request, merge, tag, certification or Phase 7D work is performed.

## PM retest

No runtime was restarted for PM and no credential/provider configuration change is required. Use the existing explicit $0 provider session:

```powershell
Set-Location 'C:\Users\Mike\Documents\Codex\2026-09-25\referenced-chatgpt-conversation-this-is-an\work\phase5'
.\scripts\Start-Phase5-QA.ps1 -Action Restart -SourceRepository 'C:\Users\Mike\Documents\pokemon-tcg-lab' -ApiPort 8003 -WebPort 5175 -PhaseLabel 'Phase 7C.3 Pass 3 remediation'
Invoke-RestMethod 'http://127.0.0.1:8003/api/v1/agent/status' | ConvertTo-Json -Depth 5
```

Verify availability, explicit provider/model and card-pool scope before Ask. With PM authorization, retest the simple and flagship questions in Standard card pool, no deck/reference. Inspect citations and limitation hygiene. If rejected, inspect Validation details and retain only the safe diagnostics. Never automatically retry. No live reliability claim is made from fake-provider tests; PM still assesses actual answer quality.

**READY FOR PM LIVE QA**, not certified. Remaining limits: historical rejected sentences are unavailable; one request's diagnostic is unassigned; bounded text guards are not universal entailment checking; ambiguous claims can still be safely rejected; competitive evidence is deliberately absent. Deterministic success establishes a working grounded path, not guaranteed future provider compliance.
