# Phase 7C.2 Pass 2 — Research integration (PM QA pending)

Extends the existing `POST /api/v1/agent/research`; no parallel Agent client,
provider adapter, answer model, validator or active-deck store. No Pass 1 rules or
frozen artifacts were changed. No live calls or certification were performed.

## Context and API

Deck requests send `scope=active_deck_research`, `question`, acknowledged workspace
`revision`, `window`, and optional explicit `archetype` key. Omit printing/finish.
The selected-card path retains `scope=selected_card_research`, `printing`, optional
`variant`, revision/window/question and its certified 7C.1 evidence construction.
Scope/printing must agree; redundant composition/mechanics are not accepted.

`GET /api/v1/agent/status` retains existing fields and adds both supported scopes
and up to 500 explicitly identified, locally cached archetype choices. These are
comparison populations, not inferred identities of the user's deck. Unknown
archetypes are never derived from card names, deck names or question text.
Comparison-intent requests lacking a resolvable archetype/eligible population
return `comparison_unavailable`, with no provider call. Composition-only questions
can proceed with unavailable comparison evidence. Selected-card requests retain
their original 7C.1 context and behavior.

## Evidence and provider boundary

On each deck submission, server-side `Sources` read transactions resolve the
current workspace/revision and current local competitive cache. The approved
`build_profile` and `select_evidence` produce the unmodified deterministic packet.
A versioned deck envelope adds the complete functional composition and its
workspace source reference (`active-deck`), allowing false premises to be checked
against the actual deck even when optional evidence is capped.

The evidence packet remains capped at 24 KiB. The wrapper is bounded to 32 KiB,
and the combined system prompt plus envelope must also fit the existing 32 KiB
transport input limit; exceeding either returns a safe budget failure rather than
increasing limits. The original Answer/Pydantic schema, citation membership,
strict JSON parser, 16,384-byte output ceiling, truncation/diagnostic handling,
single-flight execution and $0 gates are reused. Gemini still receives its existing
structured-output configuration. No repair, routing, retries or fallbacks.

The deck prompt derives its answer/citation requirements from the existing prompt;
only research scope and deck-specific epistemic instructions are extended.
Models must use computed statistics, not calculate their own populations. Facts,
plausible interpretation and limitations remain separate. Creator intent, matchup
performance, piloting-guide authority and mechanical synergy cannot be inferred
from empirical co-occurrence. Replacement search, deck edits/optimization and
actions remain unsupported. Local structural validation is not automatic semantic
entailment verification; PM must review the returned claims.

Responses expose captured revision, archetype, as-of/window, eligible/excluded
counts, confidence/self-comparison state, snapshot/profile/packet hashes, packet
bytes and coverage. A clearly labelled sample of at most ten captured population
source references provides inspectable list URLs/dates/hashes, not a dump of raw
competitive data. The sample is not the denominator. Prior immutable answers stay
labelled with their submitted snapshot when current context changes.

## UI and freshness

Deck Builder opens the existing Agent panel in `Context: Active Deck`. It can Ask
without selecting a card. The comparison dropdown is explicit and starts empty.
Navigating to a deck card's Detail selects its exact printing/finish automatically.
The old Ask-about-card button is a convenience for selection/focus, not a required
step. Clear selected card returns to Active Deck. Card navigation, removal, deck
change, revision/window/archetype changes clear the unsubmitted question; completed
answers remain. A context-key guard prevents submitting a draft from an obsolete
context before React effects complete. Removed cards/new deck IDs clear selection.

Only explicit Ask posts Research. Selecting/deselecting, typing, opening/closing
and context cleanup never infer or resubmit. Status/workspace/card reads remain
ordinary local API reads. Credentials remain server-side.

There is no new synchronization scheduler. The production path reads current
configured SQLite stores on each submission, never inspection artifacts/fixtures.
Tests prove newly imported local evidence changes the population and hashes.
If a newly synchronized archetype is absent from an already-open dropdown, reload
the page to refresh choices. As-of is the server's current date, with event/fetched
dates and snapshot hashes preserving actual evidence age; as-of does not claim a
fresh live Limitless fetch. Existing workspace copies lack source-list origin IDs,
so product self-exclusion remains explicitly unavailable; no identity is guessed.

## PM manual QA — separately authorized calls only

No environment changes are required for the previously configured Gemini
`gemini-3.5-flash-lite` $0 path. In that existing configured PowerShell session:

```powershell
Set-Location 'C:\Users\Mike\Documents\Codex\2026-09-25\referenced-chatgpt-conversation-this-is-an\work\phase5'
.\scripts\Start-Phase5-QA.ps1 -Action Restart -SourceRepository 'C:\Users\Mike\Documents\pokemon-tcg-lab' -ApiPort 8003 -WebPort 5175 -PhaseLabel 'Phase 7C.2'
Invoke-RestMethod 'http://127.0.0.1:8003/api/v1/agent/status' | ConvertTo-Json -Depth 5
```

Check available=true, explicit Gemini/model, both scopes and cached archetypes.
Open `http://127.0.0.1:5175/deck-builder` with the intended active deck; record its
current revision/window. Clear any card and explicitly choose Dragapult as the
comparison population. Submit only the individual calls authorized by PM:

1. “How does this deck differ from typical Dragapult decks?”
2. “What is this deck trying to do?”
3. “What common Dragapult cards is this deck not playing?”
4. “Which cards does this deck run more or fewer copies of than usual?”
5. “Why did Rohit Potti build the deck this way?”
6. “Why is this deck built around Charizard ex?”
7. “What should I cut to improve this deck?”
8. Select Budew: “What's the point of running Budew in this deck?”
9. Switch to Risky Ruins: “What role does Risky Ruins play in this deck?”

Review factual citations, interpretation boundaries, missing evidence, comparison
denominators, as-of/snapshot age and self-comparison status. Inspect evidence and
the labelled source sample. Confirm no invented intent, premise, matchup claim or
replacement action. On rejection inspect bounded Validation details; do not retry
without authorization. These are QA prompts, not hardcoded product cases.

For zero-call UX checks, type an unsubmitted question, switch/deselect cards,
change comparison/window, remove a selected card, and change/clear the active deck.
Verify input clears, prior answer remains with submitted snapshot/stale label,
context is correct, and no Research POST occurs. Opening/closing the panel and
typing must not create Research POSTs. This implementation did not restart the
runtime or execute these live/manual checks. PM QA is required before certification.

## Deterministic verification

- Focused backend: 157 passed, including 20 new integration cases and all ten
  requested golden scenarios with fake providers.
- Focused Agent frontend: 20 passed.
- Final backend coverage: 712 passed with external sockets blocked, in two
  nonoverlapping batches (605 Research/product cases and 107 remaining repository
  cases). No backend tests were repeated to complete that coverage. Only existing
  Starlette/FastAPI deprecation warnings were reported.
- One complete frontend run: 87 passed / 3 failed initially. The new status fetch
  ran unnecessarily before a deck loaded, disturbing Library requests. Gating it
  on loaded deck state fixed the issue; all 43 affected Library/Agent tests then
  passed. The other 47 cases passed in the full run. No failures remain; the
  entire frontend suite was not rerun.
- TypeScript, production frontend build and `git diff --check` passed.
- Syntax-tree comparison confirms unchanged Answer, Statement, assessment,
  selected-card envelope builder and selected-card system prompt. Pass 1,
  qualification/fixture artifacts and prior certification tags are unchanged.

A provider-free preflight against the current local QA stores, revision 157 on
2026-09-27, resolved 137 eligible Dragapult lists: packet 13,556 bytes, envelope
16,567 bytes, combined system/envelope 21,302 bytes. This is a dated observation
of the local 30-day population, not a new sync or a frozen production baseline.
Self-exclusion was explicitly unavailable. No API/provider request was sent.
