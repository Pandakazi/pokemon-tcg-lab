# Qualification suite v2 — ready, awaiting live authorization

PM approved a global 4,096-output-token quality-qualification benchmark. No live
v2 call has been made. v1 remains the default bounded-synthesis benchmark at 1,200
tokens. Existing result documents are unchanged and are not migrated to v2.

## Versioned comparison settings

`agent_qualification_config.py` supplies deterministic configuration objects.
Reports include the configuration and its SHA-256 digest, plus a combined suite
hash over configuration_hash, input_hash and packet_hash using the existing
canonical JSON digest. Each per-model record repeats the suite, benchmark
dimension, limit and hashes so an extracted row retains its comparison identity.

- v1 configuration hash: `4a10d3b66b6d264bb89f3e85cd64531d30d4351f61a1a4fdeaed3b7b373ff850`
- v1 suite hash: `f2146c6c90d6c6242c4cc861d3a9734f6a857ef9f493edf78869a557e8b4752d`
- v2 configuration hash: `89dc98941ecc34d707cb9e63e8079e9ae2b3325ca5d14ca7d5dfb0b5b0e14323`
- v2 suite hash: `ccb078a574f14c42b74ff07ea9993412009cf4866214c1be02b4bf8e621c4ee2`
- Shared frozen input hash: `389165b46a93ce34ea62853b5d49beeaf7c45c4875a16bbcfb8fb46631719432`
- Shared packet hash: `a98e533dc169fa6d7aa559181622ade13d11508c0b87906ef349b00491eaac3e`

The newly described v1 hashes label the unchanged v1 configuration; they are not
inserted into or used to rewrite historical reports. v2 differs only in suite
identity, benchmark dimension and output ceiling. Settings hashed include byte
caps, operation timeout, streaming/serial behavior, maximum batch size, no prior
answers, sampling/reasoning provider-default policy, scoring/output-contract
versions, live price policy, price ceilings, retries/fallbacks, proxy and redirects.
Model/provider identities remain explicit per record; the suite hash is common
across models. Hashes identify settings, not model determinism or live availability.

The 90-second per-operation timeout, 32 KiB input, 128 KiB response and 16 KiB text
limits are unchanged for both suites. A byte limit can still stop a response;
4096 is a requested output-token ceiling, not a guarantee of completion. Providers
may account for reasoning differently. No provider-specific reasoning adjustment,
temperature, output allowance or model-specific prompt has been added.

The system prompt retains its original v1 wording because it is the frozen input
contract, distinct from the suite execution version. Question, evidence, schema,
grounding/citation/rules checks, hallucination/usefulness review and PM acceptance
remain identical. length termination remains NOT_EVALUATED /
OUTPUT_TOKEN_LIMIT_REACHED. Partial output is never graded or retained as an answer.

## Prepared candidates and historical dimensions

Exactly two live v2 candidates are allowed, individually or serially:

1. Gemini: `gemini-3.5-flash-lite`
2. OpenRouter: `nvidia/nemotron-3-super-120b-a12b:free`

Other live v2 models and duplicate selections fail locally. Mocks can exercise all
eight transport formats at the same limit. Live execution still requires the
existing PM authorization gate and free-tier controls. No automatic routing,
retries/fallbacks, paid providers, model discovery or answer sharing.

Gemini currently has a PM-reviewed v1 PASS; v2 is not run. Nemotron's v1 attempt
remains NOT_EVALUATED / OUTPUT_TOKEN_LIMIT_REACHED; v2 is not run. Record future
results separately as bounded-synthesis (v1) and quality-qualification (v2).
A v2 PASS never implies v1 PASS. Do not compare latency/output efficiency across
versions as if they used the same limit. Existing historical records stay intact;
the CLI prints a new report and never overwrites result files or PM review records.

## Exact setup and commands

Use the same PM PowerShell session with existing keys. No new key or billing
change is required. Set only the exact model IDs and select --suite v2; do not
change the case or set a provider-specific token limit.

```powershell
Set-Location 'C:\Users\Mike\Documents\Codex\2026-09-25\referenced-chatgpt-conversation-this-is-an\work\phase5'
$env:PYTHONPATH = Join-Path $PWD 'src'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONIOENCODING = 'utf-8'
$phase7Python = 'C:\Users\Mike\Documents\pokemon-tcg-lab\.venv\Scripts\python.exe'
$env:POKELAB_GEMINI_MODEL = 'gemini-3.5-flash-lite'
$env:POKELAB_OPENROUTER_MODEL = 'nvidia/nemotron-3-super-120b-a12b:free'
# Safe offline preparation, exactly the two candidates with mocked responses:
& $phase7Python -m pokelab.agent_qualification --suite v2
```

Required existing environment: POKELAB_GEMINI_API_KEY,
POKELAB_GEMINI_FREE_TIER_CONFIRMED=NO_BILLING, POKELAB_OPENROUTER_API_KEY.
Do not print or paste key values. A successful prior key check does not authorize
another request. The following commands are prepared only; STOP for PM approval.

After explicit authorization for Gemini v2, one call:

```powershell
$env:POKELAB_7B_LIVE_AUTHORIZATION = 'PM_APPROVED_ZERO_COST'
try {
    & $phase7Python -m pokelab.agent_qualification --suite v2 --live --provider gemini
} finally {
    Remove-Item Env:POKELAB_7B_LIVE_AUTHORIZATION -ErrorAction SilentlyContinue
}
```

After explicit authorization for Nemotron v2, one call, after Gemini has finished:

```powershell
$env:POKELAB_7B_LIVE_AUTHORIZATION = 'PM_APPROVED_ZERO_COST'
try {
    & $phase7Python -m pokelab.agent_qualification --suite v2 --live --provider openrouter
} finally {
    Remove-Item Env:POKELAB_7B_LIVE_AUTHORIZATION -ErrorAction SilentlyContinue
}
```

Do not launch concurrent processes. Preserve output under separate new v2 result
names; never redirect over a v1 result. No automatic repeat on transport failure,
length termination or PM rejection. None of these live commands was executed.

## Verification

130 network-blocked tests passed: all eight wire formats receive 4096 in v2 and
1200 in v1 with identical messages; separate pinned configuration/suite hashes;
unchanged packet/input hashes; prepared candidate gate; v2 CLI mock pair; output
budget bounds; length termination and partial-output exclusion for both candidates;
existing secret quarantine, serial isolation and 7A regressions. No broad UI/build
work, network requests, live model calls, merge, certification or Phase 7C work.
