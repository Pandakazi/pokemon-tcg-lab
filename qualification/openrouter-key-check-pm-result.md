# PM diagnostic result — OpenRouter key check PASS

Recorded from Mike's report of the authorized non-inference `/api/v1/key` check
in the same PM PowerShell session containing `POKELAB_OPENROUTER_API_KEY`.
This is a PM-reported diagnostic, not an independently repeated request.

- Authentication: succeeded
- is_management_key: false
- is_provisioning_key: false
- limit: 100
- limit_remaining: 100
- usage: 0
- usage_daily: 0
- usage_weekly: 0
- usage_monthly: 0
- is_free_tier: true
- Expiration: 2027-03-25

No credential, key identifier or raw response is recorded. The limit is the
reported key spending cap, not a claim of prepaid balance or free-model capacity.

PM conclusion accepted: shared connectivity, credential recognition and
account-level key authentication worked in that session. Historical Qwen and
Nemotron inference attempts remain NOT_EVALUATED. This diagnostic does not prove
model-specific availability, current provider capacity or remaining free-model
request quota, and does not establish the historical failure causes.

## Readiness for a separately authorized Nemotron retry

Corrected transport commit: `aa7e44ff9901d2cdac77f8f2a92cf86bd9e56604`.
Its documented 107 network-blocked tests passed. The transport is ready for one
PM-authorized OpenRouter-only retry of
`nvidia/nemotron-3-super-120b-a12b:free`, with no success guarantee.

The frozen packet/question/system/output contracts and scoring remain unchanged.
Input hash: `389165b46a93ce34ea62853b5d49beeaf7c45c4875a16bbcfb8fb46631719432`.
Preserve explicit model selection, serial execution, zero prompt/completion/request
price ceilings, no fallback, no automatic retry and secret-safe diagnostics.
Use the same PM session's `POKELAB_OPENROUTER_API_KEY`; no credential change is
required by this result. This readiness statement is not authorization to run.

This recording step changes documentation only and makes zero network/inference
calls. No model switch, merge, certification or Phase 7C work. STOP for PM.
