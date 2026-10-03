# Phase 7C.4 — Conversational Agent foundation

Starting branch: `phase7c3-alternative-card-research`; clean HEAD `5987975589e87a45235504ac23c5abb7d3f3e0e2`.

Preserved locally with annotated tag `phase-7c3-evidence-foundation-preserved-2026-10-03` at that exact SHA. This is preservation, **not a new PM certification**. Implementation uses `phase7c4-conversational-agent`. No main merge, remote push, existing-tag movement or 7C.4 certification is part of this pass.

Architecture: [ADR 002 — Conversation First, Evidence Underneath](adr/002-conversation-first-evidence-underneath.md).

## API and behavior

The existing read-only `/api/v1/agent/research` endpoint accepts `scope: "conversation"`, a question (1–2000 characters), optional opaque `conversation_id`, selected printing/finish, `include_deck` plus expected revision, and existing competitive window. The server resolves all actual facts. It accepts no client transcript, facts, provider overrides, URLs, SQL or write instructions. Existing research scopes and contracts are unchanged. `/api/v1/agent/status` advertises the default evidence policy and unavailable external-research capability.

The new versioned envelope contains current question, bounded prior accepted reasoning, selected printing/finish, snapshot revision/window/date, source-owned evidence and omissions. Facts are loaded through read-only snapshots; no missing store is created. Selected-card/active-deck errors remain explicit; absence of unrelated retrieval results does not block reasoning. The complete deck quantity/allocation vector is preserved; inability to fit required context fails before inference rather than silently truncating a deck. Standard candidate discovery uses the existing RetrievalIndex; exact selected printing can be inspected outside that Standard index.

The orchestrator maps self-mill, Tools, counter movement, Energy denial, natural control/disruption and deck-out language into existing retrieval queries. It matches local exact card/component names and refreshes prior candidate printings for follow-ups. The model receives the natural question unchanged. There is no planning inference, autonomous tool loop, routing, fallback or retry. The existing explicit provider/model, live authorization, server-only credential, timeout, single-flight lock and $0 controls apply unchanged. Gemini receives the typed response schema through the existing provider-neutral transport.

The response contains conversational paragraphs with optional evidence IDs and server-resolved facts. Arbitrary unknown IDs/extra fields fail. It is not the old strict Answer or card-pool answer contract. No ordinary strategic paragraph passes through the old card-pool regex checker. Exact facts are supplied before reasoning and selected fact values are never generated. Recognizable high-value empirical assertions are withheld as whole paragraphs and replaced with a clear qualification, leaving useful reasoning intact. This detector is bounded, not general entailment or comprehensive hallucination prevention.

No partial response is shown for truncation, failed completion, schema/citation failure or internal assessment failure. Safe execution metadata is returned; rejected provider output and exception prose are not. Only accepted, quarantined answers contribute to subsequent turns.

## Bounds and continuity

- Existing 4096 output tokens, 32768-byte complete input and 16384-byte returned-answer ceiling.
- Conversation context target: 23000 UTF-8 bytes; shed optional cards, then older turns. A final complete-input check remains authoritative.
- Up to eight local card printings, with explicit selected printing prioritized. New searches do not remain stuck on previous results. Follow-ups preserve previous candidates before new hits.
- 32 process-local sessions; 30-minute idle lifetime; up to six recent exchanges and 8000 bytes of history. Up to three accepted paragraphs per retained exchange; history compaction is marked. Source facts are refreshed, not treated as remembered model claims.
- Browser retains up to twelve displayed exchanges, never localStorage/IndexedDB. New conversation uses a new ID. Expired IDs return a clear state without inference. Server restart/reload loses continuity; this is not 7D memory.

## UI

The existing Figma-derived Agent shell now defaults to conversation without requiring a research mode or taxonomy selection. Card Detail selection and optional active-deck context feed the same panel. Recent answers remain visible; earlier context snapshots are labeled after navigation/revision changes. Ask is explicit and single-flight; navigation, hover and evidence inspection never infer again.

Supporting evidence is collapsed by default and expanded for proof requests. Structured values/provenance use the existing EvidenceValue renderer. Card names retain exact-printing artwork previews; unambiguous component names with locally available printed effect text use the existing popover. This does not change artwork-only competitive hover.

## Known limits / Alpha implications

This foundation uses a small deterministic alias/lookup orchestrator rather than unrestricted model-directed retrieval. Named lookup and broad intent coverage are bounded; the model must acknowledge missing specifics and reason conceptually. It has no live web capability. Tournament evidence is currently reused for an explicit selected card in the active deck, not every open-pool candidate. History/proposals are not saved decks, and long histories are compacted. Multi-process servers would need a shared ephemeral session design; a single local Alpha process is supported. The code uses platform-neutral Python/SQLite/React; existing launcher packaging still needs macOS Alpha validation.

Fake-provider tests establish wiring, authority boundaries and continuity, not the quality of a real model's reasoning. Live quality and factual fidelity require PM review. No live provider calls were made during implementation.

## PM QA

Keep the existing explicit provider/model and zero-cost authorization settings. Restart only when ready:

```powershell
Set-Location 'C:\Users\Mike\Documents\Codex\2026-09-25\referenced-chatgpt-conversation-this-is-an\work\phase5'
.\scripts\Start-Phase5-QA.ps1 -Action Restart -SourceRepository 'C:\Users\Mike\Documents\pokemon-tcg-lab' -ApiPort 8003 -WebPort 5175 -PhaseLabel 'Phase 7C.4 conversational foundation'
Invoke-RestMethod 'http://127.0.0.1:8003/api/v1/agent/status' | ConvertTo-Json -Depth 5
```

Check available/configured provider/model, `evidence_policy=conversational_default`, `external_research=false` before Ask. Each Ask makes one live call; this handoff does not execute or authorize them on PM's behalf.

Use these exact prompts as desired; keep follow-ups in the same conversation:

1. “What cards can mill my own deck, and which ones look easiest to build around?”
2. “What cards can help me punish or shut down Pokémon Tools?”
3. “What cards can move damage counters around, and which ones seem the most flexible?”
4. Follow 3 with: “Out of the cards you found, which ones look like the cleanest starting points and why?”
5. “What cards can mess with my opponent’s Energy without just doing damage?”
6. “Which of these is actually the best tournament option right now?”
7. “I want something annoying that makes it hard for my opponent to actually play the game. What cards fit that?”
8. “I want to build something stupid around making my opponent run out of cards. What directions could I take that?”
9. “If I wanted to make mill actually function, what problems would I need to solve besides just finding cards that discard from the deck?”
10. “How would I play a Great Tusk mill deck into Dragapult?”

Optional continuity sequence: “Build me an off-the-wall Pikachu deck, but I still want it competitive.” → “I like it, but how do I pilot it?” → “What are the three weakest parts of the list we just built?” → “My opening hand is Pikachu ex, Snorunt, Munkidori, Ultra Ball, Iono, Lightning Energy, and Super Rod. I’m going first. Talk me through the turn.” → “Before we lock this in, audit your own list. Check every card interaction, Energy requirement and legality assumption.” → “Prove it. Which parts are card facts, tournament evidence, and your reasoning?”

Verify reasoning survives empty retrieval; actual numeric/card facts agree with visible source data; Tools are not confused with Items; tournament uncertainty is qualified; the unusual concept is preserved; hover/proof does not generate calls; no deck/ownership writes occur. Stop and report any factual drift or unusable response instead of repeatedly retrying.

## Deterministic closeout verification

Focused backend: **27 passed**. Focused conversational frontend: **9 passed**. An initial local import-cycle error was corrected; a secret test expectation was corrected because the existing transport quarantines before assessment.

One final network-blocked backend gate covered **619 cases** across conversation, prior research/remediations, retrieval/mechanics, certified evidence and provider qualification. **617 passed initially**; two test assumptions needed correction: the status scope list now includes conversation, and a qualification gate test inherited PM's non-secret Gemini free-tier-confirmation environment flag. The scope assertion was updated; the inherited flag was removed only in the targeted test subprocess. **Both targeted rechecks passed**. No qualification test/contract or production zero-cost gate was changed. Two pre-existing dependency deprecation warnings remain. The broad gate was not repeated.

One final frontend gate covered **109 cases**: **104 passed initially**, five Library-only tests had ordered global fetch fixtures consumed by the independent new Agent status request. Those Library tests now isolate the Agent panel, whose real behavior is separately covered. Rechecking the entire Library module plus conversation module yielded **32 passed**. A real stale status-message race under React development remount was also fixed by ignoring aborted status requests; the compact browser recheck verifies it. Unsupported test-only matcher typings were removed; final **TypeScript passed**. No frontend assertions were weakened to accept broken Library behavior.

Browser: **3 passed** at 1440/900px, using mocked local API/artwork, blocked external requests, and assertions for explicit single calls, follow-up session IDs, card artwork, exact component text, proof inspection, panel bounds and rejected-response quarantine. The affected 900px scenario was rerun after the remount fix: **1 passed**. Its final screenshot was inspected. This is deterministic UI verification, not live model QA.

`git diff --check` passed. Frozen qualification directory, evidence/provider/qualification modules and all existing fixtures have no diff against the starting commit. The final gate includes the historical packet/hash tests. Existing certification tag objects from Phases 4 through 7C.2 and pre-web preservation remain unchanged. Main remains `100b0036a2f78abee2a61ad213cb07de63558a5e`. New preservation tag object: `38e644faef6a27dcbf0a2a7a0f9e1c7a6e48c9ac`, target `5987975589e87a45235504ac23c5abb7d3f3e0e2`.

Changed files:

- `src/pokelab/agent_conversation.py`: ephemeral context, local retrieval, conversational contract/assessment and one-call orchestration.
- `src/pokelab/agent_research.py`: request/status/dispatch seam and service-local sessions.
- `web/src/ConversationPanel.tsx`: default conversation, snapshot labels, proof/evidence and one-submit UI.
- `web/src/App.tsx`: default panel and internal strict-policy integration seam.
- `web/src/ResearchAgent.tsx`: shared evidence/diagnostic renderers and failure labels.
- `web/src/ResearchCardText.tsx`, `web/src/AssociatedCardPreview.tsx`: reuse hover for known component text.
- `tests/test_agent_conversation.py`, `tests/test_agent_deck_research.py`: conversation coverage and updated advertised scope expectation.
- `web/src/ConversationPanel.test.tsx`, `web/src/ResearchAgent.test.tsx`, `web/src/App.test.tsx`: conversational and preserved strict/library test isolation.
- `web/integration/card-pool-research.spec.ts`: default conversational card-resource browser checks.
- This handoff and ADR 002.

Ending SHA is the single implementation commit containing this document, reported in the PM handoff. No live provider calls, automatic retries, remote network work, merge, certification, durable memory or Phase 7D implementation occurred. **READY FOR PM LIVE QA**, with the limitations above and no claim of live model quality acceptance.
