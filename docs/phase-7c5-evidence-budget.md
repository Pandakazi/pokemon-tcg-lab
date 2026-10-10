# Evidence-budget degradation and local system questions

Starting SHA: `cca02daf41ce1e20bd2e6f6c29d86a2b2d5eb61d`.
Branch: `phase7c5-concrete-deck-resolution`.
No live provider/network calls, merge, tag, certification or Phase 7D work.

## Established causes and measured composition

The exact PM recommendation question was reconstructed from the locally retained,
deterministically generated Dragapult baseline, using the actual `Conversations.put`
history compaction and the local read-only card inspection database. This is a
PM-equivalent local reconstruction, not a claim to have recovered the original
live request bytes. Its baseline has 60 cards: 19 Pokémon / 32 Trainers / 9 Energy.

At the starting commit, `agent_conversation.context` constructs 34,606 canonical
UTF-8 bytes. The main components are:

- Candidate sandbox: 18,407 bytes, including 12,922 bytes of candidates, 3,934 bytes
  of consensus, 904 bytes of repeated instructions and 338 bytes of competitive prior.
- Historical artifact projection: 5,807 bytes, duplicating current inventory.
- Card/competitive evidence: 5,568 bytes, overlapping candidate printed data.
- Current exact generated deck: 3,473 bytes.
- Bounded conversation history: 507 bytes. Old conversation is not the main cause.

Component numbers measure each value separately; JSON key/separator overhead
accounts for the remainder. The old loop removed eight optional card facts,
history and the artifact projection, but stopped at **23,641 bytes** against the
23,000-byte context limit. It never compacted the sandbox/consensus duplication.
The oversized packet was therefore refused before provider execution.

The existing proof-intent regex also matched `prove` inside **improve**. This
unintentionally opened sources for this ordinary strategic recommendation.
The matcher now requires whole words while retaining explicit proof/provenance requests.

## Priority and degradation behavior

`agent_context_budget.fit` projects a deep copy, leaving saved state untouched.
It measures the complete prospective context including hash/accounting overhead.
It does not raise the 23,000-byte context or 32,768-byte total provider-input limits.

1. Required: exact question, operation, current entries/counts, artifact ID and
   source-report hash, pending change set including its source identity/hash,
   construction constraints, selected printing/finish and workspace revision/window.
   Every supplied candidate ID stays available in its original retrieval order.
2. High value: consensus label/cohort/window metadata, shape, Energy mix and exact
   baseline ID/quantity vector; compact legal candidate identity/construction data.
3. Optional: historical turns, redundant ranking annotations, repeated printed
   facts and instruction text. Printed facts can be read locally by the existing
   fact-review boundary; omitted text is not authority for inventing mechanics.
4. Drop first: repeated evidence IDs, presentation URLs/timestamps/reference
   decorations, duplicate generated artifact/proposal inventories.

Under pressure the concrete order is: deduplicate presentation/provenance and
current artifact; compact candidate/consensus support; remove unselected duplicate
card evidence; remove older turns; omit verbose candidate printed text; omit
optional competitive support; remove other historical artifact projections.
Current task/state and pending proposal remain. At the last support tier the
selected-card fact and active workspace snapshot remain intact.

Only a packet that still cannot fit after these projections returns
`budget_exceeded` with bounded `context_diagnostics.condition=required_context_overflow`,
byte counts and `provider_called=false`. A process-local incident is retained for
the system follow-up. It contains no raw model output, exception text or credentials.
Provider transport and deterministic resolution/legality are unchanged.

## Exact-change PM-equivalent result

After adding explicit artifact hash and budget accounting, the same reconstructed
context starts at 34,690 bytes and compacts to **21,388 bytes sent to the fake provider**.
The main final components are sandbox 15,511; current artifact 3,556; evidence 681;
history 507; artifact projection 2; budget accounting 186 bytes.
The real local context retains printed candidate data and compact consensus; it
does not need the last-resort printed-text or competitive-support removal tiers.

Exactly one fake transport call returned a deterministic test proposal:

- Cut 1 Darkness Energy.
- Add 1 Fire Energy.

The server retained a `PROPOSED` change set tied to the original artifact ID/hash.
The original deck stayed unchanged until explicit local apply. Apply validated a
60-card deck, still 19/32/9, with no second fake call and no persistent store writes.
This proves wiring/state correctness, not live strategic recommendation quality.

## Local system routing and immutability

`agent_system_questions.respond` runs before card retrieval and provider
configuration. It handles the requested evidence-budget, refusal, consensus,
validated, proposal-only, data-source and sandbox questions. Narrow whole-question
matching avoids stealing ordinary card questions that mention a sandbox.

“What is the evidence budget?” returns a direct explanation of the 23,000-byte
context and 32,768-byte total input limits, task-first support trimming, and the
separate output-token allowance. Its response has no facts, sources, notices or
generated artifact and explicitly records `provider_called=false`.

“Why did that fail?” uses the structured context-budget incident when available;
without one it says the exact reason cannot be established. No deck-strategy
explanation is invented. Meta answers retain generated artifacts, pending proposal,
raw proposal state and quantities. A subsequent local recount returns the same
artifact and total. Conversation reasoning/history may advance as usual.

Ordinary recommendation no longer opens proof because of “improve.” Explicit
“Show me the evidence behind those changes” keeps `proof_requested=true`, exposes
available snapshot evidence and retains the pending change set. Existing fact
correction and empirical-claim exceptions are unchanged. No UI/hover files changed.

## Files and verification

- `agent_context_budget.py`: bounded support projection and explicit required overflow.
- `agent_system_questions.py`: local read-only product explanations.
- `agent_conversation.py`: current source hash, protected pending state, bounded
  incident, context fitter and whole-word proof intent.
- `agent_artifacts.py`: printed-fact review falls back to the authoritative current
  deck projection when its duplicate historical report has been removed.
- `agent_research.py`: local meta answers bypass provider configuration.
- `test_agent_context_budget.py`: production-path regression cases.
- This documentation file.

Focused final run: **150 passed**, two existing dependency warnings, external
connections blocked. Covers production exact-change/fake provider/apply under
optional pressure, all requested meta questions, required overflow and incident,
selected printing/active snapshot, pending proposals, recount/critique, consensus,
read-only protections, explicit proof and existing bounded repair.

Single final network-blocked backend gate: **965 passed / 9 unchanged baseline
failures**, 974 cases, 188.87 seconds, two existing dependency warnings. Failure IDs
match the starting candidate's JUnit report exactly:

- Five `test_confidence_is_not_discovery_wall` parameter cases (1/4/14/15/20).
- `test_composite_determinism_60_observed_only_and_validator`.
- `test_invalid_candidate_does_not_hide_valid_candidate`.
- Two `test_copy_exact_new_saved_preferred_unowned_and_immutable` cases
  (tournament/composite).

These older research/composite fixtures use out-of-rotation synthetic card data
rejected by existing Standard legality, as established in the preceding passes.
No unrelated fixture/legality correction or repeat broad gate was performed.
Gate includes Agent/provider/qualification/context/conversation, card-pool and
alternative retrieval, functional identity, competitive/research, Collection API,
Deck Builder and exact allocations. Frozen evidence/qualification files are
unchanged. `git diff --check` passed. No frontend tests/build were run because no
frontend files changed.

## Limitations and PM retest

Routing is deliberately a small deterministic product-question vocabulary, not a
general intent classifier. At extreme pressure some printed/competitive support
may be omitted; deterministic legality and identity checks still run against local
data. A truly oversized required context is refused explicitly. Conversation and
incident state remain process-local and expire with the existing session policy.

Minimum PM retest: on the valid recent-consensus Dragapult artifact, ask the exact
strategic-change question, inspect its Cut/Add proposal, ask the evidence-budget
question, recount, request sources explicitly, then apply the retained proposal.
Live strategic quality remains PM's assessment; no live QA was performed here.

The pre-existing `scripts/Start-Phase5-QA.ps1` user edits are preserved and excluded
from this correction commit. Working tree is task-clean apart from those edits.
