# 7C.5 — Phantom-cut and concrete-state integrity remediation

Start: clean `phase7c5-concrete-deck-resolution` at
`4fc85bd58dd1b10dc3d2c94dad88f328cec85695`.

## Established causes

The classifier matched “cut and add” literally, but not “Cut [card] and add…”. It
also lacked direct “Add another…” commands and “replace those three”. These requests
could remain EXPLORE and bypass hybrid action validation/state reconciliation.
The ordinal filter already existed on the hybrid path; bypassing that path allowed
stale ordinal prose to survive. The bare state-sensitive word “another” was not
included in the quantity guard.

There was a second independent cut defect: local validation set `validated=false`
and reported an absent/oversized cut, but did not add the resolved card name to the
invalid-premise set used to filter strategic prose. Thus even a correctly rejected
diff could retain advice dependent on the phantom source card.

## Changes

- `agent_deck_proposals.py`: explicit leading add/cut/remove/swap requests and
  replacement-of-those wording select RECOMMEND; invalid cuts mark both supplied and
  canonical names as rejected premises; absent-card messages name the source revision.
  Quantity reconciliation also removes state-sensitive “another” wording.
- `agent_conversation.py`: a direct explicit user cut is checked even if omitted from
  the optional provider block. This is a bounded anchored user-command check, not
  action extraction from arbitrary model prose. It only supplements a missing cut
  when the named card is absent from the supplied active snapshot; existing valid
  cuts are not duplicated. The same read-only evaluator resolves identities and
  rechecks revision before rendering. Missing action summaries stay incomplete.
- `agent_hybrid.py`: discard invalid-card-dependent sentences and immediately
  attached pronoun continuations, retaining independent strategic goals. Invalid
  premises are handled in both visible prose and structured rationale.
- `tests/test_agent_deck_proposals.py`: direct command routing, omitted phantom cut,
  valid/malformed/missing payloads, PM counts, stale ordinals, no writes and ordinary
  empirical-audit routing.
- This report.

No alternative card is silently substituted and nothing is applied. The hidden
summary remains the primary model-intent source. Explicit user commands are checked
against local state; ambiguous prose still does not create actions.

## First-attempt failures: known versus unknown

The exact historical provider failures cannot be established from the generic UI
message. In `run`, that message is selected from provider status/finish reason before
hidden JSON parsing. Therefore malformed hidden actions alone cannot cause that
specific early provider-failure branch. HTTP failures, transport/response failures
and unusable completion metadata remain distinguishable only with the existing safe
`provider_status`/execution fields. No response body/status from those historical
calls was supplied; no root cause or recovered prose is invented here.

The previously missed concrete prompts now use the hybrid contract rather than the
ordinary schema, removing the proven routing mismatch. This is not proof that every
historical first-attempt failure was caused by schema rejection.

Deterministic tests establish that a completed response containing useful prose
survives missing or malformed hidden actions. Valid entries are salvaged from
parseable partial summaries, and the full proposal remains unresolved/needs repair.
No automatic retry, paid routing, transport change or live call was introduced.
Existing truncation and secret quarantine boundaries remain intact.

## Verification and PM retest

Focused tests: **117 passed**. All three phantom-cut payload cases preserve an
independent consistency goal, reject absent-card strategic claims, display source
absence, and leave database bytes unchanged. Direct add/replacement questions run
through the natural-prose fake Gemini path and retain Area Zero 3 → 4 and Grass 6 → 7.
The empirical-versus-structural question remains EXPLORE with no concrete schema.
Single final network-blocked backend gate: **301 passed**, two existing dependency
deprecation warnings.
No frontend changes/tests; whitespace check passed.

After restarting the existing configured QA runtime, use the active revision-158
deck and these prompts:

1. “Cut Squawkabilly ex and add another Boss's Orders.”
2. “Add another Area Zero and another Grass Energy.”
3. “What would you replace those three with?”
4. “Which of these recommendations are proven by tournament results and which are just your structural judgment?”

Expect the absent cut to be rejected without its dependent strategic justification;
all additions use local counts; incomplete summaries remain visibly unresolved;
the evidence-audit question stays conversational. If a provider failure recurs,
retain only `status`, `provider_status` and safe execution metadata before retrying.

Bounded limits: pronoun dependency filtering is local, not universal semantic
verification. User-cut extraction recognizes direct anchored commands only. Cached
legality and the existing exact-name resolver retain their documented limitations.

READY FOR PM LIVE QA. No external network/provider calls, deck writes, push, merge,
tag, certification or Phase 7D work. Certification remains subject to PM acceptance.
