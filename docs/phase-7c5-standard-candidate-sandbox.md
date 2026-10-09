# Standard-legal candidate sandbox — PM QA candidate

Starting commit: `8bdec9ff53e3c4bef7ef4f2bc8ac5a73ea782a8e`.
Branch: `phase7c5-concrete-deck-resolution`. No certification or live calls.

## Before and after

Previously `agent_conversation.context()` supplied a few selected/mechanics card facts,
then the provider authored a full list from unconstrained knowledge. Only
`agent_deck_proposals.evaluate()` applied indexed legality. One repair could therefore
be asked to rebuild most of the list.

For FINALIZE/full Standard builds, context now prepares `candidate_sandbox` first.
`agent_deck_sandbox.legal_pool()` performs a read-only indexed query:
`gameplay_functions.standard=1`, joining each functional identity's canonical printing.
H/I/J legality remains owned by the existing Standard configuration and ingestion index.
No printing duplicates or raw provider legality claims establish eligibility.

`retrieval()` reuses existing mechanics `components`/`represent` and Pass 2
`RetrievalIndex.search`, supplying only the legal functional universe. The separate
research retrieval implementation and its scoring are unchanged. Core name matches,
legal evolution predecessors, Basic Energy, then role queries receive priority. Trainer
role queries balance draw/search/recovery/gust/switch/evolution/Energy/disruption;
mechanical queries also expose utility and unusual Pokemon. Remaining space can include
complementary types and other legal options. These are candidates, not a deck template,
strategic ranking or tournament recommendation.

## Provider input and validation

The packet has version/format, legal universe count, limitations, and up to 48 functional
candidates within a 14,000-byte candidate-list budget. Entries include functional ID,
canonical printing hint, exact name, role, and existing printed gameplay fields. Same-name
mechanically distinct candidates remain distinct; the printing hint can disambiguate.
The existing overall conversation/provider budgets remain unchanged. Optional evidence
and older conversation material are shed first; candidate entries are not silently
truncated mid-text. Insufficient overall space returns the existing budget failure.

The model still uses natural prose plus the existing generated_deck block (names and exact
quantities). It must choose supplied candidates, preserve the concept, and explain cache
limitations rather than invent cards. No tools, expansion loop or new network source.
Existing selected-card competitive/rules evidence may accompany a selected-card request;
no new Limitless lookup, freshness requirement, template averaging or ingestion change.

Resolved functional identities outside the supplied set are marked
`outside_candidate_sandbox`, omitted from totals, and prevent completion. Repair options
also use legal-only mechanics retrieval and are intersected with the same allowed set.
Existing name resolution, bad printing-ID normalization, canonical base printing,
name-level copy limit across distinct gameplay identities, ACE SPEC, Basic Pokemon,
exact 60, unresolved-slot and other construction checks remain authoritative. Existing
evolution-chain warnings remain warnings; no new universal evolution legality rule.

## Small repair only

At most one automatic repair. Eligibility requires total within eight of 60, at most
eight unresolved copies, at most eight excess ordinary name copies, and at most four
hard-validation messages. Otherwise record
`generation_failure_exceeds_small_repair` with zero repair calls. The incomplete artifact
is retained for local recount; a follow-up repair confirmation does not launch a massive
rebuild. A fresh explicit generation request is required. Draft-to-full generation remains
possible and is not mistaken for a bounded repair.

The repair receives structured failures/roles, resolved slots, and the same sandbox.
The returned artifact may add at most eight copies and remove at most eight copies;
larger edits return `repair_scope_exceeded`. The existing monotonic safeguard still
retains the better artifact. The historical Call Bell 24-to-23 case is now stopped
before the second call; an additional 59-to-58 fixture checks monotonic repair itself.

## Local coverage and limits

Read-only inspection of the existing isolated indexed cache copy found 2,045 legal
functional identities. A Dragapult ex build produced 39 candidates including
Dreepy/Drakloak/Dragapult ex, Cheren, Buddy-Buddy Poffin, Call Bell, Rare Candy,
Lana's Aid, Boss's Orders, Energy Retrieval, Glass Trumpet and Budew. This verifies
local eligibility/coverage, not deck strength or a successful live generated list.

Candidate count/text caps can omit legal options. Unknown or missing legal reprints and
missing evolution predecessors remain local-data limitations; the model cannot expand
outside the packet. Same-name distinct effects still require a valid hint. Legality does
not imply a viable strategy, and printed conditions still need model/user consideration.
No new index writes, collection writes, deck writes, runtime restart or provider calls.

Known separate PM polish blocker: raw inline `[fact_ids: "active-deck"]` metadata.
The hover/card layout and evidence UI are untouched.

## Verification

Nine new focused sandbox tests pass. They cover indexed legal-only deduplication,
Dragapult family/support, out-of-sandbox rejection, 59-to-60 repair, massive invalid
rejection without repair, repair edit bounds, monotonic retention, name-level copies
across distinct functional cards, and a tripwire forbidding legacy retrieval on builds.
Existing generated-card/repair tests were updated only where bounded membership or
small-repair semantics intentionally changed.

Final gate: 745 passed, 1 environment-sensitive existing qualification test failed
(out of 746). `test_free_gates` assumes the Gemini free-tier flag is absent, but the PM
runtime process supplied it. Clearing that flag only inside an isolated network-blocked
test process yielded 1 passed; no product/test implementation change was needed and no
broad gate was repeated. All sandbox/integration cases passed in the final gate.

Included passing groups: 381 research/card-pool/context tests; 45 Collection/Deck Builder
compatibility tests; 16 functional-index tests. Remaining tests cover Agent orchestration,
artifacts, resolution, card facts and frozen qualification behavior. `git diff --check`
passed. No frozen qualification artifacts or provider contracts were modified.
Frontend unchanged; no frontend test/build requested or run.

The pre-existing uncommitted QA-launcher quoting edits were preserved and excluded from
this implementation commit. They were present before this task began.
