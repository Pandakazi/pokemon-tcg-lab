# Phase 7C.2 — Deck & Archetype Research

**CERTIFIED / PM PASS — 2026-09-27.** Mike approved implementation
`8744fcefff5e966f028865822bc2ff1debf80863` after final live PM retest.
This documentation-only closeout records that acceptance.

Annotated tag: `phase-7c2-deck-archetype-research-certified-2026-09-27`, targeting
the final closeout commit on canonical main. Preserve history through fast-forward
only and publish main, `phase7c2-deck-archetype-research` and the tag to
`https://github.com/Pandakazi/pokemon-tcg-lab.git`. Earlier tags remain unchanged.

## Certified capability

PokéLab answers bounded natural-language questions about the active deck using
deterministic composition/mechanics and explicit competitive archetype comparison
from the current locally synchronized dataset. The provider reasons over bounded
evidence; deterministic validation remains authoritative.

Supported: Active Deck and retained 7C.1 selected-card contexts; explicit cached
archetype selection; deck overview; archetype comparison; card-role/quantity
questions within available evidence; present/common/core/absence/deviation
evidence; comparison population provenance; false-premise safe rejection;
creator-intent boundaries; strict citation/grounding contracts and safe rejection
of violating answers. Facts remain distinct from plausible interpretation.

Read-only boundaries remain: no global Standard-card alternative search,
replacement recommendations, cut/add decisions, deck modification, inferred
creator intent, strategy-guide knowledge, simulation/self-play, matchup claims
from prevalence, research memory or actions. No automatic routing/retries/fallbacks.
Explicit provider/model and existing $0 controls remain.

The 15-list confidence threshold, 80% core / 50% common / <25% uncommon inclusion
rules, 80% typical quantity band, functional identity, comparison population rules,
24 KiB evidence / 32 KiB envelope budgets and existing Answer schema remain intact.
Overview prioritizes core evolution-line mechanics generically before support
mechanics under existing caps. Local guards cover bounded failure forms, not
universal semantic entailment; PM review remains necessary.

## Completed PM live QA

PM-reported results below are acceptance records, not invented response transcripts.
Active deck revision 157; explicit Dragapult comparison; 30-day window;
137 eligible lists during the comparison QA snapshot. This count is historical,
not a frozen production population.

- **Explicit comparison PASS:** without an archetype selection, comparison
  research requested explicit cached selection and made no provider call.
- **Creator intent PASS:** “Why did Rohit Potti build the deck this way?” correctly
  reported that creator intent could not be established.
- **Selected-card / 7C.1 compatibility PASS:** “What's the point of running Budew
  in this deck?” described supported damage/effect without unsupported Energy cost.
  Initial QA exposed “1 Energy”; local Budew `me02.5-221`, functional identity
  `bb71f052255398422b7dc659a97b9501`, quantity two, had Itchy Pollen name, 10 damage
  and Item-lock effect but no cost field. Evidence preserved that omission.
  The provider-added cost is now rejected; missing cost is not assumed free.
- **Archetype comparison PASS:** “How does this deck differ from typical Dragapult
  decks?” reported close alignment without notable quantity deviations, retaining
  population/window limitations. Common/core cards are similarities/context;
  zero detected deviations under thresholds does not establish literal identity.
- **Overview PASS:** “What is this deck trying to do?” surfaced Dragapult ex /
  Drakloak / Dreepy before Munkidori/support mechanics after generic ranking
  corrected identity-order displacement under the mechanics cap.
- **False-premise grounding / safe rejection PASS:** “Why is this deck built around
  Charizard ex?” initially exposed uncited composition facts in limitations.
  Direct deck/card assertions and claims that a premise contradicts deck contents
  now require cited claim placement; genuine epistemic uncertainty stays permitted.
  Final live retest parsed and passed schema validation but failed the deterministic
  answer/citation contract. The UI safely showed “The response did not meet the
  answer or citation contract. No answer is shown.” No rejected answer, provider
  message or exception was exposed; no retry occurred. PM accepts this as PASS:
  validation rejected unsupported factual claims instead of presenting them.
- **Alternative-card boundary PASS:** with Budew selected, “Is there another card
  that stops players from using tools?” returned insufficient evidence without
  global card-pool search or fabricated alternatives. Phase 7C.3 remains excluded.

## Preserved implementation and verification history

- Pass 1: `38ebe80fc53541a303b4a82ef65e717b7ca25ed3`.
- Quantity correction: `25678713afe0a5585dfa45d8cd05b880d2a41ceb`.
- Pass 2: `f02a43329ed1ee1c285c82cea991dc8eda1d5503`.
- Live-QA correction: `139af524bcde6eae4049e329ea7b0140f5efbd41`.
- Final limitation correction: `8744fcefff5e966f028865822bc2ff1debf80863`.

Latest deterministic verification before certification: 15 exact-sentence cases,
185 affected validation tests and one full network-blocked backend gate with
755 passing tests. `git diff --check` passed. The final corrections were backend
only; frontend/build were not rerun unnecessarily. Pass 2 TypeScript/build passed.
Closeout does not rerun suites, restart QA or invoke any provider. See the
[integration record](phase-7c2-pass2.md), [QA corrections](phase-7c2-live-qa-corrections.md)
and [final limitation investigation](phase-7c2-final-limitation-retest.md) for
historical implementation details; this document records final certified behavior.
Prior 7A/7B qualification artifacts and prior certification milestones are preserved.

## Non-blocking limitations / backlog

- Workspace copies lack source-list origin IDs; exact self-comparison exclusion
  may be unavailable.
- Newly synchronized archetype choices may require page reload.
- Provider prose may remain conservative/robotic.
- Safe rejection can occur where better provider output could provide a useful
  cited false-premise correction.
- Deterministic guards are bounded, not universal semantic entailment verification.
- Overview/research quality may improve with future strategy/piloting knowledge.
- Current comparison data means current through PokéLab's most recent successful
  local competitive-data synchronization, not a live fetch at question time.

These are not certification blockers and were not implemented during closeout.
Phase 7C.3 and Phase 7D have not begun.
