# Generated-deck conversational state

Base: `f78e944eec6d2531aa0d395d278634abd2ba85d3`.

## Established causes

`agent_conversation.context` supplied historical artifacts but had no explicit
current generated-deck target. `agent_hybrid.parse` accepted a change block only
when the active workspace deck was included. `agent_deck_proposals.evaluate`
evaluated diffs against that workspace, not the generated artifact.

Exact-change critique entered RECOMMEND; without a usable structured block,
`agent_artifacts.present` emitted `missing_artifact`. This did not mean the prior
generated list had disappeared. “Make those changes and show ... list” matched
`recount_target` and returned the original stored list without applying anything.

## State and boundaries

`agent_generated_changes.intent` selects discussion, recommendation, or apply for
the current generated artifact. Explicit active/saved-deck or subject switches
suspend this default; explicitly referring to the generated/your-own deck restores
it. New generation replaces the current artifact. This is bounded intent dispatch,
not extraction of edits from prose.

Discussion receives canonical names, IDs and quantities without requiring actions.
Exact recommendations reuse the existing proposed_deck_changes block. Every change
must identify a sandbox candidate, cuts must exist in sufficient quantity, and a
composed full list goes through the existing resolver and construction validation.

Conversation-local `proposed_change_set` stores:

- `id`, `type`, `status: PROPOSED`;
- `source_artifact_id`, `source_artifact_hash` (hash of the retained report);
- `proposal`: existing typed diff, including candidate-ID/quantity removes/adds;
- `reasoning`, `validation_status`.

A new recommendation supersedes the previous one, including when no valid change
set is produced. “Do that” and other apply referents require the current source ID
and hash. Missing, stale, applied, or multiple pending sets ask one clarification.
No arbitrary conversation prose supplies edits. A source deck replaced after a
proposal cannot receive that stale proposal.

Apply revalidates against current local card data. Fully valid changes need no
provider call. Only an existing eligible pure deficit (at most eight copies) may
use the existing additive completion. Failed completion retains the original.
Successful application stores generated B and marks the proposal APPLIED; recount
then returns B. Neither path writes Collection or active/saved Deck Builder state.

## Presentation

Ordinary explanation no longer treats every occurrence of “why” as a request for
a source dump. Explicit proof/source/data requests and standalone “Why?” retain
proof behavior. Routine printed-reference review remains available without opening
the large source section for generated-deck discussion; unresolved factual review
and empirical warnings still surface. Existing Show sources and hover UI are intact.

Visible `[card-...]` and `[fact_ids: ...]` annotations are removed. An adjacent card
label with an established evidence ID is rendered using its canonical name (tested
with Grand Trumpet → Glass Trumpet). Unannotated invented aliases are not fuzzily
rewritten: this is intentionally not universal entity recognition or entailment.

## QA and limitations

Focused tests cover discussion/explanation, exact proposals, six apply phrases,
unchanged workspace files, local recount of B, stale/ambiguous/superseded proposals,
phantom/excess cuts, explicit active-deck context, identity labels, evidence requests,
and successful/failed small-deficit completion. Existing generation, completion,
functional identity, legality, ACE SPEC/copy limits, Collection and Deck Builder
tests are included in the final offline gate. No frontend files or hover layout change.

Verification: 112 focused conversation/artifact/completion tests passed; the final
18 new state-chain cases passed after the last refinements. The single external-
network-blocked backend gate passed 791 tests (two existing dependency deprecation
warnings). `git diff --check` passed. Logs: `.cache/generated-focused3.txt`,
`.cache/generated-final-focused.txt`, `.cache/generated-backend-gate.txt` and XML.
The pre-existing uncommitted launcher quoting edits are excluded from this change.

PM retest: generate a 60-card deck, explain it, request exact cuts/adds, apply those
changes, recount, and critique the updated deck. Request sources explicitly. Verify
the active Deck Builder deck is unchanged and repeating “Do that” cannot reapply.

Candidate ranking, role balance, and the known strategically weak candidate pool
remain unchanged. All verification uses mocks/local data; no live calls, network,
merge, tag, certification, or Phase 7D work.
