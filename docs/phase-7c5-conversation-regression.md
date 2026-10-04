# Phase 7C.5 — Active-deck conversation regression

Starting state: clean `phase7c5-concrete-deck-resolution`,
`06c6a732ab21be0a6af768f9207e5feafa345d40`.

## Finding and confidence

The direct 7C.4 → 7C.5 diff proves that all conversations began receiving the
expanded concrete-output prompt and, for Gemini, the expanded Answer JSON schema.
The schema introduces nested Candidate/Proposal/Premise definitions and bounds even
for EXPLORE questions. These fields were optional locally, but still part of every
provider's structured-generation request. Active-deck selection was not itself
forcing a diff; unconditional request construction was the routing defect.

The PM message maps to the branch immediately after provider completion, before
Answer parsing or local proposal resolution. Therefore a local deck-validation
exception cannot explain that message. Transport endpoints, token/byte ceilings,
completion handling and required top-level answer fields were not changed in 7C.5.

The exact historical provider cause is NOT established. No retained HTTP status,
termination reason or safe error category was supplied for these attempts. Schema
rejection, unavailable completion and other transport failures cannot be distinguished
from the UI message alone. Mock tests do not prove Gemini's live schema acceptance.
This pass fixes the proven unconditional schema expansion without claiming a
recovered provider error or replaying the historical response.

## Small correction

EXPLORE uses the small 7C.4 provider-facing prompt/schema: version, paragraphs and
optional fact_ids/evidence. It does not request a proposal or final-deck object.
DRAFT/RECOMMEND/FINALIZE retain 7C.5 structured proposals. “Give me the final 60”
now correctly selects FINALIZE. Local parsing remains the extension-capable superset;
specific returned premises and bounded named-subject detection still resolve facts.
No proposed object is required for ordinary analysis. No retrieval, provider
transport, limits, frontend, saved-deck state or strict Research changes.

Provider failures now expose only a bounded provider_status: numeric HTTP status,
known termination/transport/quarantine categories, or a fixed generic fallback.
No arbitrary messages, raw responses or exception text are exposed. No retry exists.

## Coverage and limits

New Gemini fake-transport tests assert ordinary request shape and successful repeat
questions with an active deck; local proposal evaluation is forbidden in those
ordinary fixtures. Cases cover deck explanation, both improvement phrasings and
general conversation without a deck. Concrete schema routing is separately checked.
Existing real local-domain tests cover diffs, finalized 60, malformed proposals,
revision checks and no writes. The old fake helper assumed the expanded SYSTEM for
every request; it now checks the selected contract instead.

Focused tests: 74 passed. One final relevant gate: 254 passed, four API tests
blocked by the runner's blanket socket guard preventing Windows asyncio loopback
setup. Only those four were rerun with loopback permitted and external networking
blocked: all four passed (258 covered successfully overall). An earlier gate command
referenced a nonexistent test file and collected no tests. No broad gate was repeated.
No frontend changes/tests needed. Whitespace check passed. No provider or external
network calls. This synthetic active-deck fixture is not a recovered revision-158
provider response. PM must verify the live result; historical causality is unresolved.

## Minimal PM retest

Restart the existing QA runtime at this branch's ending commit, preserving the
existing explicit provider/model and zero-cost settings. With the reported Raging
Bolt Ogerpon deck selected, ask “How does this deck work?” twice, then “Is there a
way to make it better or is it pretty maxed out?” Verify usable conversation and no
required diff. Then ask “Give me the exact card names and quantities you would
change, what you would remove, and why.” Verify a proposed revision-bound diff and
no writes. Separately check “Give me the final 60.” If a call fails, retain only
status/provider_status and safe execution metadata; do not repeatedly retry.

Ready for PM live retest; not a claim that the historical live failure is proven fixed.
No merge, push, tag or certification.
