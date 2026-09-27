# Phase 7C.2 Pass 1 — deterministic deck/archetype foundation

Internal Python only. `build_profile(sources, revision=..., as_of=...,
archetype=..., window='30')` reuses certified read-only `Sources` snapshots,
collection identities, allocation checks and `Research.selected`. No API/UI,
provider integration, deck changes, recommendations or intent interpretation.

The frozen Pydantic Profile includes deck ID/revision/document hash, complete
functional composition and category totals, source printing/text references,
printed evolution-parent names and matching active-deck identities, Basic Energy
type counts, source-rarity ACE SPEC flags, population metadata/list references,
distributions and deviations, configuration hash and content hash. Printed parent
links are not a simulated evolution sequence. Missing rarity means ACE SPEC unknown.
Draw/search/acceleration/disruption/recovery roles are unavailable as semantic
categories; printed effects remain inspectable, without invented classifications.

## Population and arithmetic

Archetype is an explicit local research key, never inferred from a deck name,
card name or question. The window/as-of are explicit and reproducible. Only
existing resolved lists from the chosen main-Limitless archetype/window enter the
denominator. Missing current functional mappings are separately excluded. Results
without lists retain the existing all-cached-tournaments scope, not an archetype
denominator. No unseen lists are inferred. Functional comparison uses existing
`deck_identity`, including curated Basic Energy type identities; cosmetic
printing/finish choices do not create independent competitive cards.

Each eligible observation retains source URL, date, fetched-at metadata and a
content hash. The population hash covers the selected header, normalized vectors
and references. Exact active-vector matches expose cached player/event/date as
matching observations, never as proof of creator intent or deck-copy provenance.
Multiple matches remain multiple. All 159 list references are retained in the
representative profile; the compact packet carries a population snapshot reference
and the profile hash for resolution. Pass 2 must retain a way to inspect that
profile rather than treating the population hash as explanatory evidence alone.

Each card comparison includes zero-inclusive quantity buckets, active quantity,
eligible/included counts, positive-only mean/median, all tied modes and the
positive-only observed minimum/maximum. Full-precision ratios follow existing
analytics; threshold decisions use integer cross multiplication. Below 15 eligible
lists or with unknown archetype identity, rates/classifications are unavailable;
raw counts/distributions remain inspectable. Small samples do not become prevalence.

Research heuristics, not universal Pokemon truths: CORE >=80%; COMMON_PRESENT
active>0 and >=50%; UNCOMMON_PRESENT active>0 and <25%; COMMON_ABSENT active=0
and >=50%. Labels may overlap. Quantity deviations require a positive active count
strictly outside the included-list observed min/max. Equality is not a deviation;
absence is not BELOW_TYPICAL_QUANTITY. An unseen card has no typical range. This
conservative rule deliberately misses within-range differences, even if they differ
from the mean/mode. The complete statistics stay available for later bounded reasoning.

## Question selection and budget

`classify` uses bounded NFKC/case normalization, exact known-card name boundaries
and explicit phrase rules. Categories: DECK_OVERVIEW, ARCHETYPE_COMPARISON,
CARD_ROLE, CARD_QUANTITY, PRESENT_DEVIATIONS, ABSENT_CARDS,
MECHANICAL_INTERACTION, COMPETITIVE_CONTEXT, CREATOR_INTENT, UNKNOWN. Categories
can overlap. Ambiguous same-name functional cards remain multiple references;
unresolved names do not manufacture a card/archetype. This is not full NLP.

`select_evidence(profile, question)` always includes deck/population and an
available/unavailable deviation summary. Comparison ranks uncommon present,
common absent, quantity deviations, then three core orientation cards. Absence
questions lead with highest-inclusion common-absent cards. Resolved quantity
questions focus on those card identities and their distributions. Overview uses
Pokemon/printed evolution/mechanics, Energy, then Trainers; unsupported semantic
roles are explicitly unavailable. Creator-intent questions receive observable facts
only. UNKNOWN caps each optional category at two.

Core orientation uses inclusion descending, active count descending, identity;
evidence ranking ties use functional identity and kind. Caps: 12 composition,
10 comparison, 10 deviation, 6 mechanics. A deviation item is never emitted without
its comparison statistics. Classification and printed mechanics remain separate
DERIVED_FACT and SOURCE_FACT items; population/comparison is EMPIRICAL_EVIDENCE.
No interaction rulings or AI facts are synthesized.

The entire canonical UTF-8 packet, references, coverage and hash included, is
measured and bounded to 24 KiB, with 512 bytes reserved while selecting for omission
metadata. Budget/rank/intent/cap omissions are counted; mandatory evidence failing
the budget raises an explicit error. The full local profile is not a provider
packet and is not subject to that cap. The future 32 KiB envelope is only a named
planning constant. The existing 16,384-byte answer ceiling is untouched.

## Inspection and handoff

[Dragapult inspection](phase-7c2-dragapult/inspection.md) includes composition,
population, examples or explicit absence of deviations, selected evidence, size,
coverage and hashes. Its profile/packet JSON freeze the local revision-157 snapshot
as-of 2026-09-26, with a 30-day window; the underlying SQLite caches are not copied.
The internal `scripts/inspect_deck_research.py` accepts explicit local paths to
regenerate artifacts. No network is used. Frozen profile replay tests do not claim
to recreate databases from that derived artifact.

Pass 2 can consume this typed profile and bounded packet, adding explicit
archetype-context selection, profile-reference inspection and the existing Research
answer pipeline under separate approval. Do not infer that selecting a comparison
population proves the active deck belongs to it. No Pass 2, 7C.3, 7D, memory,
simulation, unrestricted research, new rules authority or provider routing is here.

Verification: 26 focused tests passed; one final established network-blocked
backend regression gate passed all 576 tests (the prior 550 plus 26 foundation
tests), with two existing dependency deprecation warnings. No frontend/browser,
live API/provider or network calls. `git diff --check` passed. Prior frozen
contracts/artifacts and retained evidence fixtures remain unchanged.
