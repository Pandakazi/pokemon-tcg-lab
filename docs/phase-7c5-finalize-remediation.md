# Phase 7C.5 targeted FINALIZE remediation

Starting point: `36ef47c614a05e9a85e82f536150d3191a2763b0` on `phase7c5-concrete-deck-resolution`.

## Confirmed causes

- FINALIZE performed one evaluation and returned the incomplete artifact without requesting model repair.
- Pending generated artifacts existed, but short repair confirmations did not transition into a completion request.
- The resolver already used functional-group legality, but could retain a specifically requested historical raw printing even when its existing functional group contained a legal printing. Rejected illegal additions could also enter resolved counts. These are code-established defects; the exact reasons for every card in the historical PM response cannot be reconstructed without its original snapshot.
- Printed-fact review could independently resolve a name that remained unresolved in the generated artifact.
- The conversation renderer showed construction diagnostics and evidence scaffolding by default.

## Responsibilities and behavior

The conversational envelope now supplies Standard, 60 cards, fully resolved identities and legal slots as explicit build constraints. Resolution and alternatives use the existing functional groups and deterministic legal-printing selection. No name-only equivalence or new identity scheme is introduced. An explicit printing from another functional identity is not silently remapped. Illegal/unknown additions remain unresolved rather than entering the resolved total. Existing Basic Energy semantics and explicit-cut handling remain in place.

FINALIZE evaluates the initial model artifact. If missing/incomplete, it supplies compact failures, the resolved list, failed roles and locally legal alternatives to one additional model call. The model owns replacement choices and receives the role/effect/function/engine/matchup preservation instruction. The backend revalidates the returned full list. There are at most two sequential provider calls per submission, using the same explicit provider/model and existing execution controls. This is a structured repair pass, not a transport retry. Initial transport failures are not retried. An unsuccessful repair preserves an incomplete result and visible status; it cannot silently certify a partial deck. Safe execution metadata retains the initial attempt and repair outcome.

A pending generated artifact gates repair confirmations such as “finish it”, “ok so do that”, “resolve those”, and “make it legal”. They carry that artifact's repair requirements. Explanation questions, negations and explicit new/different-deck requests do not use this dispatcher. Local recount still returns the stored generated artifact without provider execution. Active workspace and generated artifacts remain separate.

Printed-fact review uses resolved generated identities before independent catalogue selection, and withholds identity-specific facts for unresolved slots, including embedded component-name references. This remains bounded factual review, not universal semantic entailment.

Default chat retains prose, list, computed totals/subtotals and completion status. Sources/card facts appear on explicit evidence requests, inspection, material factual review or selected empirical evidence. Construction issues, unresolved details, alternatives and validation scope are behind “Review deck details”. No coverage/hash/debug dump is rendered by default. The existing stacked card preview components and styling are unchanged. The UI request timeout accommodates the bounded second call.

## Verification

- Focused artifact/proposal/repair tests: 88 passed.
- Final focused repair/factual tests (including added proof questions and exact resolved identity): 37 passed.
- Focused conversation UI: 13 passed.
- Full frontend regression: 113 passed.
- Single final network-blocked backend gate: 339 passed in 87.99 seconds across finalize repair, artifacts/storage boundary, factual review, conversation, proposals, selected-card research, answer contracts, deck research and card-pool research. Two existing dependency deprecation warnings only.
- TypeScript: passed. git diff --check: passed.
- No live provider calls, external network requests, deck writes, merge, tag or certification.

## PM retest and remaining limits

Start a new conversation and request a complete legal 60-card Standard deck. Check exact resolved cards, category subtotals and final status. Recount it; then exercise a pending incomplete proposal with “Ok so do that”. Ask for sources and open construction details on demand. Confirm the stacked hover remains as accepted and active deck state is unchanged.

Completion and role preservation still depend on the model supplying a valid repair within one additional pass. Failure stays explicitly incomplete. Legality is limited to local cached Standard flags and the established functional grouping; this pass does not refresh card data or broaden equivalence. Deterministic fake-provider tests establish orchestration and validation, not live strategic quality. No browser visual session or live QA was performed during this remediation.
