# Phase 7B — provider transport and frozen qualification

Implementation only, awaiting PM authorization before the first live call.
Branch: `phase7b-provider-qualification`. Certified 7A starting point:
`3370ac76e440926becf2acf11b141ac2275d7173`.
No provider/model is live-qualified or certified by these mocked results.
No UI, Research Mode, memory, actions, tools, automatic model routing, selection
policy, database writes, 7C work, merge or certification is included.

## Transport and zero-dollar boundary

`agent_providers.py` shares one bounded OpenAI-compatible Chat Completions
transport across OpenAI, Gemini, xAI, Mistral, DeepSeek, OpenRouter and Ollama.
Anthropic uses the same HTTP machinery with native Messages request/response
translation. Every provider accepts credential-free `httpx.MockTransport`.
Mock requests never include real environment credentials, even when configured.
This demonstrates wire-contract compatibility, not live model compatibility.

Real execution is blocked by default. Only Gemini's explicit reviewed free-tier
model IDs, explicit OpenRouter `organization/model:free` IDs, and loopback Ollama
are eligible. OpenAI, Anthropic, xAI, Mistral and DeepSeek stay mock-only in 7B,
even with credentials and the authorization flag. Fixed endpoints, no proxy-env
inheritance, redirects, retries, model fallback or automatic model discovery.
OpenRouter requests cap prompt/completion/request prices at zero and disable
fallbacks. No tools, grounding add-ons or browsing are sent.

Gemini requires a project with **no Cloud Billing attached**, not paid credits or
a billing-enabled project's introductory credits. The host cannot establish the
key's billing tier without external account knowledge; the PM's explicit
`NO_BILLING` confirmation is required. Recheck availability/free pricing before
authorizing; if unavailable, stop rather than enable billing or substitute a
model. API refusals/rate limits stop the run. A reported positive charge stops
the run and is recorded; detecting it afterward is not a refund guarantee.

Ollama is fixed to `http://127.0.0.1:11434`, requires `LOCAL_ONLY`, rejects cloud
model names and namespaced models, and must run with cloud disabled server-side.
No model pulls, installation or cloud fallback are performed by the harness.
Zero API cost does not mean zero local electricity cost.

Official contracts checked for this implementation:

- [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat)
- [Gemini compatibility](https://ai.google.dev/gemini-api/docs/openai),
  [pricing](https://ai.google.dev/gemini-api/docs/pricing),
  [billing](https://ai.google.dev/gemini-api/docs/billing)
- [Anthropic Messages](https://platform.claude.com/docs/en/api/messages/create)
- [xAI Chat](https://docs.x.ai/developers/rest-api-reference/inference/chat)
- [Mistral Chat](https://docs.mistral.ai/api/endpoint/chat)
- [DeepSeek API](https://api-docs.deepseek.com/)
- [OpenRouter free variants](https://openrouter.ai/docs/guides/routing/model-variants/free)
  and [price constraints](https://openrouter.ai/docs/guides/routing/provider-selection)
- [Ollama compatibility](https://docs.ollama.com/api/openai-compatibility)

## Frozen qualification case and scoring

`qualification/ultra-ball-v1.json` freezes the certified 7A real-data case. Its
hash is `a98e533dc169fa6d7aa559181622ade13d11508c0b87906ef349b00491eaac3e`.
Source database and sidecar hashes were unchanged during extraction. Qualification
reads this file, never the current collection/deck databases. It includes the
7A compact active-deck/ownership evidence; PM should review this exact packet
before authorizing its transmission to a free service with its own data policy.

The combined system contract, output schema, question and packet are pinned to
input hash `389165b46a93ce34ea62853b5d49beeaf7c45c4875a16bbcfb8fb46631719432`.
Changing them fails closed. Every provider gets the same two logical messages;
Anthropic's system field is only a wire-format translation. No previous response
is included. Maximum eight selections, one synchronous request at a time; a lock
also serializes overlapping harness runs in one process. Run only one CLI process
at a time. No concurrent qualification jobs are supported.

Per request: 32 KiB input cap, 1,200 output-token request limit (provider semantics
can differ), 128 KiB response cap, 16 KiB text cap, 90-second HTTP operation timeout.
No automatic retry. Unsupported, interrupted or tool-bearing output fails closed.

The report records requested/reported model, input hash, latency, input/output and
reasoning tokens when reported, estimated/actual USD cost and its basis. Unknown
usage/cost remains null, not invented zero. Reasoning counts are informational and
are not added again to completion counts. Live estimated cost is zero under the
guarded policy; actual cost is only the provider-reported `usage.cost`, when
present. Mock counters and responses are fixtures, never performance benchmarks.

Automatic checks compare sample/inclusion counts (734/648), active quantity (4),
ownership (0), tournament quantity (3), evidence citation ownership, and the exact
rules boundary: `REVIEWED` profile, `INSUFFICIENT_INFORMATION` gameplay status,
`profile-only`, execution unauthorized. A rules profile is not a gameplay result.
Duplicate JSON keys, malformed contracts, misattributed citations and contradictory
structured facts fail. Valid output still remains **PENDING_PM_REVIEW**.

For each model, PM must record:

- Grounding correctness of every prose claim and any arithmetic/comparison.
- Whether citations actually entail the claims, beyond valid evidence IDs.
- Whether prose preserves rules scope, missing scenario and execution boundary.
- Unsupported claims/hallucinations: list each, or explicitly record none after review.
- Usefulness: poor/adequate/good, with a brief reason.
- Overall pass/fail; any rules-boundary conflation is a failure.

The machine report leaves hallucinations and usefulness as `PM_REVIEW_REQUIRED`;
it never asserts that schema compliance proves absence of hallucinations. Preserve
the report and append PM review in a separate review document after a future run.
The harness prints sanitized reports to stdout and stores no responses/database
state automatically. Invalid raw model outputs are discarded, not archived.

## Secret handling

Credential variables, **only needed for the provider in use**:
`POKELAB_GEMINI_API_KEY`, `POKELAB_OPENROUTER_API_KEY`.
Ollama requires no API key. Reserved mock-only provider variables are
`POKELAB_OPENAI_API_KEY`, `POKELAB_ANTHROPIC_API_KEY`, `POKELAB_XAI_API_KEY`,
`POKELAB_MISTRAL_API_KEY`, `POKELAB_DEEPSEEK_API_KEY`; do not configure them for 7B.

Keys are read directly from process environment, sent only in authentication
headers, and never copied into prompts, fixtures, reports, database state or logs.
No dotenv loading, key files or credential CLI arguments. HTTP logging is suppressed
during the bounded standalone request and restored afterward. Error details,
headers and raw response envelopes are never returned or logged. Known credential
values and common JSON/URL/base64 encodings are checked on inputs, full response
envelopes (also after JSON decoding), and serialized reports; matching content is
rejected wholesale. Tests use synthetic markers, never real keys. This is scoped
to the named credentials; do not put unrelated secrets in the packet or use
external HTTP tracing/debuggers that capture process memory or authentication.

## Exact PowerShell setup — no live calls yet

Use the development checkout and existing Python environment:

```powershell
Set-Location 'C:\Users\Mike\Documents\Codex\2026-09-25\referenced-chatgpt-conversation-this-is-an\work\phase5'
$env:PYTHONPATH = Join-Path $PWD 'src'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONIOENCODING = 'utf-8'
$phase7Python = 'C:\Users\Mike\Documents\pokemon-tcg-lab\.venv\Scripts\python.exe'
# Safe now: all eight providers use credential-free mocks, no network.
& $phase7Python -m pokelab.agent_qualification
```

For Gemini, create/use an AI Studio API key for a free-tier project with no billing
attached. Do not paste the key into chat or any command literal. Configure:

```powershell
$env:POKELAB_GEMINI_API_KEY = [System.Net.NetworkCredential]::new('', (Read-Host 'Gemini key' -AsSecureString)).Password
$env:POKELAB_GEMINI_MODEL = 'gemini-2.5-flash-lite'
$env:POKELAB_GEMINI_FREE_TIER_CONFIRMED = 'NO_BILLING'
```

The other allowed Gemini model is `gemini-2.5-flash`. Test each separately, serially.
For OpenRouter, create a key without purchasing credits. Select a currently
available explicit free model from the model catalogue; copy its full ID ending
in `:free`. Do not use `openrouter/free`, `openrouter/auto`, presets or paid IDs.

```powershell
$env:POKELAB_OPENROUTER_API_KEY = [System.Net.NetworkCredential]::new('', (Read-Host 'OpenRouter key' -AsSecureString)).Password
$env:POKELAB_OPENROUTER_MODEL = Read-Host 'Exact organization/model:free ID'
```

Optional Ollama: install a local model separately and disable cloud on the Ollama
server (`OLLAMA_NO_CLOUD=1` before starting/restarting it). Select the installed
local tag; the harness never pulls it or contacts a cloud endpoint.

```powershell
$env:POKELAB_OLLAMA_MODEL = Read-Host 'Installed local model tag'
$env:POKELAB_OLLAMA_LOCAL_CONFIRMED = 'LOCAL_ONLY'
```

**STOP HERE. Wait for explicit PM authorization before the following live step.**
Only after that authorization, in the same shell:

```powershell
$env:POKELAB_7B_LIVE_AUTHORIZATION = 'PM_APPROVED_ZERO_COST'
try {
    # One call at a time, Gemini then OpenRouter; transport failure stops the batch.
    & $phase7Python -m pokelab.agent_qualification --live --provider gemini --provider openrouter
    # Optional separate local run, only if authorized and configured:
    # & $phase7Python -m pokelab.agent_qualification --live --provider ollama
} finally {
    Remove-Item Env:POKELAB_7B_LIVE_AUTHORIZATION -ErrorAction SilentlyContinue
}
```

Do not run multiple shells/jobs concurrently. Review the reported status before
any further run. Clear process credentials when finished:

```powershell
Remove-Item Env:POKELAB_GEMINI_API_KEY, Env:POKELAB_OPENROUTER_API_KEY -ErrorAction SilentlyContinue
```

## Verification

**73 tests passed**: 47 targeted provider/harness cases plus 26 certified 7A
regression tests. The CLI mock run exercised all eight providers with sockets
blocked. Two existing dependency deprecation warnings remain. No broad UI,
build or browser work is required because this standalone code is not connected
to application behavior. Network sockets are forbidden in tests. Tests cover all
eight mock wire formats, gates, no key transmission to mocks, bounded/error/tool
responses, secret quarantine, frozen tamper detection, serial isolation, duplicate
JSON, rules conflation, wrong facts/citations, unknown usage and stop-on-cost-failure.
Live model calls: **zero**. Live API spend: **$0**.
