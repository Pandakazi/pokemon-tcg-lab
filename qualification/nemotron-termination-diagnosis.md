# Nemotron corrected-transport retry — termination diagnostics

PM report: `nvidia/nemotron-3-super-120b-a12b:free`, status
incomplete_or_blocked_output, latency 9340 ms, empty diagnostics, no recorded
model/finish/usage/answer. NOT_EVALUATED remains correct. No model-quality failure.

## Exact locally established path

In the cited aa7e44f transport there is exactly one return of that status. It
requires an HTTP 200 body that decoded as UTF-8 and parsed as JSON, passed secret
checks, and exposed a first choice/message accessible to the parser. No top-level
or first-choice OpenRouter error field was detected, and no tool/function call
was detected. The extracted finish_reason was not null, stop or end_turn.

Consequently, malformed/truncated JSON and missing/empty choices do not explain
this status: they take the generic exception path with stage diagnostics. A
detected provider error takes provider_error instead. Missing/empty content alone
with an accepted finish reason takes empty_output. Content may nevertheless have
been missing, empty or partial here because termination was tested before content.

The early return discarded the actual finish value, known HTTP status and any
model/provider/usage metadata that may have existed. Safe HTTP status and a
non-accepted finish value definitely existed; the other fields' presence cannot
be reconstructed. length, content_filter, error, another string or malformed
finish value remain distinguishable possibilities. A refusal cannot be proven.
9.34 seconds is time until the transport returned, not proof of inference or of
reasoning-token exhaustion. No raw historical response was retained.

This matches the official OpenRouter response/error contract already retrieved
in the preceding diagnosis. No fresh network documentation lookup was performed.
In particular, documented length termination can consume a reasoning budget,
but this is a possible explanation only, not a finding about this run.

## Minimal bounded correction

Incomplete/blocked and empty-output returns now retain fixed HTTP/stage fields,
allowlisted finish reasons (unknown values become other), content shape only,
refusal presence only, usage presence/shape, numeric input/output/reasoning counts
when valid, model equality to the requested ID, provider presence and known
Nvidia/ModelRun labels. Arbitrary provider IDs are omitted. Cost presence is
recorded without inferring actual cost. Missing counts remain null.

No partial answers, refusal text, arbitrary finish strings, provider prose,
prompts, evidence, raw response or credentials are retained. Existing response
quarantine precedes extraction; serialized metadata is checked again. These
statuses still bypass qualification scoring. The output contract is not relaxed.

121 network-blocked tests passed, including finish/content combinations, usage
retention, missing content/refusal presence, unknown finish suppression and secret
quarantine. Frozen case and contracts are unchanged; input hash verified by tests:
`389165b46a93ce34ea62853b5d49beeaf7c45c4875a16bbcfb8fb46631719432`.

## Cheapest next diagnostic action

Have PM inspect any already-retained OpenRouter activity entry for this exact
attempt for finish reason and usage, if available. This generates no new inference
tokens and may avoid another live attempt. Do not paste raw responses or secrets.
If no existing record exposes these fields, this run's discarded details cannot
be recovered locally; the new bounded diagnostics will distinguish the conditions
only during a future separately authorized attempt. No such attempt is made here.

No network/inference call, model change, price change, retry/fallback, merge,
certification or Phase 7C work. STOP for PM authorization.
