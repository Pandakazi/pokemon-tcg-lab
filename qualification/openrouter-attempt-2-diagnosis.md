# OpenRouter attempt #2 — 429, NOT_EVALUATED

PM reports `qwen/qwen3.8-27b:free` returned HTTP 429 in 515 ms, without
reported model, finish reason, usage or answer. Qwen is NOT_EVALUATED. The former
FAIL/invalid_output_contract and false quality fields were a harness bug, not a
qualification result. This document corrects that interpretation; no raw prior
run report was supplied or rewritten.

Root cause: the harness called assess on empty response text for all failures,
then special-cased only 404. It now calls assess only for successful transport
answers. Every non-ok transport/provider/policy outcome is NOT_EVALUATED with
null output/grounding/citation/rules fields, no invented contract violation, and
NOT_EVALUATED usefulness/hallucinations. Actual answer scoring is unchanged:
malformed JSON returned as model answer still fails the frozen output contract.
429 is PRE_INFERENCE_PROVIDER_RATE_LIMIT_OR_CAPACITY. Other errors retain distinct
failure categories; timeouts do not assert that server-side inference never began.

## What is known about the 429

The current [official OpenRouter limits documentation](https://openrouter.ai/docs/api_reference/limits)
describes platform free-model/DDoS rate limits and upstream provider rate limiting
or capacity as possible 429 sources. Platform rate-limit headers and provider
error metadata distinguish these. Credit/key limits have their own metadata,
usually in 402 errors. The previous implementation discarded the entire error
body and headers. Status and 515 ms alone cannot identify which condition occurred.
There is no evidence to attribute this attempt to a specific daily/minute cap,
account/key limit, upstream capacity or zero-price constraint. No account request
or inference retry was made to investigate, and no limit/routing policy changed.

## Small diagnostic correction

OpenRouter HTTP errors now read at most 16 KiB of response body, transiently,
while HTTP logging remains disabled. No raw error body is returned or stored.
Known-secret quarantine applies before and after JSON decoding and to the
selected headers. Quarantine/malformed/oversized diagnostics preserve the HTTP
status and fail closed for diagnostic capture.

Only numeric HTTP-range error_code/provider_code, exact allowlisted error_type,
limit_source/reason categories, and digit-only Retry-After/X-RateLimit-Limit/
Remaining/Reset headers survive. Error message, metadata.raw, provider prose,
request IDs, arbitrary headers, key/account identifiers and remedy hints are
discarded. Unrecognized diagnostic categories remain absent; never infer a cause
from missing fields. Numeric Retry-After is informational only: no retry scheduler
is added. This is deliberately narrower than storing sanitized free-form messages.

Frozen packet, question, system/output contracts, scoring, model, explicit-model
requirement, serial execution and zero-price/fallback controls are unchanged.
Input hash: `389165b46a93ce34ea62853b5d49beeaf7c45c4875a16bbcfb8fb46631719432`.
No environment variable change required. No additional live model calls, model
switch, paid routing, merge, certification or 7C work. Stop for PM authorization.
