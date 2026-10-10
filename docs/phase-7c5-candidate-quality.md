# Competitive candidate quality and bounded core ranking

Base: `909c4323b64bb374280777fad1f51b9224fc9663`.

## Previous selection and cause

The Standard sandbox resolved the core and ancestors, admitted all Basic Energy,
cycled through 15 generic lexical searches, then filled by type/functional ID.
It did not consult tournament evidence. Lexical match strength could prioritize
Cheren, Brock's Scouting, incidental attackers, and healing evolution packages.
Nine Energy types also consumed packet bytes before infrastructure selection.

## Small ranking overlay

The legal universe, candidate IDs, canonical printings, mechanics representation,
and construction validator are unchanged. A named-core build now reads the
existing `Competitive.evidence()` main-Limitless cache without ingestion or writes.
Existing gameplay_printings maps legacy observation identities to current identities;
only unambiguous mappings and currently legal candidates receive a boost.

An explicitly named cached archetype is preferred; otherwise observed core-card
inclusion identifies candidate archetypes. The strongest recency-weighted archetype
is used. Completed cached events only are eligible, respecting configured format
start. The window is 90 days ending at the latest matching cached event, with
weight `2 ** (-age_in_days / 30)`. This remains usable with an older cache; latest
event date, age, list count, event IDs, and small-sample status are exposed. Field
usage uses the latest cached field window separately. No average deck vector or
copy-count template is imposed, and weights are not prevalence claims.

The explicit score is:

- 100 × weighted archetype inclusion;
- 15 × weighted field inclusion;
- 18 for bounded direct core support (search, card flow, recovery, Energy support,
  or evolution support for an evolving core);
- 6 for gust/disruption/mobility, 8 for a shared represented mechanic;
- minus 16 for an unrelated evolution stage, or 24 for Stage 2;
- minus 8 for an attacking Pokémon whose printed type differs from the core.

The prior can outweigh setup penalties. These are lexical/structural heuristics,
not verified engine execution, tournament rankings, or optimality claims. Generic
damage/draw alone is not counted as a shared engine mechanic.

Core/family and relevant Basic Energy are retained first. A first pass reserves
coverage across search, draw, evolution, recovery, gust, disruption, mobility,
stadium, tools, Energy support, utility, and secondary attackers where available.
One multi-role candidate can satisfy several roles. A compact mechanical wildcard
may then occupy one slot; remaining capacity follows ranked support/staples.
Functional deduplication and already-covered roles reduce redundancy. The existing
48-candidate/14,000-byte candidate budget remains enforced; large cards or missing
local candidates can still limit coverage.

Basic Energy is justified by core attack costs, recent archetype usage, explicit
user types, or a selected relevant secondary attacker. When no named core exists,
the previous generic discovery fallback is preserved rather than inventing an
archetype. No dynamic creative-intent weighting was added.

## Local Dragapult comparison

Same read-only indexed local card snapshot, before versus after:

- Before: nine Basic Energy types; Cheren, Brock's Scouting, Patrat, Lunatone,
  split Milcery variants, and Alcremie ex occupied the bounded packet.
- After: Dreepy/Drakloak/Dragapult retained; Fire/Psychic plus Darkness justified
  by the cached shell. Search/consistency now includes Ultra Ball, Poké Pad,
  Buddy-Buddy Poffin, Lillie's Determination, and Fezandipiti ex; support includes
  Night Stretcher, Rosa's Encouragement, Unfair Stamp, Crispin, and Budew.
- After packet: 23 candidates, 13,944 candidate bytes. Prior: 159 mapped lists,
  three cached events, latest September 19, 2026 (21 days old at inspection).
- No exact tournament list is required. Some lower-confidence options remain.

## Visible exact changes

After retaining a validated generated-deck change set, the backend appends
`Cut: quantity × canonical name` and `Add: quantity × canonical name` paragraphs
directly from that structured proposal and sandbox. It then displays the existing
apply invitation. This does not parse prose or alter state, apply, recount, stale
protections, UI/hover layout, or Deck Builder/Collection persistence.

## Verification and remaining limits

Deterministic tests exercise recent versus old evidence, supported/unrelated setup
burden, role coverage under draw-card saturation, relevant/explicit Energy, a
creative candidate, and a mock 60-card build with eight Energy and no side-engine
filler. The fake build proves candidate availability and validation, not live model
strategy. Existing same-name predecessor alternatives remain available. One older
identity/fact test now explicitly names its mocked Pikachu/Lightning package so
its Energy is justified under the new filtering; its validation assertions remain.

No model calls, network retrieval, ingestion refresh, UI changes, construction or
identity redesign, Agent writes, merge, tag, certification, or Phase 7D work.
Strategic quality still depends on source coverage and provider choices. The cache
can be stale, lexical support can miss conditions, type is an imperfect synergy
proxy, and finite packet bytes can omit useful cards.

Backlog only: explicit “off the rails”/weird/non-meta intent may later reduce the
competitive prior and increase creative weighting. Not implemented here.

## Verification results and PM retest

- Focused generation/ranking/state tests: 81 passed, two existing dependency warnings.
- One network-blocked backend gate: 927 passed, 9 failed, same two warnings.
- All nine failed cases also fail on an isolated archive of exact base
  `909c4323b64bb374280777fad1f51b9224fc9663`. Seven are research-composite expectations
  and two are research-copy expectations. Their older synthetic cards retain
  regulation mark A while forcing `legal.standard=true`; current legality rejects
  them. This pass does not change those fixtures or the legality policy.
- The gate includes Agent, card-pool/context, archetype/Limitless research,
  functional identity, Collection, Deck Builder and exact allocation tests. No
  new failing case was observed. No frontend files changed or frontend build run.
- Logs: `.cache/quality-final-focused.txt`, `.cache/quality-backend-gate.txt`,
  `.cache/quality-backend-gate.xml`, `.cache/quality-baseline-failures.txt`.
- `git diff --check` passed. Pre-existing launcher quoting edits remain excluded.

PM should start a fresh generation conversation so it receives the new packet;
existing generated artifacts intentionally retain their original candidate sandbox.
Build Dragapult ex, inspect the resulting support/ratios, request exact changes,
check visible cuts/adds, apply them, and recount. No live call has been made here.

Changed files: `agent_candidate_quality.py`, `agent_deck_sandbox.py`,
`agent_conversation.py`, `test_agent_candidate_quality.py`,
`test_agent_generated_changes.py`, `test_agent_finalize_repair.py`, and this note.
