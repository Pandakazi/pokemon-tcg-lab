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

Self-comparison: the current workspace/copy path does not retain a tournament-list
origin ID; local deck UUIDs and names are not source identities. An optional trusted
internal `active_observation` accepts the existing event/rank-derived research key.
It must resolve to a mapped local tournament observation with the exact active
functional count vector. If that validated identity occurs in the eligible
population, remove exactly that list and retain its excluded reference. If it is
outside the eligible population, report `not_present`. Without a verifiable ID or
when the active vector differs, retain all lists and report `unavailable` with a
reason. Identical compositions, even a unique match, do not prove origin identity.
No fuzzy matching or copy-persistence changes were added. Profile metadata records
the supplied ID, state, reason and excluded count; statistics/confidence use the
post-exclusion denominator. The representative snapshot has nine vector matches
but no retained source ID: self-exclusion is unavailable, population remains 159.

Each card comparison includes zero-inclusive quantity buckets, active quantity,
eligible/included counts, positive-only mean/median, all tied modes and the
positive-only observed minimum/maximum. Full-precision ratios follow existing
analytics; threshold decisions use integer cross multiplication. Below 15 eligible
lists or with unknown archetype identity, rates/classifications are unavailable;
raw counts/distributions remain inspectable. Small samples do not become prevalence.

Research heuristics, not universal Pokemon truths: CORE >=80%; COMMON_PRESENT
active>0 and >=50%; UNCOMMON_PRESENT active>0 and <25%; COMMON_ABSENT active=0
and >=50%. Labels may overlap. Quantity deviations require a positive active count
strictly outside the included-list typical band. Equality is not a deviation;
absence is not BELOW_TYPICAL_QUANTITY. An unseen card has no typical range. This
band is defined by `TYPICAL_MASS_PERCENT=80`: sort the n positive observations,
take one-based ranks max(1, ceil(10*n/100)) and ceil(90*n/100), and use those
observed quantities as inclusive lower/upper bounds. Integer arithmetic avoids
rounding drift; there is no interpolation or tie-breaking between equally common
quantities. Entire endpoint quantity buckets remain included, so actual coverage
can exceed 80% for discrete distributions. Sparse populations can legitimately
yield the full observed range, but it is not used as the definition of typical.
Observed min/max is preserved separately in `observed_range`; mean, median, tied
modes and full zero-inclusive distribution remain unchanged. Full extrema are no
longer the deviation rule because rare tails (including the active list itself)
can mask non-typical counts. Configuration version/hash advances to 2; prior-phase
contracts/hashes are unchanged. The representative deck still has no quantity
deviations under the corrected rule; none are manufactured.

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

Original Pass 1 verification: 26 focused tests and the 576-test backend gate passed.
Quantity correction: 35 focused tests passed, including tails, ties, sparse data,
zero-copy absence, exact exclusion, unavailable/changed identity and not-present
identity. One final network-blocked correction gate passed all 585 tests, with
two existing dependency deprecation warnings; `git diff --check` passed.
No frontend/browser,
live API/provider or network calls. `git diff --check` passed. Prior frozen
contracts/artifacts and retained evidence fixtures remain unchanged.
