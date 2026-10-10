# Deterministic small-delta completion — PM QA candidate

Base: `d0e9a2a3098e62af376b0ba990644babec1baa8a`.
Branch: `phase7c5-concrete-deck-resolution`. No live calls, merge, tag or certification.

## Pre-change trace and evidence limits

The actual historical PM provider text was not supplied or recovered. No claim is made
about its exact contents. A network-blocked fake-provider reconstruction established the
production failure path before behavior changed: a legal 58-card list followed by the
same 58-card replacement yields `incomplete`, `repair_attempts=1`, total 58.

`agent_artifacts.repair_requirements()` sent this exact structured repair body for the
synthetic Pikachu/Recovery Tool/Lightning Energy fixture. The allowed sandbox remained
alongside it at envelope.candidate_sandbox:

```json
{
  "accounting": {
    "excess_proposed_count": 0,
    "proposed_total": 58,
    "resolved_count": 58,
    "true_missing_count": 2,
    "unresolved_proposed_count": 0
  },
  "alternatives": [],
  "cards": [
    {
      "candidate_id": "gameplay:127f9728880d24434c07c9ea019975c6",
      "canonical_name": "Pikachu ex",
      "category": "Pokemon",
      "printing_id": "qa-pikachu",
      "quantity": 4
    },
    {
      "candidate_id": "gameplay:de6a12f57cc546fe498ea3cae2a7d555",
      "canonical_name": "Recovery Tool",
      "category": "Trainer",
      "printing_id": "qa-recover",
      "quantity": 4
    },
    {
      "candidate_id": "deck-basic-energy:Lightning",
      "canonical_name": "Lightning Energy",
      "category": "Energy",
      "printing_id": "qa-energy",
      "quantity": 50
    }
  ],
  "construction_violations": [],
  "failures": [
    "2 cards remaining"
  ],
  "format": "standard",
  "missing_copies": 2,
  "name": "Keep the core",
  "target_total": 60,
  "total": 58,
  "unresolved": []
}
```

Exact accompanying repair instruction:

> Repair this same generated deck now. Return a complete generated_deck artifact; do not merely explain. Preserve valid engine cards, repair failed roles using Standard-legal candidates. Resolve or replace the unresolved proposed copies, add only accounting.true_missing_count genuinely missing copies, and fix construction_violations. total is resolved copies, not proposed_total; never double-count unresolved slots as missing. Select exact candidate_id values. Change at most 8 card copies; no broader redesign. Choose only candidate_sandbox cards.

The expected provider shape was a complete `<POKELAB_ACTIONS>` generated_deck block:

```text
<POKELAB_ACTIONS>{"type": "generated_deck", "name": "Keep the core", "cards": [{"card_name": "Pikachu ex", "printing_id": "qa-pikachu", "quantity": 4, "role": "main attacker"}, {"card_name": "Recovery Tool", "printing_id": "qa-recover", "quantity": 4, "role": "recovery"}, {"card_name": "Lightning Energy", "printing_id": null, "quantity": 50, "role": "energy"}]}</POKELAB_ACTIONS>
```

`agent_conversation.run()` parsed this using `agent_hybrid.parse()` into a list Proposal.
`agent_deck_proposals.evaluate()` constructed a new transient document from that list;
it did not apply a delta to the retained 58. Validation reported `2 cards remaining`.
The monotonic check rejected only totals below the original total, so 58→58 survived.
The second run correctly stayed incomplete and stopped at the one-repair limit, but it
had no exact-additions contract to force progress. The reconstruction lost no parsed
additions: the fake response contained none. Thus the proven defect is overly broad
replacement-artifact semantics for a pure deficit, not a demonstrated parser loss.

## Narrow new path

`agent_deck_completion.eligible()` accepts only a resolved generated list with zero
unresolved slots, zero typed construction violations, 1–8 missing copies, a sandbox,
and no hard validation message except the exact known count deficit. A missing Basic,
unknown legality or other construction error keeps the existing general repair path.

`repair_requirements()` marks `mode=additive_completion`, supplies `required_delta=N`,
retained cards/counts, and the same allowed sandbox. A dedicated bounded repair contract
asks for additions only; no ordinary full-deck reconstruction instructions are used.

```json
{"type":"generated_deck_completion","adds":[{"candidate_id":"<supplied ID>","quantity":1},{"candidate_id":"<supplied ID>","quantity":1}],"removes":[]}
```

The existing action-block delimiter is used. Optional natural prose may precede it.
The strict schema permits at most eight additions and no removals; positive integer
quantities must sum exactly to required_delta. Every ID must be supplied in the sandbox.
The backend combines these additions with the retained typed entries, never provider
replacement entries, and invokes the existing full evaluator. Same-card additions merge
through the existing transient document logic. Only a fully validated 60 replaces the
partial artifact. No active deck or collection write occurs.

The max-eight bound, one provider repair pass and monotonic protection remain. A failed
pure repair preserves the original report/session artifact, including on an explicit
follow-up repair. A successful delta persists the 60-card generated artifact for recount.
This does not add a second automatic repair after a general replacement repair. An
explicit later completion request can use the retained pure-deficit artifact.

## Bounded failure reasons

- `repair_delta_wrong_size`
- `repair_candidate_outside_sandbox`
- `repair_candidate_id_invalid`
- `repair_copy_limit_violation`
- `repair_ace_spec_violation`
- `repair_parse_failed` (including forbidden replacement/removal shapes)
- `repair_provider_incomplete`
- `repair_provider_failure`
- `repair_post_apply_validation_failed`
- `repair_internal_assessment_failure`

These are returned in completion.reason for retained results. Existing safe execution
metadata is preserved; arbitrary provider messages, raw output and exception text are
not included in diagnostics. General repair behavior is otherwise unchanged.

## Verification and limits

The PM-equivalent test starts with 58 resolved, zero unresolved, proposed total 58,
true missing 2 and no construction violations. The provider selects +1 Pikachu ex and
+1 Recovery Tool; backend application yields 60, VALIDATED, completion complete.
The retained Energy quantity stays unchanged, and local recount returns 60 without a call.

Focused completion/sandbox run: **26 passed**, including wrong-size (+1/+3), malformed,
full replacement, removal, outside/missing ID, copy/ACE failure, Basic Energy, pending
repair failure/success, provider/truncation and post-apply validation failure cases.
One final network-blocked backend gate: **773 passed**, including 381 research/card-pool/
context, 16 functional-index and 45 Collection/Deck Builder compatibility tests. External
sockets and DNS were blocked and PM settings were removed only from the test process.
`git diff --check` passed. Only two existing dependency deprecation warnings.
Frontend unchanged; no frontend build/test run.

Candidate quality remains separate: PM observed 15 Energy, weak Trainer mix and a thin
support pool from a 28-candidate packet with nine Basic Energy entries. Ranking,
Limitless weighting, role balance and iterative expansion are unchanged. The new path
guarantees application/validation of a valid returned +N delta, not strategic quality
or provider compliance on every request.

Frontend, legality policy, functional index, Collection storage, exact Deck Builder
allocations and Phase 7D were not changed. The pre-existing uncommitted QA-launcher
quoting edits remain untouched and excluded from this commit.

## Files changed

- src/pokelab/agent_deck_completion.py — eligibility, strict delta schema, application and failure classification.
- src/pokelab/agent_artifacts.py — precise additive repair requirements.
- src/pokelab/agent_conversation.py — dedicated bounded repair execution and retained-result handling.
- tests/test_agent_deck_completion.py — 17 new deterministic cases.
- tests/test_agent_deck_sandbox.py — pure-deficit fixtures use/reject the appropriate delta/replacement shapes.
- docs/phase-7c5-small-delta-completion.md — trace, scope and verification record.
