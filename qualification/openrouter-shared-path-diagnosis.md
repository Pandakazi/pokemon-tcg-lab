# Shared OpenRouter path diagnosis after Nemotron attempt #3

PM report: `nvidia/nemotron-3-super-120b-a12b:free`, 633 ms,
transport_or_response_error, empty diagnostics and no answer/usage. NOT_EVALUATED
remains correct. No further inference or authenticated account calls were made.

## Deterministic audit

- Base: `https://openrouter.ai/api/v1`; POST `/chat/completions`.
- Header: `Authorization: Bearer <POKELAB_OPENROUTER_API_KEY>`;
  `Content-Type: application/json`. Optional attribution headers are not required.
- Adapter reads exactly `POKELAB_OPENROUTER_API_KEY`, not `OPENROUTER_API_KEY`.
  Presence-only local inspection found it absent in this agent process. This says
  nothing about the separate PM shell used for the run. Missing credentials in
  this adapter return missing_credential before networking, not the reported error.
- Explicit model and frozen system/user messages, stream false, max_tokens 1200.
- provider.allow_fallbacks false; max_price prompt/completion/request all zero.
- HTTPX timeout 90 seconds for each network operation (not a total wall deadline);
  redirects disabled, environment proxy settings ignored, no configured retries.
- Response body cap 128 KiB, output text cap 16 KiB; errors bounded and quarantined.

These request settings match the official [overview](https://openrouter.ai/docs/api_reference/overview)
and [routing contract](https://openrouter.ai/docs/guides/routing/provider-selection).
No evidence establishes a wrong URL, required missing header or malformed request.
Qwen's 429 proves an HTTP response reached its run, not that every later request
used the same environment, or that a specific model route is available.

## Established diagnostic defects; historical failure unknown

The broad exception handler discarded exception category, processing stage and
any received HTTP status. That is why diagnostics were empty. Connection/TLS
failures, read failures, invalid JSON and unexpected response shapes all collapsed
to the same status. Latency cannot distinguish them.

Official [error documentation](https://openrouter.ai/docs/api_reference/errors-and-debugging)
also describes HTTP 200 non-streaming bodies containing error instead of choices.
The prior parser indexed choices and raised KeyError for that documented shape.
This path is reproduced locally, but cannot be established as this attempt's
actual cause because its evidence was discarded. Server-side inference progress
cannot be inferred from the absence of a delivered answer.

Small correction: recognize top-level and choice-level OpenRouter errors; preserve
only existing allowlisted error codes/categories. Generic exceptions now retain
fixed internal stage/category labels and integer HTTP status if received. No
exception text, class names from providers, traceback, response/request objects,
headers, credentials or raw prose are stored. Existing secret quarantine and
no-quality-grade-on-failure behavior remain intact.

107 network-blocked tests passed (81 provider/harness + 26 7A). New cases exercise
HTTP-200 provider errors, invalid JSON/envelopes/UTF-8, connection/timeout/protocol
failures, synthetic environment-key selection, literal endpoint/auth header, and
timeout/proxy/redirect settings. Frozen contract tests verify input hash:
`389165b46a93ce34ea62853b5d49beeaf7c45c4875a16bbcfb8fb46631719432`.

## Single cheapest next diagnostic action — authorization required

Propose ONE authenticated, non-inference GET to
`https://openrouter.ai/api/v1/key`, from the same shell/key used for the failed
run, using the same Bearer construction, timeout, proxy and redirect policy.
The [official limits documentation](https://openrouter.ai/docs/api_reference/limits)
documents this key/account endpoint. It sends no model/prompt, generates no model
tokens and is not a paid inference request. Do not execute it yet.

Capture only status, fixed stage/error category, and allowlisted numeric/boolean
fields such as limit_remaining, is_free_tier and free_model_daily_requests
used/limit/remaining; discard key label, identifiers and raw JSON, and quarantine
known secrets. No key value in command text/logs. No retries or inference fallback.

This separates present connectivity/authentication/account-quota problems from
the inference-specific path: connection failure implicates the transport path;
401/403 implicates authentication/access; 200 establishes accepted key/access to
this endpoint and exposes reported account limits. It does NOT prove model access,
provider capacity, per-minute allowance or reconstruct the historical failure.
No single non-inference check can definitively distinguish all model-side causes.
If it succeeds with available quota, the new diagnostics would be needed during
a separately authorized inference attempt to distinguish the remaining causes.

Model, frozen case, question, contracts, scoring, serial execution and zero-dollar
controls unchanged. No alternative model selected. Stop for PM authorization.
