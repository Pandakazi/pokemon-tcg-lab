# 7C.5 final closeout polish

Starting commit: `09e45bd829df7344fb6dde2aeebaaf55cc28607f`.
Branch: `phase7c5-concrete-deck-resolution`.

## Behavior

- The existing hybrid instruction now requests balancing cuts in the same response when adding to a full deck. It prioritizes situational/redundant slots, preserves core cards, and asks for a tradeoff explanation. Existing local diff validation still controls totals and legality. These remain proposals only; no deck writes.
- The existing AssociatedCardPreview positioning/portal was extracted into useCardPreview. Shared artwork previews use its 350px width and 500ms pointer delay. CardImage/FinishImage propagate this across Library, Collection, Variations, Card Detail, Deck Builder and research artwork. Existing Agent/name references retain the same preview. Keyboard name focus remains immediate.
- Competitive surfaces show one vertically stacked popup: enlarged artwork, then name, statistics and evidence. Artwork-only triggering and the existing 500ms competitive delay remain. Competitive surfaces suppress the separate artwork tooltip. The panel stays within the viewport and scrolls when needed.
- Source-owned factual corrections are retained as whole, card-named paragraphs before hybrid prose filtering. Display whitespace/repeated punctuation is normalized; original printed evidence remains unchanged.
- Empirical-versus-structural instructions request discussion of the actual recommendations. Bounded existing conversation history retains up to 12 recommendation names; follow-up boundary text names those swaps and distinguishes observations from proven efficacy.
- Concrete follow-up instructions require explicit referents or one clarification question without actions. Validated removal names are repeated in the proposed response to expose the interpretation to the user.

## Verification

- Focused backend: 122 passed.
- Single final backend gate, external socket connections blocked: 306 passed; two existing dependency deprecation warnings.
- Frontend: initial full run 109/110 passed; the remaining test counted an unrelated delayed Library fetch during the new hover delay. Its assertion now specifically checks no artwork lookup or provider submission. Affected file rerun: 10/10 passed. All 110 tests are covered by passing runs.
- TypeScript: passed.
- Browser: five focused checks passed, covering Agent hover/evidence, safe rejection, and stacked competitive artwork at 900px and 1440px. After viewport positioning correction, both stacked-popup checks passed again. Screenshots visually inspected using local placeholder artwork, not live card-image downloads.
- git diff --check: passed.
- No live provider calls, external network calls, writes to user decks, pushes, merges, tags or certification.

## Files

Backend: agent_hybrid.py, agent_conversation.py, agent_card_facts.py.
Backend coverage: test_agent_deck_proposals.py, test_agent_card_facts.py.
Frontend: AssociatedCardPreview.tsx, FinishImage.tsx, CardTile.tsx, Competitive.tsx, DeckBuilder.tsx, index.css.
Frontend coverage: Competitive.test.tsx, ConversationPanel.test.tsx, integration/competitive.spec.ts.

## Limits and PM retest

Auto-cut strategy and resolving conversational ambiguity remain model-guided. Fake-provider tests establish prompt requirements, response handling, validation, and no writes; they do not prove every live model will choose good cuts. No new optimizer, retries or memory architecture were added. Existing validation continues to report incomplete or invalid proposals honestly.

PM should check one full-deck addition proposes defensible balancing cuts and explains the sacrifice, a follow-up names the intended cards or asks for clarification, factual corrections remain intact, and the empirical answer discusses the actual swaps. Verify the stacked artwork/statistics popup on Library and Deck Builder, and image-only previews on Variations/Collection/Card Detail. No live call was performed as part of this pass.

READY FOR 7C.5 CERTIFICATION, subject to final PM QA and separate authorization. No certification performed.
