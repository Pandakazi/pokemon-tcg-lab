# PM-reviewed qualification — Nemotron / ultra-ball-v1 / suite v2

Preserved from Mike's explicit PM review. Metrics and conclusions below are
PM-reported; this recording step did not repeat inference or reconstruct output.

- Model: `nvidia/nemotron-3-super-120b-a12b:free`
- Gateway: OpenRouter
- Suite: `pokelab-qualification-v2` (quality qualification, 4096 output tokens)
- Case: `ultra-ball-v1`
- Grounding: PASS
- Evidence references / citation entailment: PASS
- Rules-authority boundary: PASS
- Unsupported claims: none identified
- Hallucinations: none identified
- Usefulness: GOOD
- Overall qualification: PASS
- Latency: 25,026 ms
- Input tokens: 4,824
- Output tokens: 2,588
- Reasoning tokens: 1,968
- Finish reason: stop
- Actual provider-reported cost: $0.00

PM confirms the answer distinguishes REVIEWED from INSUFFICIENT_INFORMATION,
identifies profile-only scope, preserves execution_authorized=false, accurately
reports competitive/deck/ownership facts and does not elevate cached empirical
evidence into rules authority.

Benchmark observation: v1 OUTPUT_TOKEN_LIMIT_REACHED is consistent with v2's
reasoning-token demand. PM finds the final answer reasonably concise; the larger
total output budget substantially accommodates internal reasoning. This does not
establish v1's missing reasoning breakdown or retroactively qualify v1. Reported
reasoning tokens are not added again to total output tokens.

- V2 configuration hash: `89dc98941ecc34d707cb9e63e8079e9ae2b3325ca5d14ca7d5dfb0b5b0e14323`
- V2 suite hash: `ccb078a574f14c42b74ff07ea9993412009cf4866214c1be02b4bf8e621c4ee2`
- Input hash: `389165b46a93ce34ea62853b5d49beeaf7c45c4875a16bbcfb8fb46631719432`
- Packet hash: `a98e533dc169fa6d7aa559181622ade13d11508c0b87906ef349b00491eaac3e`

This is a case/suite-specific PM PASS, not general provider reliability or Phase
7B certification. V1 remains NOT_EVALUATED / OUTPUT_TOKEN_LIMIT_REACHED. No new
live calls, case changes, merge, certification or Phase 7C implementation.
