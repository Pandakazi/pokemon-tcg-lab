# Phase 7C.2 PM QA corrections — retest pending

Starting commit: `f02a43329ed1ee1c285c82cea991dc8eda1d5503`.
Investigation used local SQLite stores, the existing revision-157 fixture and
deterministic reconstruction only. No network, live provider call, runtime
restart or historical raw-response recovery was performed.

## Budew: exact local trace

- Active workspace revision: 157; two Budew allocated to `me02.5-221`, holo.
- Functional/deck identity: `bb71f052255398422b7dc659a97b9501`.
- Raw local cards SQLite representation (also returned by the collection catalog):

```json
{"name":"Itchy Pollen","effect":"During your opponent's next turn, they can't play any Item cards from their hand.","damage":10}
```

There is **no cost property**. This local record cannot establish either one
Energy or a free attack. We did not use outside knowledge to fill that gap.
The source data was not edited or coerced into a numeric cost.

The 7A builder copies `raw['attacks']` into the selected card's `printed` field.
The 7C.1 envelope preserves it, as does the deck-profile mechanics extraction.
Exact selected-card evidence ID in the reconstructed envelope:
`ev-0e507ccb7979021d`, provenance `ref-790bbf53e5832e14`.
The attack FieldValue is:

```json
{"field":"attacks","value":"[{\"damage\":10,\"effect\":\"During your opponent's next turn, they can't play any Item cards from their hand.\",\"name\":\"Itchy Pollen\"}]"}
```

The provider receives that same canonical field, with no added attack cost.
The existing frozen Budew envelope hash remains
`991a77f9439050275916f1933a169b7a5d886a4b1874c601e3381d9a2eb819f1`.
This is a local reconstruction, not a recovered capture of the live transaction.

**Established cause:** the PM-supplied answer added “for 1 Energy” without support
in the locally reproduced evidence. Extraction/serialization did not manufacture
that number. The former validator checked structure and citation membership, but
did not check the added cost assertion. Whether the source omission convention
means a free attack is not established by the permitted local evidence.

**Correction:** provider wording now distinguishes omitted/null costs from an
explicit empty cost array. A bounded deterministic product guard rejects direct
numeric/free-cost claims about named supplied attacks unless cited attack data
explicitly supports them. Missing cost stays unknown; explicit `[]` supports zero.
No source, evidence fixture, identity or Answer schema changed.

Tests use the exact Budew fixture, reject the PM sentence and unsupported zero/free
variants, accept its supplied damage/effect without an invented cost, test explicit
zero/nonzero synthetic costs and require supporting citations. A fake-provider
test verifies one call, preserved safe execution metadata, no answer/raw-output
leak and bounded `unsupported_attack_cost` diagnostics.

## Comparison: framing, not missing evidence

Same local revision-157 snapshot, as-of 2026-09-27, 30-day explicit Dragapult
population: 137 eligible lists. Both before and after selection contain 22 core,
25 common-present, **zero** uncommon-present, common-absent, above-typical and
below-typical labels. The complete deviation summary precedes capped examples.
Poké Pad, Dreepy and Buddy-Buddy Poffin remain orientation/similarity examples.

Before/after packet is identical: 13,556 bytes, hash
`f866165b5982bccdbb2a22043c86051fc252b6f1b3b1d328be0e466a85b7420f`.
No thresholds, population calculations or comparison retrieval changed.

The prompt now requires answering the requested difference from that summary
first, distinguishes core/common from deviations, and states that zero detected
deviations under thresholds does not establish literal identity, equal strategy
or performance. Similarities may follow as context. A narrow guard rejects common
explicit difference/identity assertion forms when the available full summary has
zero deviations. Deterministic/fake-provider tests cover acceptance of bounded
no-deviation answers and rejection of those unsupported forms.

## Overview: generic priority before the existing caps

Previously all active Pokémon shared the same overview priority, with functional
identity breaking ties. The six retained mechanics were Fezandipiti ex, Munkidori,
Dreepy, Dunsparce, Budew and Meowth ex. Dragapult ex was omitted.

Now core active evolution endpoints and their active ancestors precede support
mechanics. Lines rank by linked-line size, then aggregate active copies, then
stable identity. This uses explicit core/evolution data, not archetype-name
matching or an inferred strategy. Referenced-card priority and comparison
selection remain intact. The new six are **Dragapult ex, Drakloak, Dreepy**,
Fezandipiti ex, Munkidori and Dunsparce.

- Before: 22,868 bytes;
  `686748357c78cd8dc915cbd7b45e2537d1ece6a01652373b0bd02a0504fd6ca4`.
- After: 22,862 bytes;
  `4bfcd9e81d9cf610d4dc033474c8227c07bd20f6d2c9747fa9e05240862b2dd5`.

Six-mechanics/12-composition caps and 24 KiB packet budget are unchanged. Two
unrelated synthetic evolution lines prove endpoint/ancestor priority over eight
support Pokémon under the cap. Without qualifying core/evolution evidence, the
existing fallback priority remains; no primary strategy is invented.

## Limitation hygiene and bounded validation

The earlier prompt already prohibited uncited positive claims, but its validator
only checked limitation length/nonblank text. Negative facts could escape too.
Wording now explicitly places presence/absence facts in cited claim arrays.
A deterministic guard rejects direct deck/named-card assertion forms in
limitations, including “The deck contains no Charizard ex”, while accepting pure
epistemic boundaries and explicitly uncertain embedded propositions.
Diagnostics expose only `uncited_limitation_claim`, not rejected prose.

These lexical guards address known failure forms. They do **not** prove arbitrary
natural-language entailment or catch every paraphrase. PM semantic review remains
required. Internal assessment exceptions retain their existing safe classification.
The Answer schema, transport, zero-cost gates, budgets and no-retry/fallback
policy remain unchanged. No frontend code changed.

## Verification

- 28 new correction cases, including exact Budew, explicit cost semantics,
  citation support, limitation hygiene, comparison framing and generic ranking.
- Focused backend set: 151 passed.
- One complete network-blocked backend regression gate: 740 passed; two existing
  Starlette/FastAPI deprecation warnings. A launcher argument error was corrected
  before any final-gate tests were collected; the completed gate ran once.
- Frontend/TypeScript/build not rerun because no frontend files changed.
- `git diff --check` passed. Prior qualification fixtures/artifacts, certification
  tags, main, comparison configuration and math remain unchanged. Only the
  authorized overview evidence priority changes Pass 1 selection behavior.

## Minimal PM retest

After restarting the existing configured QA runtime, authorize only these four
submissions, with the same deck and 30-day window:

1. Select Budew `me02.5-221` holo: “What's the point of running Budew in this deck?”
   Check no unsupported cost, or a safe contract rejection if one is invented.
2. Clear card; select Dragapult comparison: “How does this deck differ from typical
   Dragapult decks?” Check the current summary is answered directly, similarities
   labelled as such, and no literal-identity claim.
3. “What is this deck trying to do?” Inspect primary-line mechanics and cited
   interpretation; no invented pilot intent.
4. “Why is this deck built around Charizard ex?” Check correction facts are cited
   and limitations contain only uncertainty/scope boundaries.

New local syncs/date windows may change comparison counts; judge against the
captured current packet, not the historical count of 137. Do not retry failures
automatically. No certification, merge or tag is authorized by this pass.
