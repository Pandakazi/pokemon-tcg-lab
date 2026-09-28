# Phase 7C.3 Pass 1 — Standard mechanics discovery

**READY for Pass 2 design review; not a retrieval implementation or certification.**
Starting point: `100b0036a2f78abee2a61ad213cb07de63558a5e` and unchanged
`phase-7c2-deck-archetype-research-certified-2026-09-27`.
Branch: `phase7c3-alternative-card-research`.

## Corpus definition and provenance

Discovery reads the actual locally synchronized `cards.sqlite3` using an explicit
read-only SQLite transaction. It never initializes, repairs or writes the source.
Selection requires indexed `game='tcg'`, indexed `standard=1`, and raw
`legal.standard=true`. Explicit non-English language values are excluded; missing
legality is never inferred from regulation marks. Pocket is excluded.

English provenance comes from the existing sync's
`https://api.tcgdex.net/v2/en/cards` endpoint. All 3,345 selected records lack an
explicit per-card language field; this is an ingestion-provenance assumption,
not a language detector or independently verified translation status.

- Cache rows inspected for selection: **23,736**.
- Selected Standard printings: **3,345**, representing **2,092** conservative
  functional identities using the existing `functional_signature`/SHA-256 rule.
- Pokémon: **2,584**; Trainers: **445**; Energy: **316**.
- Excluded: 17,911 non-Standard TCG records and 2,480 Pocket records.
- Source regulation marks: G 1; H 1,303; I 1,278; J 469; absent 294. The G record
  is included because the source explicitly marks it Standard; no rotation rule
  was substituted for the source flag.
- Last successful sync: **2026-09-23 02:39:38.770017 UTC**. Card checked-at range:
  02:34:37.564096–02:39:18.155629 UTC that day.
- Source-record parsing failures: **0**; indexed/raw legality disagreements: **0**.
- Corpus manifest hash:
  `bd069ccc10964e13c127f97ab318cca018933ca18f1f3b3e5c18c94643d08581`.

This means Standard according to this local source snapshot, not an assertion
that online legality/catalog completeness was current on September 27. No refresh
or external lookup occurred. Functional IDs are inventory metadata only; Basic
Energy deck identity and collection/deck storage were not changed or consulted.

## Representation

`mechanics_discovery.py` is an isolated offline module with no API, provider,
Agent, ownership or competitive dependencies. The analyzer calls existing pure
functional identity logic; no shared implementation was edited.

Each **Effect** records exact printing and functional identity; source category;
component type/index/name; original and normalized rules text; source URL,
checked-at and full card hash; original component fields as canonical JSON;
ordered atoms; candidate taxonomy IDs; unmatched text spans; source omissions;
and unresolved-scope flags. Attack, Ability, Trainer, Energy and other/rules
components are retained separately. Attack damage fields remain independently
represented even when an attack has no effect text.

Each **Atom** records an extensible action string, exact normalized source span
or explicit structured-field provenance, textual order and predecessor, object
phrase, quantity phrase, direct affected-player/from-zone/to-zone phrases when
present, optionality, polarity, source context and scope status. Unsupported
dimensions remain null/unknown. Printed attack cost stays in the original
component JSON; missing cost is never converted to zero. Context retains
conditions/timing/restrictions without claiming their execution scopes are parsed.

Normalization is NFKC, case-folding, apostrophe normalization and whitespace
collapse. Original text is also retained. No card name or archetype is used to
infer effects. No latent model or semantic embedding is involved.

Multiple actions retain distinct atoms. For example, an Energy discard followed
by draw produces separate `discard` and `draw` atoms. Actual Ninetales `me01-020`
preserves self-mill followed by conditional effect copying; Clefable `me02.5-075`
preserves choosing an attack and using it as this attack. The relationship is
explicitly **text order, not proven execution order**. Choice/cost/condition and
pronoun scope remain unresolved rather than invented.

The parser only calls a small literal draw grammar or numeric damage-only
component `represented_simple`. Even that describes extraction, not complete
gameplay execution or legality. Other matched effects stay `partial`.

## Taxonomy and breadth

The machine-readable `mechanics_taxonomy.json` contains **90 candidate concepts**,
of which **87 are observed** through action/span matching in this snapshot.
Every concept is a lexical discovery candidate, not a guarantee of functional
equivalence. The taxonomy is layered over atom evidence and is never a retention
or future eligibility filter.

Twelve families: resource movement/provision; board development; damage/counters;
control; defense; Prize game; information; copy/transform; Special Conditions;
game-object qualifiers; chance; Knock Out instructions.

Corpus-driven additions beyond the initial checklist include Energy provision
versus attachment, attack-cost modification, damage-counter multiplication, HP
modification, Ability usage limits versus global suppression, and Tool
nullification versus removal versus play restriction.

Representative real Standard examples, also covered by deterministic tests:

- Opponent mill: **Spiritomb `me01-087`**, discard the top card of the opponent's deck.
- Self-mill / conditional effect copying: **Ninetales `me01-020`**, own top-card
  discard followed by use of a Supporter effect if applicable.
- Item restriction: **Budew `me02.5-016`** and exact QA printing `me02.5-221`.
- Tool removal: **Spearow `me01-102`**; Tool nullification: **Jamming Tower
  `me02.5-261`**. These are not collapsed into Item lock.
- Damage-counter movement: **Munkidori `me02.5-099`**; multiplication:
  **N's Vanilluxe `me02.5-051`**.
- Bench damage: **Stonjourner `me01-081`**; spread: **Kyogre `me01-034`**.
- Energy acceleration: **Mega Lucario ex `me01-077`**; opposing Energy removal:
  **Centiskorch `me01-030`**; Energy provision: **Meganium `me01-010`**.
- Pokémon/Energy recovery: **Night Stretcher `me01-173`**.
- Hand disruption: **Scraggy `me02.5-134`**; gust: **Bayleef `me01-009`**.
- Ability suppression: **Team Rocket's Watchtower `me02.5-210`**. **Phantump
  `me04-038`** instead has a self-use timing restriction; tests keep them separate.
- Prize access: **Lt. Surge's Bargain `me01-120`**; Prize reduction:
  **Shedinja `me01-061`**.
- Attack copying: **Clefable `me02.5-075`**; healing: **Mega Venusaur ex
  `me01-003`**; prevention: **Snom `me01-042`**; Poison: **Tangela `me01-006`**.
- Devolution: **Strange Timepiece `me01-128`**; Stadium removal:
  **Mamoswine `me02-025`**; Future interaction: **Iron Thorns `sv05-062`**.
- Weakness change: **Lillie's Clefairy ex `me02.5-076`**; type change:
  **Carbink `me02.5-117`**; attack-cost modification: **Counter Gain `me02.5-186`**.

**No Lost Zone wording, explicit alternate win/loss wording, or explicit
can't/cannot-search wording was observed.** This is a source-pool observation,
not a claim that such mechanics do not exist elsewhere. A clearly synthetic test
proves Lost Zone movement can be represented; it is not counted as corpus evidence.
Three candidate labels were unobserved: explicit deck-to-discard phrasing, Lost
Zone movement and counter removal. Counter movement/prevention are distinct.

The coverage checklist and additional text audit explicitly investigate Rule Box,
ex, Ancient/Future, Tera, Team Rocket, Technical Machine, Tool, Stadium, Prize,
Weakness/Resistance, Special Conditions, bench capacity, stall/lock and copying.
Audit occurrences are **not semantic matches** (e.g. attack-damage boilerplate
may mention the Bench). They expose further review candidates without claiming
an ability that the atoms do not establish.

## Phrase mappings and distinctions

- `put` / `place` damage counters are placement cues; `move` counters stays separate.
- `can't` / `cannot` express related restrictions; the affected action/card class
  remains distinct. Self-use caps do not become opposing Ability suppression.
- `switch ... with`, `switch out ... to the Bench`, and `switch in ... to the
  Active Spot` remain related but preserve affected player and chooser text.
- Top-of-deck discard is mill only with explicit deck/controller wording; own deck,
  opposing deck, hand discard and Energy removal have separate concepts.
- Explicit deck-to-discard movement is a supported candidate phrase but unobserved
  here; the artifact does not falsely claim a corpus attestation for that synonym.

## Measured coverage — lexical extraction, not semantic accuracy

All **5,180 components** are retained. **4,886** have usable text and/or a printed
damage field. **3,646** have rules text, across **2,705 printings**, with **1,362**
distinct normalized texts. Alternate printings remain in the primary denominator;
functional identity and unique-text counts expose that duplication.

- At least one atom: **4,834 / 4,886 (98.94%)**.
- At least one candidate taxonomy concept: **4,798 / 4,886 (98.20%)**.
- Text-bearing components with a text-action atom: **3,500 / 3,646 (96.00%)**.
  This separate measure avoids crediting printed damage as parsed effect text.
- Simple extraction only: **1,269**; **partially represented: 3,565**.
- Usable effects with no atom: **52**; with no taxonomy concept: **88**.
- Unresolved condition/choice/reference/compound flags: **3,249**. These are
  parser uncertainty flags, not a claim the English is inherently ambiguous.
- Components lacking both text and damage: **294** (Energy source omissions).

Breakdown (usable / atom / taxonomy / partial / no-atom):

- Attacks: **3,830 / 3,812 / 3,801 / 2,548 / 18**.
- Abilities: **589 / 558 / 539 / 558 / 31**.
- Trainers: **445 / 442 / 436 / 437 / 3**.
- Energy effects: **22 / 22 / 22 / 22 / 0**, plus 294 without effect text.

These high candidate-coverage figures must not be used as semantic precision,
recall or gameplay completeness claims. There is no human-labeled full-corpus
gold standard, and broad lexical context can include triggers or qualifications
rather than an action executed by the card. Pass 2 must inspect those boundaries.

## Unknowns, partials and source gaps

Every unknown retains full original/normalized text and stable component identity;
unmatched spans are preserved, not replaced by a meaningless OTHER label.
Examples of remaining unclassified wording include conditional passive Knock Out
on Mega Absol ex `me01-086`, granted attack use on Core Memory `me03-070`, counter
movement prohibition on Patrat `me04-070`, and attack-effect bypass on Walking
Wake ex `sv05-050`. These remain available to future text-based retrieval now.

Partial examples include conditional copying, Munkidori's optional conditioned
counter movement, and multi-step search/reveal/put/shuffle. The artifacts preserve
all qualifiers and do not infer hidden pronoun targets or strategic equivalence.
`rare-effects.json` inventories wording limited to a single functional identity;
`summary.json` also inventories atom sequences occurring on at most two functional
identities. Rarity is local corpus frequency, not tournament relevance.

**2,185 components across 1,780 printings** have at least one source omission:
13 omitted attack costs; 642 omitted attack damage fields; 1,534 omitted effect
texts (1,240 attacks plus 294 Energy). Categories overlap. An omission is not
necessarily a corrupt card: effect-only attacks and simple damage attacks may
legitimately omit different fields. Missing Energy text is not silently filled
with Basic Energy rules. No cost/damage omission is interpreted as numeric zero.
There were zero source-record JSON/shape failures in this actual corpus.

## Artifacts and reproducibility

- `phase-7c3-mechanics/summary.json`: provenance, all coverage breakdowns, taxonomy
  frequencies, unobserved concepts, examples, source issues and rare sequences.
- `effects.jsonl.gz`: every Effect/Atom as canonical UTF-8 JSONL, deterministic gzip
  timestamp zero. Unknown and missing components are included.
- `cards.json.gz`: every selected printing, functional identity and source metadata.
- `coverage-examples.json`: bounded readable unclassified/partial/missing examples.
- `rare-effects.json`: full rare-wording inventory.
- `src/pokelab/mechanics_taxonomy.json`: versioned machine-readable concepts,
  patterns, phrase relationships and coverage audit definitions.

Regenerate locally with the existing Python environment (no network):

```powershell
$env:PYTHONPATH = 'src'
& 'C:\Users\Mike\Documents\pokemon-tcg-lab\.venv\Scripts\python.exe' `
  scripts/inspect_mechanics.py `
  --cards 'C:\Users\Mike\Documents\pokemon-tcg-lab\data\cards.sqlite3' `
  --output docs/phase-7c3-mechanics
```

Run from this branch's repository root. New local source data naturally changes
the manifest/hash/artifacts; no new taxonomy label is required to retain a novel
effect. This command is an offline analyzer, not a user-facing search endpoint.

## Verification and Pass 2 recommendation

**47 focused mechanics tests passed**, including actual Standard examples,
compound ordering, mill direction, cost omission, unknown preservation, all-source
artifact hashes, duplicate IDs, malformed components, read-only SQLite and
determinism. **44 existing card-data/functional-identity tests passed.** A real
Clefable example exposed choose/use overlap during testing; the split was fixed
and the complete mechanics suite passed afterward. `git diff --check` passed.
No existing runtime implementation changed; packaging includes the new taxonomy
JSON. No broad backend gate was justified by this isolated discovery addition.
An offline wheel build verified that the taxonomy JSON is packaged. A fresh
full-corpus analysis reproduced the stored corpus/taxonomy/effects hashes and
left the source SQLite file byte-for-byte unchanged.
No frontend/TypeScript/build tests, providers or external network calls occurred.

Recommended Pass 2 design: build a versioned local index over **all** component
text and source properties; union literal/phrase, atom and concept candidates;
deduplicate for display by existing functional identity while retaining exact
printing/source links. A concept match should boost or explain a candidate, never
determine eligibility. Unknown text candidates must remain reachable. Ownership
and tournament popularity must not gate discovery.

Keep matching explanations tied to exact spans, preserve affected player/zone,
surface unresolved conditions/costs/choices, and distinguish related effects from
substitutable cards. Build a reviewed retrieval evaluation set before claiming
precision or enabling provider interpretation. Any later runtime refresh should
rebuild or invalidate by source/config hash rather than ship frozen artifacts.

No blocking PM question for design review. Later product decisions include how
visibly to label partial/text-only candidates and the source freshness policy for
external Alpha. No alternative search, Agent integration, recommendations, writes,
UI, embeddings, new ingestion, 7D, merge, tag or certification was implemented.
