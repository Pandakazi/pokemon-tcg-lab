# Phase 7C.3 Pass 3 — open card-pool Research

Implementation status: **READY for PM live QA**, not certified. No live inference was performed.

Starting HEAD: `c468ebf1e06c2fd79fc8f1ed9a30aa961e742cfe`.
Branch: `phase7c3-alternative-card-research`.
Ending HEAD is the implementation commit containing this report, reported explicitly in the handoff. Certified main remains `100b0036a2f78abee2a61ad213cb07de63558a5e`.

## Files

- `src/pokelab/card_pool_research.py`: local retrieval projection and bounded additional claim guards.
- `src/pokelab/agent_research.py`: optional-context request scope, pool prompt, reuse of transport/assessment and no-inference boundary responses.
- `tests/test_card_pool_research.py`: 27 network-blocked product/contract tests.
- `tests/test_agent_deck_research.py`: advertised scopes expectation includes the new scope; existing assertions retained.
- `web/src/ResearchAgent.tsx`: research-area control, optional deck context, pool request/snapshot/citation rendering.
- `web/src/CardDetail.tsx`: reference-card entry point, including cards outside the active deck.
- `web/src/index.css`: scoped layout for the two new controls.
- `web/src/CardPoolResearch.test.tsx`: open/reference UI tests with mocked fetch and no DeckProvider.
- `web/integration/card-pool-research.spec.ts`: browser checks at 1440 and 900 px with mocked research responses and blocked external requests.
- This report.

## Architecture and request contract

The existing `POST /api/v1/agent/research` service now accepts `scope="card_pool_research"`. No parallel Agent service or transport was created. Existing selected-card and active-deck scopes retain their previous builders, prompts and answer contract. Status advertises all three scopes.

Pool request fields: question (1–1000 characters), optional printing/variant, optional `include_deck` (default false), revision required only when deck context is included, and the existing competitive window. Requests beyond the accepted retrieval query limit are rejected rather than silently truncated. Legacy question limits remain unchanged.

Open research needs neither a selected card nor an active workspace. Reference research resolves the exact selected Standard printing and optional finish locally; it does not require deck membership. Deck-context research validates the submitted workspace revision, captures complete functional quantities and selects up to three deterministic printed-mechanic orientations. These orientations are explicitly not creator intent. Each orientation searches the whole Standard index; active-deck membership is not an eligibility filter.

Pipeline: request → bounded deterministic query/explicit context → unchanged Pass 2 whole-pool retrieval → small versioned projection → existing provider-neutral service → unchanged Answer schema/citation assessment plus bounded pool guards → existing Agent panel.

Single-flight, explicit provider/model, $0 price controls, no retries/fallbacks, secret quarantine and truncation rejection remain in the certified transport path. No runtime or credential configuration was changed.

## Projection and provenance

`pokelab-card-pool-research-v1` wraps `pokelab-card-pool-evidence-v1`, reusing existing immutable field values, evidence items, coverage and provenance references. The 7A packet definition is not modified.

- At most five distinct candidate identities; at most two distinct matching components per candidate.
- Optional exact reference evidence and up to three deck-mechanics anchors, each retaining printed text and provenance.
- Whole envelope capped at 24,576 UTF-8 bytes; trailing candidates are removed with explicit omissions. Existing total provider-input ceiling is also checked.
- Exact original question, deterministic retrieval representations, corpus hash, candidate source hashes/timestamps/URLs and envelope content hash are retained.
- Candidate projection retains functional identity, representative Standard printing, category/properties, printed/normalized text, structured attack fields, matched atoms/concepts/text, scores, classifications, ambiguity/unmatched spans and constraint results.
- Complete reprint lists and unrelated components are not sent. The full card database is never sent. The local catalog-name guard is explicitly excluded from serialized provider/UI payloads.
- No competitive enrichment is projected in this pass. Coverage explicitly marks tournament performance, piloting guides and reviewed gameplay outcomes unavailable. The existing selected/deck-research paths still expose their competitive evidence as before.

Actual local-corpus smoke checks, read-only and without providers:

- Flagship milling question: 13,150-byte envelope / 19,698-byte total prompt+envelope; five candidates (Centiskorch, Coalossal, Cornerstone Mask Ogerpon, Crawdaunt, Deino).
- Budew/Tools: 14,368-byte envelope / 20,916-byte total; Jamming Tower, Jellicent ex and three related Tool-removal candidates.
- Corpus hash unchanged: `bd069ccc10964e13c127f97ab318cca018933ca18f1f3b3e5c18c94643d08581`.

## Query integration versus Pass 2

Pass 2 code, taxonomy, benchmark and recorded results remain unchanged. The integration layer supplies a small documented alias bridge for newly required product wording: milling → opponent mill; moving counters → move counters; deny opponent Energy → Energy denial; something like a supplied card → explicit reference similarity. Existing recognized requested concepts always take priority. No ranking changes or benchmark retuning occurred.

Deck orientation is bounded by quantity/identity order and supported printed concepts, with round-robin collection across up to three local searches. It is not strategic similarity, optimization or a claim about what the pilot intended. Broad-query ranking limitations accepted in Pass 2 remain.

## Voice, citations and boundaries

The pool prompt asks for an early, useful answer in ordinary Pokémon language, a small selection of candidates and an explanation of relevance. Retrieval rank does not dictate answer order; noisy or redundant candidates may be omitted. Internal scores, IDs and taxonomy belong in the evidence viewer, not routine prose. Direct, related and uncertain relevance must remain distinguishable in natural wording.

The existing five-field Answer schema is unchanged. JSON-only output, exact enums, required arrays, byte ceiling, no fence repair, strict evidence-ID membership, safe rejection and no raw rejected output/hidden reasoning remain intact. `active-deck` is a valid citation only if this envelope actually contains deck context. Conversational prose passes the production assessment in mocked tests; this does not predict live model prose quality.

Additional bounded guards reject known out-of-projection catalog-card claims, uncited named candidates, unsupported competitive superlatives, known action/piloting forms, direct-equivalence claims for related/uncertain candidates, known mill/Tool mismatches, invented numeric card properties and unsupported named attack costs. They are not a universal semantic entailment proof. PM still reviews the actual cited claims; arbitrary natural-language hallucinations cannot be ruled out solely by regex checks.

Detailed matchup/piloting questions and recognized deck-changing requests return an unsupported boundary without inference. Empty retrieval returns insufficient evidence without inference. No candidates are invented to avoid an empty result. No deck writes, transactions, replacements or save actions were added.

Missing tournament evidence is unknown, not proof that a card is bad. Mechanical suitability alone cannot support “best,” “proven,” “tournament staple,” or matchup-performance claims.

Follow-up is supported as another explicit question using the selected context. No previous answer or hidden conversation history is sent; pronoun-only follow-ups may require clarification. This is not Research Memory.

## Deterministic acceptance results

All ten positive canonical categories passed the real local builder → mocked existing provider transport → strict production validator path:

1. Open flagship milling question, no printing/deck.
2. Opponent mill.
3. Self-mill, distinct from opponent mill.
4. Moving damage counters.
5. Denying opponent Energy.
6. Similar-role Budew with explicit reference.
7. Budew reference plus Tools; Tool query preserved and Jamming Tower supplied.
8. Other Pokémon moving counters with Munkidori reference.
9. Supporting the active deck, revision checked, whole pool searched.
10. Unusual interactions with active-deck mechanics, with printed orientation anchors.

Unknown terminology and detailed matchup-piloting questions passed negative tests with zero mocked inference requests. Additional tests cover absent workspace/collection, unchanged source bytes, invalid citations (including nonexistent active deck), competitive claims, an out-of-evidence card, invented HP, related/direct separation, truncation, byte-budget omissions, query-length rejection and deterministic content hashes. Fixtures deliberately omit candidates from the answer while retaining strict citations.

## Verification

- One final relevant network-blocked backend gate: **343 passed**, 34.19 s. Includes selected-card Research, answer contracts, deck Research, PM correction regressions, retrieval and mechanics.
- A subsequent narrow request-length guard was added to prevent silent truncation at the unchanged Pass 2 1000-character limit; **27 pool tests passed**, including its new regression. No broad suite was repeated.
- Focused frontend Research tests: **22 passed** across three files. Final pool-only rerun after control spacing/length changes: **2 passed**.
- TypeScript passed.
- Browser checks: **2 passed**, 1440 and 900 px; rerun after the scoped spacing correction. Final screenshot visually inspected. These mock the research API; backend provider integration is covered separately above.
- Existing library/Card Detail behavior is retained; no unrelated frontend suite/build was run.
- `git diff --check` passed before commit.
- Zero live provider calls and zero external network calls. Browser/server communication was local loopback only; provider responses were mocked.
- No changes to Pass 1/2 artifacts, 7A contracts, 7B provider/qualification contracts or historical qualification results. Main and certification tags remain unchanged.

## PM QA procedure

Use the existing configured $0 Gemini session. No new environment variables or credential changes are needed. Restart is a PM action; Work did not restart the PM runtime or submit live questions.

```powershell
Set-Location 'C:\Users\Mike\Documents\Codex\2026-09-25\referenced-chatgpt-conversation-this-is-an\work\phase5'
.\scripts\Start-Phase5-QA.ps1 -Action Restart -SourceRepository 'C:\Users\Mike\Documents\pokemon-tcg-lab' -ApiPort 8003 -WebPort 5175 -PhaseLabel 'Phase 7C.3 Pass 3'
Invoke-RestMethod 'http://127.0.0.1:8003/api/v1/agent/status' | ConvertTo-Json -Depth 5
```

Verify available=true, the intended explicit provider/model and `card_pool_research` in scopes. Open http://127.0.0.1:5175. In the Agent panel choose **Standard card pool**, clear any selected card, and leave **Use active deck as optional context** unchecked.

After PM authorizes live submissions, test:

1. “What are some really good cards if I wanted to make a milling Pokemon deck for Standard format tournament play?” Expect a short useful explanation, not retrieval rows or unsupported tournament rankings. Inspect every factual citation.
2. “What cards can mill my opponent?” Then “What cards can mill me?” Check direction separately.
3. “I want to build around moving damage counters. What cards should I research?”
4. “What cards could help a deck that tries to deny my opponent Energy?”
5. Open Budew Card Detail → **Research similar cards** → “What other cards do something like Budew?”
6. With that reference, ask “Is there another card that stops players from using Tools?” Tools must not become Items.
7. Repeat counter research with a Munkidori reference.
8. Enable optional active-deck context and ask “What cards might support what this deck is trying to do?” Then “Are there any weird cards in Standard that interact with the mechanics in this deck?” Check captured revision and printed anchors; retrieval must not be restricted to deck members.
9. “Quantum banana transposition” should return insufficient evidence without inference.
10. “How should I play Great Tusk Mill against Dragapult ex?” should return the scope boundary without inference.

Confirm one explicit Ask produces at most one provider request; changing context, opening evidence and clearing a reference produce none. Change context after an answer and verify the original submitted snapshot stays labelled. Confirm no deck actions and no ownership changes. Existing **Current card / deck** mode still supports the certified selected-card and comparison workflows.

No merge, tag, certification or Phase 7D work is authorized by this implementation report. Stop for Mike's PM QA decision.
