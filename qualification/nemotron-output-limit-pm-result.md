# PM-established Nemotron termination cause

PM recovered the existing OpenRouter Activity metadata. This record preserves
the PM report; no provider request was made to retrieve or reproduce it here.

- Model: `nvidia/nemotron-3-super-120b-a12b:free`
- Serving provider: NVIDIA
- HTTP/provider response: 200
- Input tokens: 4,824
- Output tokens: exactly 1,200
- Finish reason: length
- Generation time: approximately 9.0 seconds
- Provider latency: 184 ms
- Throughput: 133.9 tokens/second
- Activity-reported cost: $0.00
- Fallbacks: none
- Previously reported total harness latency: 9340 ms (distinct from provider latency)

Cause established by PM evidence: the 1,200-output-token ceiling was reached
before normal completion. Correct category: OUTPUT_TOKEN_LIMIT_REACHED.
Qualification remains NOT_EVALUATED; no partial answer is retroactively graded.
This supersedes the unresolved termination diagnosis for this specific attempt.
Reasoning-token breakdown is not supplied, so reasoning exhaustion specifically
is not established. Missing metadata in the original report was parser loss, not
proof that no inference occurred or that no tokens were generated.

The harness now maps incomplete_or_blocked_output with safe finish reason length
(or the native max_tokens equivalent) to OUTPUT_TOKEN_LIMIT_REACHED. Other
termination states retain their categories. Existing safe finish/token metadata
is preserved; quality fields remain null and assessment is never invoked.

## Ceiling recommendation — proposed only, awaiting PM decision

Keep v1's recorded 1,200-token protocol and historical results intact. For further
cross-model quality qualification, recommend a separately versioned suite v2 with
a global 4,096-output-token ceiling for every model, rather than a Nemotron-only
exception. The current case requires structured evidence synthesis; a tight cap
can prevent assessment of that quality. Gemini's 728-token completion establishes
that Gemini fits v1, not that all model families can complete with the same token
accounting. Provider tokenizers and reasoning accounting differ; equal numeric
caps are a reproducible resource rule, not identical effective answer budgets.

4,096 is a proposed bounded engineering allowance, not an empirically established
minimum or guarantee of Nemotron completion. It raises potential latency and
free-tier quota consumption while retaining zero API price restrictions. Do not
change prompts, reasoning settings or output requirements to favor any model.

If PM chooses v2, rerun Gemini and each selected comparison under the same revised
protocol after authorization. Do not compare v1 Gemini latency/tokens against v2
Nemotron as a controlled performance comparison. Preserve v1 PASS/NOT_EVALUATED
records with their protocol labels. Include output ceiling and transport limits
in a versioned run-configuration hash: the existing frozen input hash covers
system/user messages, not the transport output-token limit. Any body/time caps
needed for v2 must also be explicit global protocol settings. No automatic growth
or retry after length termination. A v2 length termination remains NOT_EVALUATED.

If PM's intended question is instead which models can complete within 1,200
tokens, retain v1 for further runs and record this model as unable to complete
this attempt within that budget; still do not call its unassessed answer wrong.

No ceiling change is implemented. Current max_output remains 1200. Frozen case,
packet, question, system/output contracts and answer-scoring criteria are unchanged.
Input hash: `389165b46a93ce34ea62853b5d49beeaf7c45c4875a16bbcfb8fb46631719432`.
No network/live inference call, model switch, paid routing, retry/fallback, merge,
certification or 7C work. STOP for PM decision.
