# Phase 7B qualification status — pending PM decision

This registry summarizes PM-reviewed records; it does not infer grades for
unassessed output or combine benchmark dimensions. V1 = bounded synthesis at
1200 output tokens. V2 = quality qualification at 4096 output tokens.

## Current qualification matrix

- Gemini / gemini-3.5-flash-lite:
  - v1 PASS (PM): GOOD usefulness; 3199 ms; 4698 input / 728 output;
    reasoning count unavailable; estimated $0, actual cost unavailable.
  - v2 NOT_EVALUATED / INDETERMINATE_ASSESSMENT_FAILURE (PM disposition):
    normal stop; 3636 ms; 4698 input / 989 output; estimated $0;
    actual cost unavailable. No output-contract or model-quality conclusion.
- OpenRouter / nvidia/nemotron-3-super-120b-a12b:free:
  - v1 NOT_EVALUATED / OUTPUT_TOKEN_LIMIT_REACHED: stop reason length;
    9340 ms total; 4824 input / 1200 output; Activity cost $0.
    Earlier transport failure is separately NOT_EVALUATED.
  - v2 PASS (PM): GOOD usefulness; 25026 ms; 4824 input / 2588 output,
    including 1968 reported reasoning tokens; stop; actual cost $0.
- OpenRouter / qwen/qwen3-next-80b-a3b-instruct:free:
  - v1 NOT_EVALUATED / PRE_INFERENCE_TRANSPORT_CONFIGURATION (404, 395 ms).
  - v2 not run.
- OpenRouter / qwen/qwen3.8-27b:free:
  - v1 NOT_EVALUATED / PRE_INFERENCE_PROVIDER_RATE_LIMIT_OR_CAPACITY
    (429, 515 ms; specific source unestablished).
  - v2 not run.
- Native OpenAI, Anthropic, xAI, Mistral, DeepSeek: mocked transport coverage;
  live disabled by 7B zero-cost policy; neither suite live-qualified.
- Ollama/local: mocked transport coverage; no live run; neither suite qualified.

The initial legacy Gemini 2.5 Flash-Lite 404 is a historical transport failure,
not a quality grade for Gemini 3.5. OpenRouter key authentication PASS is account
diagnostic evidence, not inference qualification. No v2 PASS implies v1 PASS;
cross-version latency/output figures are not a controlled model ranking.

Sources: the PM review/disposition and attempt-diagnosis documents in this folder.
One case demonstrates capability on this case, not broad reliability or routing
fitness. No aggregate success rates or cheapest-capable ranking are inferred.

## Minimum remaining certification work — recommendation only

No additional live provider benchmark is required to close the authorized 7B
foundation scope: all eight providers have mocked coverage, Gemini has a reviewed
v1 result and Nemotron has a reviewed v2 result. Recommend PM explicitly accept
that bounded coverage; Gemini v2 and live Ollama can remain unqualified rather
than becoming certification blockers. This is a proposed acceptance boundary,
not a declaration that PM already certified 7B.

One local classification hardening remains advisable before certification:
assess currently retains FAIL/invalid_output_contract even when its new diagnostic
says schema_valid_assessment_failed. Separate actual JSON/schema rejection from
internal evaluator exceptions; internal assessment failure should be
NOT_EVALUATED / INDETERMINATE_ASSESSMENT_FAILURE with null quality fields. Preserve
genuine output-contract failures and existing scoring criteria. Cover this with
deterministic network-blocked tests; no model rerun is needed. Do not implement
it in this recording-only turn; obtain PM's scope decision first.

Then do only focused verification and evidence reconciliation for that fix,
preserving all suite/input/packet hashes and historical records. Existing latest
143-test validation is the baseline, not a request for broad UI/build work.
PM may then certify the explicitly bounded Phase 7B scope. Only after that
authorization, perform documentation/Git closeout and separately define/authorize
7C Research Mode around read-only evidence, citations, authority boundaries and
the qualified model/suite combinations. No routing intelligence, memory, write
actions, autonomous tools or provider expansion is implied by this recommendation.

Gemini v2 rerun, broader case coverage, repeatability/performance studies and live
Ollama are future optional qualification work, not part of this minimum closeout.
STOP for PM decision. No live call, merge, certification or 7C work occurred here.
