# Recent archetype consensus baseline

Base: `12955ed23d105eeaa34a477622dfa871e356a6d9`, branch
`phase7c5-concrete-deck-resolution`. No live calls, ingestion, UI work, merge,
tag, certification, or Phase 7D work in this pass.

## Flow and source selection

Previously, the legal candidate sandbox ranked relevant competitive cards, but
the provider still invented all quantities. Generic new-build requests now enter
FINALIZE, retrieve a deterministic consensus where available, and send that list
alongside the existing ranked candidates. The returned artifact still passes the
existing functional resolver and Deck Builder validation. Discussion, exact cuts
and additions, local apply, recount and saved/active deck separation remain on
their existing paths. “Make those changes” is not treated as a new build.

The inspected local cache contains September 19 events 577 and 606, plus August
28 event 515. Source labels distinguish Dragapult, Dragapult Dusknoir, Dragapult
Blaziken and Dragapult Dudunsparce. No clustering is added. Source labels are
matched to the question; an explicitly longer variant label takes precedence.
Additional question constraints remain higher priority than the generic default.

Only resolved, complete, currently legal-mappable 60-card main-Limitless lists
qualify. Legacy functional keys map through the current functional index, merging
equivalent printings; ambiguous or unavailable mappings exclude a list. Future
events and events before the configured format start are excluded. The two newest
relevant usable events are selected first, with event ID breaking date ties.

Generic variant dominance is list count within that selected event pool, not
all-time count or placement weight. Explicit variants bypass dominance. Within
the selected variant, try Top 8, Top 16, Top 32, then the deepest cached qualifying
placement. Eight is the minimum; use every qualifying list in the first sufficient
band. Only after exhausting depth add one older event, recompute dominance for
that pool, and restart the ladder. Insufficient evidence is reported as such;
the existing candidate-ranking generation remains available.

## Allocation

Placement weights are winner 1.25, other Top 8 1.15, Top 16 1.05, deeper 1.00.
A winner cannot outweigh even two ordinary qualifying lists. Expected copies
are weighted copies divided by the total weight of **all** selected lists,
including zeros for absence. All calculations use exact rational arithmetic;
display values are rounded to four decimals.

The same cohort supplies Pokémon/Trainer/Energy totals and individual Energy
expectations. Largest fractional category remainders establish a 60-slot shape.
The allocator repeatedly takes the greatest remaining expected-copy deficit,
accounting for any required predecessor bundle. Each identity is capped at the
ceiling of its observed expectation. Category capacity, name-level four-copy
limits and ACE SPEC prevent illegal filling; Basic Energy uses existing identity
semantics. There is no unrelated-card or Energy padding fallback.

An evolution requires an available normal predecessor path, or a Basic ancestor
with printed Rare Candy infrastructure for Stage 2. Counts are not fixed ratios
or atomic packages. If greedy constrained allocation cannot complete 60, it
reports allocation unavailable rather than asserting a valid baseline. Only the
chosen variant contributes cards to this allocation.

The full baseline receives first candidate-packet priority for generic requests.
Explicitly requested cards receive priority for constrained requests. If the
baseline does not fit, it is not offered as an actionable complete baseline.
Current mechanics ranking still supplies deliberate alternatives and sparse-cache
fallbacks. No candidate/retrieval, legality, identity, or storage redesign occurs.

## Model role and persisted artifact

The provider receives the selected variant/events, sample size, placement band,
weights, shape, expected Energy copies, baseline quantities, candidate sandbox
and original question. For a generic request, natural explanatory prose without
an action block accepts the baseline. A full proposed list may replace at most
eight copies and must supply a rationale for a change. It must still preserve a
plausible evolution path and pass ordinary resolver/construction validation.
Excessive, unsupported or invalid deviations retain the baseline and replace
stale proposed-change prose with an honest notice. No additional model call is
needed to obtain the default list. Provider failure/truncation behavior is unchanged.

Explicit unusual card/engine/control requirements bypass the generic eight-copy
guard and remain subject to existing validation. This does not claim those builds
are competitively good. Subsequent recommendations use the existing retained
sandbox and exact-change state; they are not automatically reset to consensus.
Conversation artifacts retain their original source snapshot. No Collection or
Deck Builder state is written.

## Local Dragapult comparison

PM's previous live model artifact had 23 Energy, then 22 after critique. The new
read-only local reconstruction selected straight Dragapult `/decks/284`, events
606 and 577, Top 32, all 15 qualifying lists. Dominance in those events was 137
straight, 47 Dusknoir, 35 Blaziken and 2 Dudunsparce qualifying lists.

Weighted shape: 19.0096 Pokémon, 32.2596 Trainers, 8.7308 Energy.
Constructed shape: **19 Pokémon / 32 Trainers / 9 Energy**, exactly 60.
Energy: 3 Fire, 4 Psychic, 2 Darkness. Weighted expectations are 3.1314 Fire,
3.4615 Psychic, 2.0705 Darkness, 0.0673 Telepathic Psychic Energy.

The baseline includes 4 Dreepy, 4 Drakloak, 3 Dragapult ex, 4 Poké Pad,
4 Buddy-Buddy Poffin, 3 Ultra Ball, 4 Lillie's Determination and 3 Night Stretcher.
It includes a 1–1 Dunsparce/Dudunsparce path because those cards actually occur
inside the selected **straight Dragapult source label**, not because separately
labeled variants were mixed. No Patrat, Lunatone, or Alcremie filler was added.
Source labels are deliberately trusted; they are not assertions of perfect taxonomy.

The real cached list passed the existing production resolver/validator:
`VALIDATED`, 60 cards, no hard validation findings. Its assembled Research context
was 20,553 bytes, under the unchanged 23,000-byte context limit. This is local
deterministic validation, not a new live-provider quality result.

## Verification and limitations

Focused tests: 92 passed, two existing dependency warnings. Coverage includes
two-event start, depth-before-age, older-event ladder restart, all-list minimum,
variant selection, mild weights, exact fractional allocation/shape/Energy,
stranded evolution rejection, Rare Candy, reprint merging, production default
consumption, large-deviation rejection, explicit constraints, read-only state,
recount, existing ranking and exact-change/apply behavior.

One network-blocked backend regression gate: **938 passed, 9 failed**, two existing
dependency warnings. All nine failures match the already-established baseline
cases; no new failure appeared. This gate includes Agent/card-pool/context,
Limitless/archetype research, functional identity, generated state, Collection,
Deck Builder and allocation compatibility. It is not an all-green gate.
After a final predecessor-metadata budget adjustment, the affected consensus,
candidate-quality and candidate-selection checks passed **26 tests**. The broader
gate was not repeated. No frontend files changed, so no frontend build/tests were run.
Existing base already has nine research/composite-copy fixture failures caused
by regulation-mark-A fixtures claiming current Standard legality. They were
reproduced on the prior base and are not repaired by this task.

Logs: `.cache/consensus-focused-2.txt`, `.cache/consensus-budget-check.txt`,
`.cache/consensus-gate.txt` and `.cache/consensus-gate.xml`. Local production
reconstruction: `.cache/consensus-local-dragapult.json`. `git diff --check` passed.

Limits: this is cached international Standard coverage, not live freshness or
all events. The newest inspected events are September 19. Label matching is
deterministic and bounded, not general intent understanding. Greedy allocation
may fail where a more expensive combinatorial search could find a solution.
Rare Candy support is bounded printed-text/path recognition, not a universal
rules engine. Rationale presence is enforceable; strategic merit still requires
PM judgment. Explicit experimental builds can still have unusual ratios.
Finite candidate bytes can omit alternatives or prevent a complete baseline.

Backlog only: dynamic “off the rails,” weird/non-meta and creative-intent weighting.

## Changed files and PM check

- `src/pokelab/agent_consensus.py`: selection, averaging, allocation and deviation policy.
- `src/pokelab/agent_deck_sandbox.py`: baseline candidate priority and packet.
- `src/pokelab/agent_conversation.py`: new-build routing and baseline consumption.
- `tests/test_agent_consensus.py`: deterministic fixtures and production mock flow.
- This documentation.

Use a fresh conversation to build a Dragapult deck. Inspect the displayed 60,
Energy count, selected variant and reasoning; then request exact changes, apply
them and recount. Existing conversations intentionally retain their old packets.
No live QA call has been performed or authorized by this implementation pass.
The pre-existing `scripts/Start-Phase5-QA.ps1` edit remains excluded from the commit.
