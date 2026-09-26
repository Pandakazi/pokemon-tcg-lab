# PM-reviewed qualification — Gemini / ultra-ball-v1

Preserved from Mike's explicit PM review, September 26, 2026. These observations
and metrics are PM-reported; this preservation step did not rerun the model or
capture/reconstruct its response. This is acceptance of one case, not Phase 7B
certification or general model qualification across other cases.

- Provider: Gemini
- Model: `gemini-3.5-flash-lite`
- Case: `ultra-ball-v1`
- Frozen input hash: `389165b46a93ce34ea62853b5d49beeaf7c45c4875a16bbcfb8fb46631719432`
- Packet hash: `a98e533dc169fa6d7aa559181622ade13d11508c0b87906ef349b00491eaac3e`
- Grounding: PASS
- Evidence references: PASS
- Rules boundary: PASS
- Unsupported claims: none identified
- Hallucinations: none identified
- Usefulness: GOOD
- Overall: PASS
- Latency: 3199 ms
- Input: 4698 tokens
- Output: 728 tokens
- Reasoning tokens: not supplied in PM review
- Estimated cost: $0
- Actual provider-reported cost: unavailable (not asserted to be zero)

Minor non-failing presentation note: “aligns with the 4x+ distribution bracket”
is accurate but could state the comparison more explicitly.

No frozen case, question, system/output contract or scoring criteria changed.
No merge, certification or Phase 7C work is authorized by this case acceptance.

## Proposed next comparison — awaiting PM authorization

Exact OpenRouter model ID: `qwen/qwen3-next-80b-a3b-instruct:free`.
On September 26, 2026, the [official model listing](https://openrouter.ai/qwen/qwen3-next-80b-a3b-instruct:free)
lists this explicit free variant, zero prompt/completion token prices and a 262K
context window. It describes instruction-tuned, stable final-answer behavior
without thinking traces, suited to evidence-based retrieval/QA and formatting.

Comparison rationale: a different model family and serving provider tests whether
the same evidence grounding, citation discipline and rules boundary are preserved
outside Gemini. Its instruction-following focus fits the existing bounded JSON
contract without changing the frozen prompt or adding reasoning settings. This
is a comparison hypothesis, not an assertion that it will pass or beat Gemini.

Catalogue availability is confirmed; live endpoint/account capacity is untested
and free endpoints are rate-limited. Keep the existing zero-price caps, no paid
fallback, frozen inputs, serial execution and no access to Gemini's response.
No inference call was made to identify this candidate. Stop for PM authorization.
