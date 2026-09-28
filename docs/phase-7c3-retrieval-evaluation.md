# Phase 7C.3 Pass 2 — deterministic alternative retrieval evaluation

Starting commit: `f9b74e9593f405a2cb746c203b8ac18c0bcc5426`.
Branch: `phase7c3-alternative-card-research`.
Certified main: `100b0036a2f78abee2a61ad213cb07de63558a5e`.

## Disposition

READY for bounded Pass 3 Agent integration, subject to PM approval. This is a lexical candidate retrieval foundation, not a semantic equivalence engine or a recommendation system. The ten requested readiness properties are demonstrated below; neither complete recall nor precision has been established. Broad rankings remain a material limitation. No Agent integration is included in this commit.

## Architecture and interfaces

`RetrievalIndex.from_database(path)` calls the unchanged Pass 1 read-only SQLite snapshot analyzer over the complete currently cached Standard pool. It never reads collection, tournament popularity, active deck or provider data. `search(text, reference=None, limit=10)` returns a deterministic dictionary; maximum limit is 50. Query length is 1–1000 characters. Invalid limits and unknown reference identities raise bounded ValueErrors. No API endpoint was added.

The index retains every component and every legal printing, including missing/partial/unclassified effects. Text matches, structured atom matches and concept matches independently contribute to a union. Explicit constraints are then applied within functional identities. Per-component scores are computed before grouping as an equivalent implementation of max-over-component ranking; scores are never summed over reprints. One result is returned per existing functional identity. Same-name cards with different functional identities can legitimately appear separately.

The query representation includes normalized original text, bounded recognized phrases/concepts, actions, objects, players, source/destination zones, category/stage/type/Trainer-subtype constraints, negative Trainer/ex constraints, optional reference identity, and unresolved original text. It does not pretend to consume arbitrary prose. The full normalized query remains available as unresolved text even when some phrases are recognized. Unsupported HP/cost/resistance/ownership/price requests are explicitly flagged as unevaluable; they are not silently considered satisfied. Missing source properties are reported per result.

Bounded aliases cover mill/deck depletion, self-mill, Pokémon recovery, counter transfer, Energy removal and Item/Tool/Ability control. User-requested concepts always override the reference card. Reference-only similar-role retrieval derives supported concepts from that functional card and excludes the reference itself. A small explicit related-concept map distinguishes Item lock from Tool suppression/Ability suppression, and Tool suppression from removal; no generic DISRUPTION equivalence exists.

## Ranking and result contract

Each result contains functional identity, card name/category/source properties, deterministic representative printing, all legal printings with checked timestamps/source hashes, source components with original and normalized text, atoms, matched concepts/relationships/text, independent eligibility channels, score components, unresolved spans, ambiguity/source-omission flags and satisfied/unevaluable constraints.

Scores: explicit bounded relationship plus compatible action = 100; exact full source phrase = 110; compatible atoms = 8; exact concept = 25; related concept = 12; qualifying token overlap = 3 per term capped at 20; partial/ambiguous representation = -3. Component maximum is the identity score. Ties use normalized name then functional identity, with component IDs breaking component ties. Reprints cannot add points. The score is inspectable, not calibrated relevance probability.

`direct_mechanical` means an explicit bounded source relationship plus action was found. It does NOT mean conditions, targets, costs or game execution have been fully resolved. `related_functional` means an explicitly related concept rather than the requested mechanic. `text_only_uncertain` includes label-only, atom-only and unclassified text candidates without sufficient corresponding relationship evidence. Full text remains attached for future presentation. No strategic interchangeability is asserted.

The result count is bounded, but complete printing/component provenance can be large. Pass 3 must separately budget the provider-facing projection rather than serialize this whole result into a prompt.

## Benchmark design

53 cases, 47 with independently specified known source-printing targets. Targets were chosen from manual printed-text inspection, not retrieval output. The benchmark covers all requested major families: resource/search/recovery, self/opponent mill, Energy acceleration/denial, Item/Tool/Ability control, switching/retreat/Stadium, damage/healing/prevention, counters, prizes/liability, copy/evolution/devolution/status, Weakness, top-deck/reorder, Rule Box/ex, rare/partial text, and unsupported/empty cases. The slightly larger count preserves eight paraphrase pairs and all twelve canonical questions.

Machine-readable inputs: `tests/fixtures/alternative_retrieval_benchmark.json`.
Results: `docs/phase-7c3-retrieval/evaluation.json`.
Source corpus: unchanged Pass 1 cards/effects artifacts, independently reanalyzed from the local database during evaluation.

Any-known-target hit counts (not precision or full recall): top 1 **11/47 (23.4%)**, top 3 **19/47 (40.4%)**, top 5 **27/47 (57.4%)**, top 10 **33/47 (70.2%)**. No output-derived targets were added to inflate these numbers. A target below ten is a bounded shortlist miss even if earlier candidates are also relevant. Full relevant sets and full recall are unknown.

All eight pairs have consistent known-target top-ten outcomes. Six have identical top-ten identity sets; recovery and counter movement have Jaccard overlap 0.8182. Extra original-language text signals and the explicit Pokémon constraint explain the differences; the parsed mechanic remains the same.

## Canonical questions

- **tools_budew** — Is there another card that stops players from using Tools? Top three: Jamming Tower [direct_mechanical]; Jellicent ex [direct_mechanical]; Arven's Skwovet [related_functional]. Known-target ranks: [1]. Eligible identities: 18.
- **mill** — What cards can mill my opponent? Top three: Centiskorch [direct_mechanical]; Coalossal [direct_mechanical]; Cornerstone Mask Ogerpon [direct_mechanical]. Known-target ranks: [21]. Eligible identities: 27.
- **selfmill** — What cards can mill me? Top three: Avalugg [direct_mechanical]; Fraxure [direct_mechanical]; Goodra [direct_mechanical]. Known-target ranks: [8]. Eligible identities: 12.
- **move** — Are there other Pokémon that move damage counters? Top three: Alakazam [direct_mechanical]; Cofagrigus [direct_mechanical]; Flutter Mane [direct_mechanical]. Known-target ranks: [4]. Eligible identities: 103.
- **supporter** — What else can search for a Supporter? Top three: Call Bell [direct_mechanical]; Larry's Skill [direct_mechanical]; Meowth ex [direct_mechanical]. Known-target ranks: [4]. Eligible identities: 9.
- **recover** — What other cards can recover Pokémon from the discard pile? Top three: Dhelmise [direct_mechanical]; Iron Leaves [direct_mechanical]; Lana's Aid [direct_mechanical]. Known-target ranks: [5]. Eligible identities: 87.
- **similar_budew** — What cards perform a similar role to Budew? Top three: Flaaffy [direct_mechanical]; Frillish [direct_mechanical]; Galvantula ex [direct_mechanical]. Known-target ranks: not assigned; classification evaluation. Eligible identities: 12.
- **basic_items** — Are there other Basic Pokémon that can disrupt Items? Top three: Budew [direct_mechanical]; Frillish [direct_mechanical]; Flutter Mane [related_functional]. Known-target ranks: [1]. Eligible identities: 5.
- **energy_denial** — What can discard Energy from my opponent's Pokémon? Top three: Accelgor [direct_mechanical]; Centiskorch [direct_mechanical]; Cobalion [direct_mechanical]. Known-target ranks: [2]. Eligible identities: 377.
- **bench** — What cards can damage the Bench? Top three: Armarouge [direct_mechanical]; Blaziken [direct_mechanical]; Centiskorch [direct_mechanical]. Known-target ranks: [39]. Eligible identities: 83.
- **abilities** — What prevents Abilities? Top three: Flutter Mane [direct_mechanical]; Gastrodon [direct_mechanical]; Golduck [direct_mechanical]. Known-target ranks: [1]. Eligible identities: 7.
- **copy** — What cards can copy attacks? Top three: Clefable [direct_mechanical]; Ethan's Sudowoodo [direct_mechanical]; Mr. Mime [direct_mechanical]. Known-target ranks: [1]. Eligible identities: 11.

Budew/Tools explicitly chooses `tool_nullification`; Jamming Tower ranks first, followed by Jellicent ex. Budew's Item restriction is not substituted. Similar-role Budew uses Item mechanics with separately labelled related control, excludes Budew itself, and does not claim interchangeability. Basic-Pokémon Item restriction reduces the universe to five identities; Budew is first when it is not explicitly excluded by a reference.

Mill direction is represented separately. Top-ten direct relationships pass directional tests, including conditional retaliatory mill whose trigger mentions the other deck; merely mentioning both decks must not be mistaken for changing the discard action's target. Spiritomb is eligible at rank 21 for opponent mill, a top-ten miss; Ninetales is rank 8 for self-mill.

## Corpus-wide safety and uncertainty

The current snapshot remains 3,345 printings / 2,092 functional identities / 5,180 components. All 3,646 text components belonging to 1,750 functional identities are indexed. All 88 taxonomy-free text components and 3,565 partially represented text components remain eligible for the independent text channel. Remaining identities without supplied text cannot yield invented text matches. All source hashes/URLs/checked timestamps survive.

Patrat `me04-070` has an unclassified, atom-free counter-movement prohibition. Its full source text ranks first as `text_only_uncertain`. Munkidori `me02.5-099` is a real partial/conditional counter-moving example and ranks fourth. Synthetic ablation of Munkidori's atoms/taxonomy proves text eligibility independently; it is not counted as additional corpus evidence. A separate architectural ablation verifies atom-only eligibility. Duplicate-component testing leaves identity order and score unchanged. No ownership/popularity inputs or filters exist.

Explicit Trainer recovery and Basic Pokémon constraints pass. Stage 2 Tool-control constraints eliminate all candidates. Known-missing properties remain unevaluable rather than assumed true. Lost Zone, quantum terminology and a vague “What is best?” return empty. A 999 HP draw query returns partial with an explicit unsupported-property limitation, not a claim that candidates have 999 HP.

## False positives, misses and limits

- Pass 1's lexical `spread_damage` label includes Kyogre `me01-034` because its text says damage **for each** Energy. That is not spread damage. Pass 2 does not alter the Pass 1 artifact; the label-only candidate is explicitly uncertain and cannot receive the direct relationship score. A regression locks this distinction.
- Weak lexical tails remain noisy: the Energy-denial wording has 377 union candidates and recovery 87, while their top results carry stronger direct relationships. Exact phrase fallback for Patrat also retrieves weaker unrelated word-overlap candidates below it. These must not be presented as proven alternatives.
- Fourteen of 47 known-target cases miss the default top ten. Examples: Spiritomb rank 21; Stonjourner Bench damage rank 39; Mega Lucario ex acceleration rank 16; Spearow Tool removal rank 16; Mamoswine Stadium removal rank 13; Tangela Poison rank 25; Shedinja ex interaction rank 27. Broad draw/heal/search queries have many ties. The `me01-021` Pokémon-search target and Mega Venusaur healing are outside the bounded top 50; no unbounded recall claim is made.
- A category/constraint spelling defect in the initial new implementation (`Pokémon` versus source `Pokemon`) was caught by evaluation and corrected before committing.
- An initial test incorrectly treated any mention of “your deck” as self-mill, rejecting a legitimate retaliatory opponent-mill effect. The corrected test checks the requested explicit relationship rather than an unrelated trigger substring.
- An initial independent atom matcher was too generic for Lost Zone movement. It was narrowed so an unqualified move/put verb cannot establish that specialized concept. The real absent-Lost-Zone test now passes; no synthetic Lost Zone support is claimed.
- Bounded regexes are not universal NLP, semantic entailment, condition execution, strategic similarity or rules authority. Multi-intent prose, arbitrary negative constraints, arbitrary numeric properties and pronoun scope remain limitations. Generic concept/atom matches stay uncertain. Full text and ambiguity flags must remain visible in Pass 3.

## Verification

Final external-network-blocked gate: **126 passed** (47 mechanics, 35 retrieval, 44 existing card-data/desktop-engine regressions), 4.54 seconds. Targeted retrieval iterations preceded this single final relevant gate. No shared existing production code changed, so no broad backend suite was warranted. No frontend tests/build ran. Socket connections were blocked in new tests and evaluation; the final existing-test wrapper permits only loopback for local test plumbing.

Pass 1 implementation, taxonomy and artifacts remain byte-for-byte unchanged. Existing certification tags and local/canonical main remain unchanged. No provider calls, no external network calls, no Agent/UI/recommendation work, no merge, no tag and no certification.

## Pass 3 proposal and PM decisions

After PM acceptance, resolve an explicit query and optional selected functional identity server-side, retrieve locally, and build a small versioned evidence projection containing a bounded subset of candidates, direct/related/uncertain labels, specific matched source components and omissions. Reuse the certified provider-neutral Research boundary; do not expose the provider to the full corpus or treat taxonomy as rules authority. Keep ownership/competitive enrichment subsequent and separate from eligibility. Citations should identify exact selected source components, not free-form model recollection. Maintain snapshot/revision protection and zero-write behavior.

PM should decide whether text-only/related candidates are exposed by default or behind an explicit broader-search control, and accept or request further work on broad-query top-ten diversity before integrating. No provider call is needed for those decisions. Current READY means a bounded, inspectable candidate-evidence integration can proceed; it is not acceptance of strategic recommendations or an assertion of exhaustive relevance.

## Every benchmark case

- `tools_budew`: known-target ranks [1]; candidates 18; state `candidates`.
- `mill`: known-target ranks [21]; candidates 27; state `candidates`.
- `selfmill`: known-target ranks [8]; candidates 12; state `candidates`.
- `move`: known-target ranks [4]; candidates 103; state `candidates`.
- `supporter`: known-target ranks [4]; candidates 9; state `candidates`.
- `recover`: known-target ranks [5]; candidates 87; state `candidates`.
- `similar_budew`: known-target ranks []; candidates 12; state `candidates`.
- `basic_items`: known-target ranks [1]; candidates 5; state `candidates`.
- `energy_denial`: known-target ranks [2]; candidates 377; state `candidates`.
- `bench`: known-target ranks [39]; candidates 83; state `candidates`.
- `abilities`: known-target ranks [1]; candidates 7; state `candidates`.
- `copy`: known-target ranks [1]; candidates 11; state `candidates`.
- `mill_plain`: known-target ranks [21]; candidates 27; state `candidates`.
- `selfmill_plain`: known-target ranks [8]; candidates 18; state `candidates`.
- `recover_plain`: known-target ranks [5]; candidates 17; state `candidates`.
- `move_plain`: known-target ranks [4]; candidates 10; state `candidates`.
- `denial_plain`: known-target ranks [2]; candidates 173; state `candidates`.
- `items`: known-target ranks [1]; candidates 13; state `candidates`.
- `items_plain`: known-target ranks [1]; candidates 13; state `candidates`.
- `tools`: known-target ranks [1]; candidates 18; state `candidates`.
- `tools_plain`: known-target ranks [1]; candidates 18; state `candidates`.
- `abilities_plain`: known-target ranks [1]; candidates 7; state `candidates`.
- `draw`: known-target ranks [38]; candidates 129; state `candidates`.
- `pokemon_search`: known-target ranks [None]; candidates 136; state `candidates`.
- `acceleration`: known-target ranks [16]; candidates 95; state `candidates`.
- `energy_recovery`: known-target ranks [1]; candidates 12; state `candidates`.
- `tool_removal`: known-target ranks [16]; candidates 16; state `candidates`.
- `hand`: known-target ranks [8]; candidates 289; state `candidates`.
- `gust`: known-target ranks [2]; candidates 37; state `candidates`.
- `retreat`: known-target ranks [10]; candidates 46; state `candidates`.
- `stadium`: known-target ranks [13]; candidates 17; state `candidates`.
- `heal`: known-target ranks [None]; candidates 96; state `candidates`.
- `prevent`: known-target ranks [49]; candidates 69; state `candidates`.
- `reduce`: known-target ranks [18]; candidates 58; state `candidates`.
- `place`: known-target ranks [33]; candidates 115; state `candidates`.
- `prize`: known-target ranks [4]; candidates 15; state `candidates`.
- `liability`: known-target ranks [7]; candidates 15; state `candidates`.
- `evolution`: known-target ranks [3]; candidates 9; state `candidates`.
- `devolution`: known-target ranks [2]; candidates 6; state `candidates`.
- `status`: known-target ranks [25]; candidates 44; state `candidates`.
- `weakness`: known-target ranks [2]; candidates 3; state `candidates`.
- `reorder`: known-target ranks [5]; candidates 7; state `candidates`.
- `rule_box`: known-target ranks [4]; candidates 10; state `candidates`.
- `ex`: known-target ranks [27]; candidates 62; state `candidates`.
- `rare`: known-target ranks [1]; candidates 31; state `candidates`.
- `trainer_recover`: known-target ranks [3]; candidates 21; state `candidates`.
- `lost_zone`: known-target ranks []; candidates 0; state `empty`.
- `unknown`: known-target ranks []; candidates 0; state `empty`.
- `vague`: known-target ranks []; candidates 0; state `empty`.
- `unknown_constraint`: known-target ranks []; candidates 129; state `partial`.
- `spread`: known-target ranks [7]; candidates 326; state `candidates`.
- `topdeck`: known-target ranks [2]; candidates 6; state `candidates`.
- `constraint_empty`: known-target ranks []; candidates 0; state `empty`.

Corpus hash: `bd069ccc10964e13c127f97ab318cca018933ca18f1f3b3e5c18c94643d08581`.
Benchmark hash: `e4d3ec57921774424b8d3f64b5c54f906f9a6be2881bdf2136b08c54a6e197d4`.
