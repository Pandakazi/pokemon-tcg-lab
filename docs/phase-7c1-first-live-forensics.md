# Phase 7C.1 first live Research failure — offline findings

PM product QA result: FAIL (no usable answer). This is not a provider qualification
benchmark or a demonstrated model-quality failure. The one authorized submission
is consumed; no retry is authorized or performed by this investigation.

Implementation under review: `db5528ed649e8f9047de7f6d8cba7a6653b65b09`.

## Historical context

- Exact submitted question supplied by PM: `What is the point of budew in this deck?`
- Budew `me02.5-221`, holo; two exact allocated copies.
- Active deck: Dragapult — Rohit Potti — Regional Baltimore, MD.
- Workspace revision: 157; competitive window: 30 days.
- Configured provider/model, per PM: Gemini / `gemini-3.5-flash-lite`.
- Product result: `invalid_answer_contract`, answer null.
- No response-quality conclusion is inferred.

The request that actually ran differs in wording from the initial acceptance
example. Reconstruction uses PM's actual submitted wording, not the earlier one.

## Exact evidence reconstruction succeeded

Using the existing canonical card/competitive stores and QA collection/workspace
through the certified read-only snapshot adapters, with `as_of=2026-09-26`:

- Envelope hash: `991a77f9439050275916f1933a169b7a5d886a4b1874c601e3381d9a2eb819f1`
- Packet hash: `76bbdcbe190ac7b53b34025a7655cc774a35e97dc7939931e8cc2270d26e8df0`
- Canonical serialized envelope: 17,173 UTF-8 bytes.
- No unavailable evidence.
- Omissions: `archetypes:ranked-cap-3`, `associations:ranked-cap-5`,
  `partner-text:associated-active-cards-only;identity-order;cap-3`.

The exact hash confirms the deterministic input reconstruction. These omissions
are deliberate retrieval bounds. They do not themselves trip answer validation;
they can limit the evidence available for an answer. The supplement's cap notice
is emitted unconditionally and is not a precise count of discarded partner cards.

The local API access log has one Research POST with local HTTP status 200. This
status is the API's result envelope status, not proof of a successful product
answer. Logs have no contract diagnostic record. No log body or free-form provider
data is copied into this report.

## What can and cannot be established

At the accepted code's `invalid_answer_contract` return point, transport status
was `ok`, a normal finish reason (`stop` or `end_turn`) had passed, and assessment
raised either Pydantic `ValidationError` or product `ContractError`. Truncation,
transport failure and an absent completion reason have different return paths.

The server intentionally did not persist raw model output. Its rejected response
returned safe execution metadata and evidence, but neither the validation error
condition nor the output. The log does not retain token counts, latency or finish
reason. Those exact historical values are not recoverable from these files.

Consequently the exact historical condition is **unknown**, including:

1. JSON/schema failure: possible; parsing success was not retained.
2. Invalid/missing references: possible; neither the failing field nor ID class
   was retained. `ref-*` source IDs are not accepted as `ev-*` evidence citations.
3. Parser/normalization: direct JSON validation performs no fence stripping or
   repair, as the prompt requires. No historical wrapper is available to inspect.
4. Prompt/schema mismatch: the system prompt omits the validator's explicit
   maximum of 12 citations per statement and minimum one limitation, and does not
   explicitly spell out every whitespace rule. Its outcome example uses a
   pipe-separated placeholder rather than one valid enum example. These are
   clarity gaps, not proof of the failure's cause or an unsatisfiable contract.
5. Validator/classification bug: an internal Pydantic exception could be caught
   by the broad outer `ValidationError` handler and mislabeled as a model contract
   rejection. This is independently reproducible, but not established as the
   historical cause. A valid synthetic answer to the exact envelope passes.

Do not reinterpret this as a Gemini quality failure or grade missing content.

## Smallest fixed diff for PM review

Product-only changes in `agent_research.py` and focused tests:

- Return bounded `contract_diagnostics`: JSON parsed flag, schema valid flag,
  known root type, fence-prefix flag, known statement-text presence, canonical
  field paths and allowlisted error codes (at most eight issues).
- Distinguish schema failures from unknown evidence IDs. For unknown citations,
  return counts and the count using the `ref-` namespace, never submitted IDs.
- Preserve named semantic-shape conditions such as empty answer/statement,
  invalid limitations and unsupported outcome carrying claims.
- Wrap Pydantic failures only at the actual output-schema validation boundary.
  Internal assessment exceptions, including internal Pydantic errors or diagnostic
  failures, remain `internal_assessment_failure`, answer null, safe metadata intact.
- Retain no raw output, arbitrary keys/values, exception messages, hidden
  reasoning or credentials. Known credential forms remain quarantined.

The prompt, accepted output schema, evidence selection/budget, token ceiling,
provider configuration/transport, price policy and frozen 7A/7B artifacts are
unchanged. No schema relaxation, output repair, fallback or retry was added.
No running QA server was restarted or live request resubmitted.

Recommended follow-up for PM decision: retain this diagnostic/classification fix.
If subsequently authorized, separately clarify the product prompt with one valid
outcome example, all existing limits and an explicit evidence-ID versus source-ID
distinction. Such clarification should not be represented as a proven fix for
the historical failure. No additional live attempt is authorized here.

## Verification

- 200 targeted backend tests passed: 48 product Research tests, 26 certified 7A
  tests and 126 certified provider/qualification tests.
- New cases distinguish JSON syntax/fences, missing/wrong-type/invalid-enum fields,
  unknown fields, malformed/missing citations, source-ID versus evidence-ID errors,
  empty/blank limitations, whitespace statements, empty answers, unsupported
  claims, internal Pydantic exceptions and diagnostics failures.
- Eight synthetic cases were assessed against the exact reconstructed envelope:
  valid accepted; fenced JSON, malformed JSON, source-reference citation,
  unknown evidence ID, wrong field type, empty limitations and empty answer rejected.
- Reconstruction blocked all socket connections and did not call a provider.
  Tests use fake transports and block external network; Windows test event-loop
  initialization uses its internal loopback socket pair.
- Two existing dependency deprecation warnings remain.
- No historical answer was recovered or fabricated. No merge or certification.

## PM-approved fix verification

The diagnostic/classification fix was approved by PM without prompt or answer
acceptance changes. The exact reconstructed evidence is now retained as
`tests/fixtures/agent_research_budew_revision157.json`, not as a provider response.
Five repeatable fake-transport regressions use it, assert its envelope and packet
hashes, and distinguish valid answers, fenced JSON, schema rejection, source-ID
citation rejection and internal Pydantic failure. The historical rejected answer
remains unavailable; the fixture contains no answer or hidden reasoning.

Final verification for this approved pass:

- Complete Phase 7C.1 backend regression selection: **459 passed**, external socket
  connections blocked; two pre-existing dependency deprecation warnings.
- Focused Research frontend tests: **6 passed**, mocked fetch only.
- Browser tests not rerun: no UI/browser flow changed; the API adds optional bounded
  diagnostics while preserving the existing status/answer/execution fields.
- AST comparison against `db5528e` confirms the Research system prompt,
  Statement/Answer schemas and envelope/output budgets are unchanged.
- Certified 7A/7B source and `qualification/` compare unchanged against `665cf76`.
  Qualification tree: `1743d4acc87cb1a00188804aa6d55b1f085cfab0`.
  Frozen input/packet/v1/v2 configuration/suite hash regression assertions passed.
- `git diff --check` passed. No live provider calls or runtime restart performed.

Restart only when PM chooses to load this fix, from the same configured PowerShell
session used for QA. No Ask/retry is authorized by restarting:

```powershell
Set-Location 'C:\Users\Mike\Documents\Codex\2026-09-25\referenced-chatgpt-conversation-this-is-an\work\phase5'
.\scripts\Start-Phase5-QA.ps1 -Action Restart -SourceRepository 'C:\Users\Mike\Documents\pokemon-tcg-lab' -ApiPort 8003 -WebPort 5175 -PhaseLabel 'Phase 7C.1'
```

Hard-refresh `http://127.0.0.1:5175/deck-builder`. Compare the workspace endpoint's
`runtime_revision` with `git rev-parse HEAD`. Do not submit another Research request
without new PM authorization. No merge or certification is part of this fix.
