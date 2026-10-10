# Consensus-first generation and read-only artifact immutability

Starting commit: `2ccc42bd86d3d1f391e9ece6848a2cd560d1bd9b`.
Branch: `phase7c5-concrete-deck-resolution`.
This supersedes the initial-build deviation policy in the previous consensus note.

## Established failure paths

The existing full Dragapult prompt fixture is:

> Create me a complete legal 60-card Dragapult ex deck and put it in list form.
> Make every slot an exact card, include category subtotals, and make sure the
> total is exactly 60.

Read-only execution of the **original commit's** sandbox and consensus functions
against the local inspection copy reproduced `candidate_budget_unavailable` and
`constrained=true` for this wording. The shorter “Build me a Dragapult deck” had
produced the available 19/32/9 baseline. There are two bypasses:

1. `agent_consensus.select` treated residual formatting words (`category`,
   `subtotals`, `exactly`, `slot`, etc.) as strategic constraints. That enabled the
   custom path, outside the generic deviation guard.
2. `agent_deck_sandbox.build` recognized the exact name **Dragapult ex** as a core.
   Its per-candidate ranking annotations consumed additional packet bytes, and
   constrained-request core/ancestor priority further affected available space.
   When the entire consensus did not fit, it set `candidate_budget_unavailable`
   and removed the actionable baseline cards. `agent_conversation.run` only used
   the baseline when its status was `available`, so ordinary provider generation
   and repair silently proceeded instead.

The eight-copy rule was backend-enforced by `permitted_deviation`, not merely a
prompt. But neither bypass entered that enforcement branch. The provider's list
could therefore reach `evaluate`, bounded repair and `remember` without being
replaced by the consensus. The deterministic consensus math did not produce the
reported 58/21-Energy artifact.

The historical provider response and unabridged live request were not retained
in the supplied evidence. Consequently, the exact historical entry-by-entry
58-card composition and repair sequence cannot be established here. The reproduced
paths explain how such a list could be accepted as an incomplete proposal; they
do not establish why the model chose each quantity.

The read-only corruption path is independently established:

- Original `agent_generated_changes.intent` returns `None` for the supplied
  “Why did you deviate from the recent competitive Dragapult consensus anywhere
  you did?” wording. Its discussion keyword list misses this sentence.
- `context` then omits the generated-deck sandbox/current-deck discussion context.
- An unexpected provider list reaches `evaluate`; candidate IDs with no allowed
  sandbox resolve as `outside_candidate_sandbox` in `Resolver.resolve_functional`.
- `remember` previously retained any list report, including zero resolved cards.
  There was no read-only storage boundary.

A deterministic local reconstruction using valid current candidate IDs but the
old no-sandbox envelope produced **0 resolved / outside_candidate_sandbox** and
replaced the retained report with zero. The precise historical raw output is
unavailable, but this is a reproduced integration defect, not a guess about card
legality or model intent.

## New generation boundary

Generic named build → recent consensus → existing production validation → exact
generated artifact → local conversational presentation. No provider reconstruction
or automatic deviation is involved, and the successful path reports
`generation_source=recent_consensus`, `consensus_status=complete` and
`provider_called=false`.

The original eight-copy helper and contract remain marked historical compatibility
code; production initial generation neither calls the helper nor sends that
contract. No automatic initial-build deviation remains. Keeping an unused helper
does not give a provider permission to replace the locally returned deck.

Custom intent uses affirmative constraints/style requests, not arbitrary leftover
presentation words. Explicit additions, unusual cards, aggressive/control/custom
builds still use the existing sandbox, provider and validation flow. A request
with no archetype specified is explicitly labeled `model_custom` with
`fallback_reason=no_archetype_requested`; it is not presented as a consensus.
Recognizing an explicit experimental request does not change any ranking weights.

Unknown, insufficient-sample, allocation, packet-budget and validation failures
return a visible explanation and structured `generation` state. No model fallback
is silently executed for a named generic build. Failed generation leaves an
existing conversational deck intact and records `generation_attempt` separately.

Ranking annotations are omitted only for already-determined consensus slots,
so they cannot displace the baseline they merely describe. The ranking algorithm,
candidate IDs, legality, event selection, variant dominance, minimum eight,
placement ladder, copy averages, shape and evolution allocation are unchanged.

## Read-only and presentation boundary

Read-only intent precedes build/finalize keyword interpretation for discussion.
Pending repair also rejects read-only requests, including critiques mentioning
“complete.” Genuine repair confirmations and explicit modifications keep their
existing paths.

The envelope marks `artifact_mutation_allowed=false`. Unexpected list/diff output
is ignored before evaluation, with bounded `read_only_artifact_ignored` diagnostics.
`remember` independently refuses mutation, and final conversation commit preserves
all previous artifacts and the previous proposal on a read turn. History may gain
the accepted explanation; deck IDs, hashes, quantities, pending changes and deck
referents do not change.

Discussion receives the current exact deck and original consensus snapshot.
A read-only projection removes unused alternative/ranking annotations to keep
the context bounded without changing the saved candidate packet. Known current
cards cannot be described as unavailable by the bounded presentation check;
validated artifacts cannot be called placeholders/unresolved. This is not a
universal semantic-entailment system.

When a deviation question concerns a current list that exactly equals its retained
consensus, the answer is local: no model-driven deviation occurred; fractional
source averages were allocated into a coherent 60. After actual modifications,
that shortcut no longer claims equality.

The large evidence section was also affected by missed discussion routing:
non-generated printed-fact reviews triggered `printed_fact_review`. Correctly
routed discussion retains the existing evidence-on-demand policy. Explicit proof,
material unresolved/corrective review and empirical claims still expose evidence.
The consensus source snapshot remains inspectable. No frontend files or hover
layout were changed.

## PM-equivalent local result

Using the full presentation-heavy Dragapult ex question and the inspected local
cache: **60 validated cards, 19 Pokémon / 32 Trainers / 9 Energy**; newest two
events, all 15 Top-32 lists from the selected straight-Dragapult label. Both the
initial build and “Why did you deviate from recent consensus?” complete with
`provider_called=false`. The follow-up leaves the entire retained artifact state
unchanged. Safe local result: `.cache/authority-local-result.json`.

## Verification

Focused work covered exact direct return, adversarial unexpected list blocks on
seven discussion forms, IDs/state/recount preservation, consensus equality,
evidence on demand, false unavailability/placeholder wording, storage-level
immutability, insufficient/invalid/unknown fallback, explicit constraints and
exact modify/apply. Existing repair, identity, factual review and conversation
checks were also exercised.

An expanded focused run had 165 passing cases and one custom-concept compatibility
failure. That case was corrected without changing the existing provider contract;
the final affected subset passed **26 tests**. Earlier focused state/generation
coverage passed **106 tests**. These overlapping counts are not additive.

One network-blocked backend gate: **952 passed, 9 failed**, two existing dependency
warnings, 188.11 seconds. The failure identities match the prior gate exactly;
there are no newly failing cases. This includes consensus/archetype, Agent
conversation/state/artifact, candidate sandbox, functional identity, Collection,
Deck Builder and allocation checks. The gate is not all-green. No frontend
tests/build were run because frontend files did not change.
The established nine regulation-mark-A research/composite-copy fixture
failures are outside this task; neither those fixtures nor legality is changed.

Logs: `.cache/authority-focused-final.txt`, `.cache/authority-targeted-pass.txt`,
`.cache/authority-backend-gate.txt` and `.cache/authority-backend-gate.xml`.
`git diff --check` passed. Ready for PM QA, not certification.

## Files and limits

Production: `agent_generation.py` (new local boundary), `agent_conversation.py`,
`agent_generated_changes.py`, `agent_artifacts.py`, `agent_consensus.py` (request
classification only), and `agent_deck_sandbox.py` (redundant packet annotations).
Tests: new `test_agent_consensus_authority.py`, updated `test_agent_consensus.py`,
plus two existing model-generation fixtures now explicitly requesting **custom**
generation (`test_agent_artifacts.py`, `test_agent_candidate_quality.py`). Their
resolution/count assertions remain unchanged; they have no usable consensus sample.
This report is the documentation change.

Remaining limits: cached evidence can be stale or incomplete; bounded intent
recognition is not unrestricted language understanding; presentation guards are
not universal prose verification. Existing corrupted in-memory sessions are not
silently reconstructed. Start a fresh PM conversation. Failed generic consensus
is now visible and may require data work or an explicit custom request.

No external network or live provider calls, storage writes to Collection/Deck
Builder, ranking/math redesign, simulation, dynamic creative weighting, Phase 7D,
merge, tag or certification. The pre-existing launcher edit is excluded.
