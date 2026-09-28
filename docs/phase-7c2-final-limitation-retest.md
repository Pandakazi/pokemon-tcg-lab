# Final limitation retest investigation

Starting HEAD: `139af524bcde6eae4049e329ea7b0140f5efbd41`;
branch `phase7c2-deck-archetype-research`; starting tree clean.

## Exact production trace

The exact PM composition sentence is rejected by the starting commit:

> The active deck contains no Charizard ex cards, as its featured primary Pokémon is Dragapult ex.

1. `Answer.model_validate_json` accepts its structure with outcome
   `unsupported_question`, empty facts/interpretation and nonempty limitations.
2. `assess` does not return early for that outcome. It rejects nonempty claim
   arrays for unsupported questions, then invokes `research_grounding.violation`.
3. The existing subject/verb expression matches `The active deck contains`.
   There is no epistemic prefix, so it returns `uncited_limitation_claim`.
4. `assess` raises `ContractError`; `ResearchService._run` returns
   `invalid_answer_contract`, `answer=null`, and bounded diagnostics.
5. The existing API returns that result directly. It has no alternative acceptance
   path for unsupported questions.

This was reproduced before any production edit with the exact sentence through
the guard, assessment and fake-provider service. New tests also exercise both
real API scopes, real envelope construction, real parsing/assessment and the real
guard. Only the external provider is fake; assessment is not replaced.

## Runtime mismatch, not a bypass of the first sentence

Read-only local process inspection found port 8003 owned by Python PID 15060,
started 2026-09-27 **10:43:21 EDT**, using this checkout with **no --reload**.
The corresponding wrapper PID 25344 had the same startup time. The validator
source was edited at 10:59:27 EDT; the guard at 11:03:46 EDT; the correction commit
was created at 11:06:49 EDT. `api.py` imports/instantiates ResearchService on startup.
Thus the currently listening QA process predates the new assessment integration;
changing checkout HEAD does not reload its imported Python code.

This establishes a stale QA runtime and explains acceptance on that process.
There is no retained per-request build attestation here to independently prove
which process served the historical response. No historical raw output, process
memory, environment secrets or provider data was retrieved. No API call or
runtime restart was made during diagnosis.

Prior tests used fresh code; they could not establish that the PM server had been
restarted. They also lacked this exact unsupported-question/API regression matrix.
There is no demonstrated lexical or unsupported-outcome bypass for the first
sentence at the specified starting commit.

## Narrow additional correction

The second sentence is a factual claim about the relationship between the premise
and observed deck composition, not merely an epistemic boundary:

> The question assumes a premise about Charizard ex that contradicts the supplied deck composition and evidence.

If stated, that comparison belongs in a cited claim array; it cannot evade
citations by being placed in limitations. A four-line limitation-only extension
rejects the bounded `premise/assumption ... that contradicts ... deck
composition/contents` form. It does not infer whether the premise is true or false.

`Creator intent cannot be established from the supplied evidence.` stays accepted.
No Answer schema, citation requirements, prompt, transport, Budew attack-cost
logic, comparison framing or overview ranking changed. This is not universal
semantic entailment validation.

## Regression and minimal retest

Fifteen exact-sentence tests cover all three outcomes at the guard/assessment
boundary and both API scopes for unsupported questions. They assert one fake
provider call, guard invocation, safe execution metadata and no rejected answer
leak. Pure epistemic limitations remain accepted.

Verification: 15 new focused tests passed; 185 affected Research validation tests
passed; one complete network-blocked backend gate passed all 755 tests (only the
two existing Starlette/FastAPI deprecation warnings). `git diff --check` passed.
No frontend code changed, so no frontend/TypeScript/build runs were needed. No
live provider or external network calls, merge, tag or certification occurred.

Before the one PM retest, stop/restart the actual QA backend from this checkout
using the existing configured Gemini session. The recorded processes.json IDs
were stale at inspection; do not assume restarting an unrelated process refreshes
the listener. If the normal QA restart reports port 8003 occupied, stop only the
verified backend for this checkout, then restart. Do not change credentials or
provider configuration.

Verify `(Invoke-RestMethod 'http://127.0.0.1:8003/api/v1/deck-workspace').runtime_revision`
equals the new correction commit, then hard-refresh the UI. That read-only check
does not invoke a model. With Active Deck context and the same explicit comparison
and window, submit once: **Why is this deck built around Charizard ex?**
Expect any factual correction in cited claims, or a purely epistemic/scope
limitation. Either supplied offending sentence in limitations must cause safe
rejection. No retest of the three passing areas is requested. No automatic retry.
