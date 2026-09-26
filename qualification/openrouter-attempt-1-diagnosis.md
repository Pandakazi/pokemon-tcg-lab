# OpenRouter attempt #1 — pre-inference diagnosis

PM-reported attempt: `qwen/qwen3-next-80b-a3b-instruct:free`, HTTP 404,
395 ms, no reported model, tokens or answer. Classification remains
`PRE_INFERENCE_TRANSPORT_CONFIGURATION` / `NOT_EVALUATED`.
This is not a Qwen model qualification failure.

## Evidence checked September 26, 2026

The official [selected model endpoint metadata](https://openrouter.ai/api/v1/models/qwen/qwen3-next-80b-a3b-instruct:free/endpoints)
returns its model identity with `endpoints: []`. The catalogue page can remain
visible without any serving endpoint. Our earlier recommendation checked the
catalogue listing, not this stronger routability evidence. No timestamped error
body from the failed request was retained, so its exact historical server-side
reason cannot be proven. Current lack of endpoints explains why it cannot now
be routed; loosening the zero-cost limits would not fix this free variant.

The POST URL `https://openrouter.ai/api/v1/chat/completions`, Bearer header,
explicit `model`, `stream: false`, and `max_tokens: 1200` match the official
[request/routing documentation](https://openrouter.ai/docs/guides/routing/provider-selection).
That documentation supports `provider.allow_fallbacks: false` and
`provider.max_price: {prompt: 0, completion: 0, request: 0}`. Preserve them.
No transport implementation change is required or made.

## Proposed attempt #2 — no inference run yet

Exact candidate: `qwen/qwen3.8-27b:free`.
Its official [endpoint metadata](https://openrouter.ai/api/v1/models/qwen/qwen3.8-27b:free/endpoints)
advertises one ModelRun endpoint (`modelrun/fp4`), status 0, prompt/completion
prices both `0`, context 262144, completion cap 235929, and `max_tokens` support.
It accepts text and returns text. These advertised capabilities fit the existing
frozen request and limits. The metadata omits a per-request price; we retain our
zero request-price ceiling rather than assuming permission to pay.

This is a different explicit Qwen model, proposed because the previous variant
has no advertised endpoints. It retains a different-family comparison against
Gemini for evidence grounding and rules-boundary discipline. There is no claim
of qualification or comparative quality before testing. Public endpoint metadata
supports current routability, not guaranteed availability for Mike's account;
capacity and account privacy/provider restrictions may still reject a request.
Do not relax restrictions or retry automatically if that occurs.

Only the model environment variable needs to change after PM approval:

```powershell
$env:POKELAB_OPENROUTER_MODEL = 'qwen/qwen3.8-27b:free'
```

Keep the existing key and endpoint. Do not change billing, use routers, add
fallbacks, substitute models automatically or modify reasoning parameters.
The future authorized command is OpenRouter-only:
`python -m pokelab.agent_qualification --live --provider openrouter`.
STOP for PM authorization before running it or enabling the authorization gate.

## Preservation and verification

Only documentation and a focused mock test were added. The test asserts the exact
candidate, literal endpoint, zero price caps, disabled fallbacks, one request,
and byte-identical logical messages. Existing socket-blocked qualification tests
also cover serial execution and the accepted 404 classification.
Frozen case, packet, question, system/output contracts, scoring and input hash
remain unchanged:
`389165b46a93ce34ea62853b5d49beeaf7c45c4875a16bbcfb8fb46631719432`.

Diagnosis used public, unauthenticated documentation/metadata GETs only.
Zero additional inference/live model calls; no credentials used for discovery.
Gemini PM acceptance remains preserved. No merge, certification or Phase 7C work.
