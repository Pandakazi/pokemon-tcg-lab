# 7C.5 Agent simplification / FINALIZE architecture candidate

Starting commit: `14ae1e2047811934f0f3819ae10e47b6c593e7ab` (clean).
Branch: `phase7c5-concrete-deck-resolution`.

## Confirmed causes

- The exact PM full-deck request could route to EXPLORE: the old FINALIZE matcher did not recognize “create ... complete legal 60-card ... deck.” EXPLORE requested a prose-containing JSON envelope that did not expose the proposal field, so the model could supply an unchecked list in paragraphs.
- The session retained raw proposal intent when supplied, but not the resolved/validated list with category totals and source identity. Compacted prose was not a reliable recount source.
- The response path independently assessed, reconciled printed text, removed quantity sentences, appended canonical prose, and injected corrections/qualification text. The factual subject matcher could treat “That requires” as a card claim.

## New responsibility boundaries

The model returns natural prose and zero or one narrow JSON artifact inside the existing hidden POKELAB_ACTIONS block. `generated_deck` uses exact cards/quantities; `proposed_deck_changes` uses add/remove deltas. The artifact type, not the presence of an active deck, determines generated-list versus active-deck-diff intent. The old structured answer envelope is readable for compatibility but is not requested or enforced for ordinary conversation.

Local resolution and existing Deck Builder construction checks remain authoritative. Category subtotals and total are computed from resolved entries; model totals and legality labels are withheld from prose. Missing or malformed artifacts preserve independent discussion but cannot become a completed list. Partial structured entries remain explicitly incomplete. There are no repair calls or automatic retries.

The response now has one presentation boundary. It preserves safe original sentence units, withholds affected units, and supplies typed notices/factual reviews plus source evidence. It does not splice corrected strings or reconstructed causal tails into model prose. Deleted superseded structured-output instructions, strategic_prose, diff_paragraphs, the old assessment/injection path, and printed-fact replacement-string construction.

## Stored conversational artifacts and recount

The bounded existing session retains separate latest `generated_deck` and `proposed_deck_changes` artifacts. Each includes resolved entries/quantities/categories, computed subtotals/total, validation state/reasons, source turn, source snapshot hash and artifact identity. Artifacts survive prose compaction; a new diff does not overwrite a generated deck. Compact summaries are provided to subsequent model turns for reference. They never mutate the workspace deck.

Recount/show-again inventory intents read the stored artifact and recalculate its totals locally, bypassing both the provider and printed-fact review. The UI labels the original validation snapshot. This is session persistence (existing 30-minute idle expiry / 32-session bound), not durable storage or Phase 7D memory. Each artifact has a 64 KiB bound; overflow removes the artifact and explicitly prevents finalized status.

## Factual review and tone

Only bounded material printed-fact triggers open factual review. Pronouns such as That/This/It and ordinary strategic subjects are excluded. Inventory/recount never reconstruct card facts. Material claims are replaced by inspectable local factual data, not Python-authored conversational corrections; unresolved facts receive a concise separate notice. Printed text remains distinct from reviewed gameplay rulings.

The shortened prompt permits ordinary deckbuilding judgment without empirical permission gates. Empirical statements still require source evidence; explicit source IDs select local evidence with its original window/denominator. Unsupported empirical units are withheld with a concise separate notice only when needed. No routine legalistic paragraph is appended to every recommendation.

## Diff integrity

Explicit user cuts own the removal set: an impossible cut is not silently replaced by the model's alternative. Existing revision, source snapshot, functional identity, phantom-cut and construction checks remain. Removing and adding the same functional card in one proposal cannot silently cancel the requested increase; that cut is rejected and the proposal needs repair. Auto-cut choice and its rationale remain model responsibilities.

## UI

Existing Agent panel only: backend category subtotals, existing validated list/status, historical-artifact label, and concise separate notices. Stored proposal rows retain the existing exact-printing preview binding even when optional evidence cards were budgeted out. No stylesheet, artwork component, stacked popup, or deck layout changes.

## Files

Production: `agent_artifacts.py` (new), `agent_conversation.py`, `agent_hybrid.py`, `agent_deck_proposals.py`, `agent_card_facts.py`, `web/src/ConversationPanel.tsx`.
Tests: `test_agent_artifacts.py` (new), `test_agent_conversation.py`, `test_agent_deck_proposals.py`, `test_agent_card_facts.py`, `web/src/ConversationPanel.test.tsx`.
This closeout document.

## Verification

Focused affected suites: 130 passed before final helper deletion; then 25 targeted artifact/factual tests passed on the simplified path. A separate storage-budget edge-case regression passed. Frontend: 113 passed; TypeScript passed. Final backend gate result recorded below. All providers were fake transports and external backend socket connections were blocked in the final gate. No live provider calls or live QA quality claim.

Existing tests were updated where they specifically asserted deleted injected prose or the now-retired JSON-only conversational wire format. They now assert the corresponding authoritative report fields, typed factual reviews, natural provider contract, and retained independent reasoning. The tests still cover phantom cuts, exact quantities, Basic Energy, revision changes, no writes, truncation, secret quarantine and empirical boundaries.

## Remaining limits / PM QA

- Live model strategy, full-deck quality and reliable artifact emission still need PM QA. Synthetic deck fixtures prove arithmetic/identity behavior, not that Gemini will choose a strong Dragapult list.
- A model can omit/malform an artifact; the answer stays incomplete rather than being reconstructed from prose or retried.
- Narrow sentence guards remain; this is not universal semantic entailment. A sentence mixing strategy with unverified quantities/mechanics may be withheld as a whole. Separate strategic sentences survive unchanged.
- Recount is the original validation snapshot, not a new legality certification against subsequently changed card data. Idle expiration/restart ends this session state.
- Contradictory same-functional-card add/remove intents require review rather than automatic netting.

PM retest: restart the existing runtime, request the exact complete Dragapult list, inspect computed subtotals/status, then immediately recount and show it again. Recount should produce no provider execution. Check an absent explicit cut, an auto-cut that tries to cancel the requested addition, a three-card follow-up, and the empirical-versus-judgment question. No live calls were performed in this implementation pass.

No merge, tag, certification, deck writes, provider transport changes, qualification expansion, or Phase 7D implementation.

Final gate: **316 passed**, two existing Starlette/httpx deprecation warnings, 74.65 seconds. The storage-budget edge case was checked separately afterward: **1 passed**; the full gate was not repeated. `git diff --check` passed. Approved card-layout/hover files, provider transport and qualification configuration are unchanged from the starting commit.

**READY FOR PM QA.** No certification requested or performed.
