# Pre-Ally exact recommendation diagnostics and targeted fallback

Starting candidate: `84c97ae98c7a9a1dbf94874dcfb241fc62d58902`, branch
`phase7c5-concrete-deck-resolution`. This patch changes backend recommendation
recovery and a narrow printed-fact name match. It does not change custom generation,
consensus construction, global ranking, providers/settings, or saved decks.

## Diagnosis before editing

The historical Mega Gengar failure cannot be assigned an exact validator reason:
the old implementation discarded the rejected selections. Do not label that
historical failure a copy-limit or sandbox failure without an original trace.

The supplied exact list resolved locally as VALIDATED: Pokémon 12, Trainer 36,
Energy 12, total 60. One explicitly approved Gemini diagnostic request against the
starting candidate succeeded without retry: cut 2 Special Red Card, add 2 Spiky
Energy. This proves a valid supported-construction swap existed; it does not prove
competitive improvement or explain the prior two failures. The pool contained 21
identities, source binding was unchanged, and budget compaction removed duplicate
provenance/artifact content without dropping candidate IDs.

A separate deterministic reproduction proved the old failure mechanism: a
replacement that exceeded the grouped four-copy limit was retried against the
same pool and rejected again, then rendered only `change_construction_invalid`.
A valid alternative existed. The old code obscured this specific reason and had
no targeted local recovery. That mechanism is confirmed, not the historical
Gemini selection.

## Changed behavior

1. Assessment preserves specific copy-limit, ACE SPEC, outside-sandbox, legality,
   stale-source, malformed-contract, unbalanced-swap, required-candidate trimming,
   no-material-improvement, and unknown-validation reasons. Narrow-pool/no-role
   reasons are supported by recovery routing; the system does not invent those
   diagnoses when the original reason is unknown.
2. One provider retry changes eligible choices and constraints for construction
   failures, retrieves up to eight legal role alternatives when appropriate,
   restores missing required candidates, or refreshes source binding. A malformed
   contract gets format repair only. Current source identities remain available.
3. If a custom recommendation still fails, bounded local recovery tries the
   attempted Trainer trade's same role, then adjacent roles, then a current-card
   support ratio adjustment. It preserves the core and does not invent Energy or
   Pokémon cuts. Every option passes the existing resolver/construction validator
   at exactly 60 before it can reach the authoritative retained change set.
4. A bound provider opt-out produces no fabricated swap: “I couldn’t find a
   meaningful legal upgrade without changing the deck’s core plan. The current
   deck is unchanged.” Other failures explain the specific constraint in ordinary
   language. Failed recommendations remove stale pending changes, not the deck.
5. Sanitized `proposal_attempt` appears in the API response and local conversation
   debug state. It records source ID/hash, attempted cuts/adds, safe failure code,
   blocked IDs, retry strategy, and final status. It contains no API keys or raw
   provider prose and is not placed in normal chat paragraphs or model history.
6. On valid generated-deck explanations, grammatical prefixes such as “Your
   Pikachu ex” match the resolved card. An unknown “Mega Pikachu ex” remains
   unknown. Genuine unresolved-detail warnings remain; evidence stays on demand.

## Validation and PM QA

The exact PM fixture starts from a locally validated retained list, independently
of generation. It tests copy-limit failure, changed retry constraints, validated
fallback, matching Cut/Add prose, apply, and recount at 60; current source remains
immutable until apply. It also tests the observed Spiky Energy swap, ACE SPEC,
stale binding, bad JSON, unsupported IDs, imbalance, opt-out, adjacent roles,
current-card consistency, required-candidate restoration, and fact notices.

Focused verification: 166 passed across recommendation, generation/build routing,
Pikachu, consensus authority, fact review, completion, and context-budget tests.
The 16-test diagnostic suite also passed, including two additional fallback-tier
checks. One backend gate passed: **1,389 passed, 9 deselected**, in 305.15 seconds.
Only the nine previously confirmed baseline research/copy-fixture failures were
excluded, using:
`not test_confidence_is_not_discovery_wall and not test_composite_determinism_60_observed_only_and_validator and not test_invalid_candidate_does_not_hide_valid_candidate and not test_copy_exact_new_saved_preferred_unowned_and_immutable`.

After this gate, final focused verification additionally checks explicit
Dragapult and Lopunny Dusknoir recommendation → apply → recount, and a metadata
ordering correction that includes the retry number before calculating the retry
context hash. The single backend gate was not repeated for that narrow correction.
This final focused run passed **54 tests**, including all 18 diagnostic/consensus
flow tests. **READY for PM QA**, with the historical failure diagnosis limitation
above. The ending commit SHA is supplied in the delivery message.

Files changed in this patch:

- `src/pokelab/agent_recommendation_fallback.py` (new)
- `src/pokelab/agent_conversation.py`
- `src/pokelab/agent_generated_changes.py`
- `src/pokelab/agent_context_budget.py`
- `src/pokelab/agent_card_facts.py`
- `tests/test_agent_recommendation_fallback.py` (new)
- `tests/fixtures/gengar_pm_fallback.json` (new)
- `tests/test_agent_exact_recommendations.py`
- `docs/pre-ally-recommendation-fallback-qa.md` (new)

PM should rerun the live Gengar loop: build → why → exact changes → apply → recount.
If it fails, inspect `proposal_attempt` in the recommendation response rather than
trying to infer the cause from prose. Also exercise custom Pikachu and consensus
Dragapult/Lopunny Dusknoir. Local strategic-role heuristics establish a defensible
support tradeoff, not measured tournament quality. No post-change live provider
replay is claimed. No frontend files changed, so frontend checks were not rerun.

The pre-existing dirty `scripts/Start-Phase5-QA.ps1` is excluded from this commit.
Its SHA256 remains
`BB800264286E41FB5C080A817D7136A69F1796C79568CABFD5548C6782B32356`.
No merge, tag, certification, Analytics activation, or Phase 7D work.
