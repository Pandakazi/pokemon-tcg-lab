# Gemini v2 output-contract failure — PM report and diagnostic limitation

PM reports Gemini `gemini-3.5-flash-lite` completed the v2 request normally:
status ok, finish reason stop, latency 3636 ms, input 4698 tokens, output 989
tokens, allowance 4096, estimated cost $0. Actual provider cost was not supplied.
Harness output: output_valid false, invalid_output_contract, qualification FAIL,
answer null. Nemotron v2 is ON HOLD. No further model is run by this task.

The v2 output naturally stopped at 989 tokens, compared with 728 in Gemini's
PM-reviewed v1 attempt. These are benchmark observations under different limits,
not a quality judgment or evidence that the increased ceiling caused this failure.
Gemini's historical v1 PASS is unchanged. No partial or invalid answer is graded
for grounding, citation entailment, rules authority, hallucinations or usefulness.

## What can be established locally

Transport ok means HTTP 200 JSON envelope parsing succeeded and yielded a
nonempty text response with accepted termination. This does NOT mean the text
itself parsed as the required answer JSON. The assessor used one broad except
for JSON syntax, duplicate-key rejection, Pydantic validation and later assessment.
It returned answer null and discarded both text and exception details. The CLI
also deliberately excluded Response.text from its report. The supplied report
therefore cannot reveal the original structural error.

- Exact field/condition: unrecoverable from the supplied report.
- Answer JSON parsing success: unknown (transport envelope parsing did succeed).
- Missing fields, wrong types, invalid values: unknown.
- Malformed citation structure: possible, not established. Well-formed but wrong
  evidence IDs normally reach the separate citation check instead of this error.
- Prose present versus wrapper failure: nonempty text existed; prose, markdown
  fences or an extra object wrapper cannot be established.
- Definitive model noncompliance versus harness defect: unknown. An unexpected
  internal assessment exception could produce the same old invalid_output_contract.

The harness has no persisted raw answer to replay. No retained original answer
was provided by PM. Do not reconstruct one from token counts or guess a field.
The original FAIL report is preserved as reported, with its cause unresolved.

## Small diagnostic correction, no acceptance/scoring change

Only failed assessments gain contract_diagnostics. The diagnostic independently
checks JSON syntax/duplicates and the exact existing Answer model, then emits:
JSON-parsed state, root kind, nonempty-text/fence-prefix indicators, summary-string
presence, schema-valid state and at most 12 errors. Paths contain only predefined
contract names; arbitrary keys and array indices become fixed placeholders.
Error categories are allowlisted (missing, wrong type, length bounds, extras,
etc.). Syntax errors expose line/column only. No text snippets, Pydantic messages,
input values, context, unknown keys, raw errors, evidence or response prose survive.
Known-secret quarantine applies before parsing and to serialized diagnostics.

A structurally valid answer caught by the outer exception yields
schema_valid_assessment_failed, distinguishing an assessment problem from schema
noncompliance. Nothing repairs fences, coerces new types, fills fields or changes
the frozen model. Existing quality/scoring paths and PM-review requirements are
untouched. Historical false quality fields must not be interpreted as actual
grounding/citation/rules assessments when output_valid was false.

Frozen input hash: `389165b46a93ce34ea62853b5d49beeaf7c45c4875a16bbcfb8fb46631719432`.
V2 configuration hash: `89dc98941ecc34d707cb9e63e8079e9ae2b3325ca5d14ca7d5dfb0b5b0e14323`.
V2 suite hash: `ccb078a574f14c42b74ff07ea9993412009cf4866214c1be02b4bf8e621c4ee2`.
No contract, suite settings, prompt, packet, model or allowance changes.

Next step is PM review of this limitation and diagnostic correction. An already
retained original completion, if PM has one locally, could be validated offline;
the current report alone is insufficient. Do not make a new live call to recover
it. No new network/inference calls, retries, model switches or Nemotron v2 run.
