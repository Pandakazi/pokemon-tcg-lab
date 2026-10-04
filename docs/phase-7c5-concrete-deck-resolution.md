# Phase 7C.5 — Concrete deck resolution

Status: implemented for PM live QA; not certified. No live provider calls.

## State and scope

Verified clean starting branch `phase7c4-conversational-agent` at
`d5228890e3c113eb88b0731d19a52c5a67142674`. Implementation branch:
`phase7c5-concrete-deck-resolution`. The implementation commit containing this
document is the ending commit. Main remains `100b0036a2f78abee2a61ad213cb07de63558a5e`.
No merge, push, tag, certification, schema migration or Phase 7D work.

This extends ADR 002's conversational default. Strict Research, provider transport,
Pass 2 retrieval and frozen qualification artifacts are unchanged.

## Implementation

- `src/pokelab/agent_deck_proposals.py`: typed transient proposals, canonical local
  resolution, existing Deck Builder validation, role alternatives and advisory checks.
- `src/pokelab/agent_conversation.py`: prompt extension, optional proposal/premise
  parsing, post-provider resolution, corrections and session-only proposal continuity.
- `web/src/ConversationPanel.tsx`: proposed list/diff review with no write controls.
- Tests: `tests/test_agent_deck_proposals.py`, `tests/test_agent_conversation.py`,
  `web/src/ConversationPanel.test.tsx`, `web/integration/deck-proposal.spec.ts`.
- This closeout document.

### Lifecycle and triggers

No mode selector. A bounded question classifier gives explicit partial intent
precedence: “not ready”, “just … shell/core”, “sketch”, “partial list/deck” → DRAFT.
Finalize/finished/give me the 60/resolve slots/tournament legal/PTCGL → FINALIZE.
Recommended deck/list, actually play, specific/exact cards, quantities, cut/add or
cards to change → RECOMMEND. Shell/core/draft → DRAFT; otherwise EXPLORE.
Recent conversation and the latest structured proposal are supplied to the model.
The classifier itself is lexical, not a universal intent recognizer.

The model can nominate cards outside initial retrieval. Optional typed `proposal`
and `premises` trigger local resolution after the single provider completion.
A bounded fallback recognizes named subjects before “has an Ability/attack”,
“uses”, “deals”, “discards” or “moves”. General reasoning does not require a list.
Malformed optional proposals degrade to a visible unfinished-concept qualification.

### Named facts and lists

Names resolve through the existing catalogue and DeckProvider functional identities.
Explicit printing IDs must match their supplied names. Distinct current functional
versions remain ambiguous; they are not guessed. Basic Energy uses the existing
functional type identity. Exact printing remains separate presentation information.

Material premises may provide exact printed `expected_text`; mismatches produce
source-owned printed facts and a correction, replacing dependent prose rather than
silencing the answer. The optional `depends_on` annotation identifies dependency.
This is bounded premise checking, not semantic entailment of arbitrary paraphrases.

Lists use ephemeral Deck Builder entries/allocations. Finalize/recommend require a
complete list. Drafts may retain named or role-only unresolved slots. A list with
unresolved slots is explicitly unfinished; no arbitrary fillers are invented.

### Proposed diff and revisions

The returned `pokelab-proposal-v1` report contains `status: PROPOSED`, lifecycle,
format, kind, name, deck_id, source_revision, source_content_hash, cards, adds,
removes, rationale, resolution_status, validation_status, legality_status,
hard_validation, strategic_diagnostics, repair_notes, alternatives, premises and
`writes_performed: false`. Rows expose canonical functional card_id, printing_id,
name, category and quantity. Diff rows include actual source current_quantity;
cuts additionally record whether they validated.

After inference, a fresh read-only snapshot rechecks the exact requested workspace
revision and card-source stamp. Changes yield STALE, never a validated current diff.
Cuts are checked cumulatively against a copy of the actual source list; additions
use real existing quantities. Missing cuts offer actual source-card choices, with
no arbitrary replacement cut. The resulting copied document is validated locally.
No active/saved deck or collection write occurs. Future approved writes would still
need their own revision recheck and explicit allocation/approval policy.

### Legality, quality and repair

Hard checks reuse Decks.validation/Lab: supported allocation consistency, total 60
for complete lists, maximum size, name-based copy limits, curated Basic Energy
exceptions, Basic Pokémon requirement, ACE SPEC uniqueness, Pocket exclusion and
cached format legality. Unknown metadata remains unknown. LEGAL_SUPPORTED_CHECKS
does not claim universal tournament certification or current ban-list coverage.

Strategic diagnostics are separate advisory messages: absent printed evolution
predecessor; printed Darkness attachment condition without a Basic Darkness source
(Special Energy compatibility explicitly uncertain); printed attack cost exceeding
the list's total Basic Energy when no Special Energy is present. Alternate evolution
routes and cost reduction are acknowledged. No simulation or matchup rating exists.

Repairs preserve the role: existing retrieval searches same role, printed effect,
then small function aliases (draw/recovery/devolution/mill), returning up to three
locally legal candidates. Low-commitment single-prize draw filters Basic Pokémon
and multi-prize suffixes. Engine/matchup fit remains an explicit comparison task,
not a fabricated deterministic ranking. No broad redesign is automatic.
ACE conflicts suggest keeping the first proposed anchor with its declared role,
and offer non-ACE alternatives for displaced roles. This is provisional, not an
optimized strategic verdict. Invalidity returns explanation/options, not no-answer.

## Verification

- Initial focused proposal run: 17 passed, one failed; corrected role filter.
- Focused proposal/conversation rerun: 67 passed. Two further safety regressions
  (removing illegal cards and post-resolution secret quarantine) passed in final gate.
- One final network-blocked backend gate: **366 passed**, two existing dependency
  deprecation warnings. Includes proposals, conversation, Agent context/Research,
  card-pool, deck validation and exact allocations.
- Focused frontend: **10 passed**. One final frontend gate: **110 passed**.
- TypeScript: passed.
- Minimal browser gate: **5 passed**, including proposal review at 1440/900 pixels,
  continuity/evidence/hover, safe rejection/no retry, one request and no deck writes.
  Inspected the 900-pixel proposal screenshot; controls and review remain inside panel.
- Database byte comparisons and read-only connection assertions cover proposal paths.
- No external network/provider calls; browser checks use local runtime and fake APIs.

## Known limits

PM must assess live model adherence, usefulness and factual fidelity. Structured
proposal/premise cooperation plus bounded fallback is not universal fact detection.
Local repair offers choices; it does not rerun the model or guarantee an automatically
repaired legal 60. Cache legality can be stale and supports only existing rules.
Quality diagnostics do not cover every prize, Bench, search or recovery weakness.
Unresolved slots remain unfinished when no suitable option is established.
PTCGL wording selects FINALIZE but no new PTCGL exporter was built.
Proposal continuity is process-local, expiring and bounded; prompt budgeting may
omit the prior proposal with an explicit omission. No durable deck memory exists.

## PM manual QA

Restart the existing QA runtime in the configured PowerShell session; no new
credentials, model selection, routing or automatic calls are introduced:

```powershell
Set-Location 'C:\Users\Mike\Documents\Codex\2026-09-25\referenced-chatgpt-conversation-this-is-an\work\phase5'
.\scripts\Start-Phase5-QA.ps1 -Action Restart -SourceRepository 'C:\Users\Mike\Documents\pokemon-tcg-lab' -ApiPort 8003 -WebPort 5175 -PhaseLabel 'Phase 7C.5 concrete deck resolution'
Invoke-RestMethod 'http://127.0.0.1:8003/api/v1/agent/status' | ConvertTo-Json -Depth 5
```

Each Ask is a separate PM-controlled live call. Check source revision, inspect local
facts as needed, and confirm active/saved decks and ownership remain unchanged.

1. “Build me an off-the-wall Pikachu deck, but I still want it competitive. Give me the finished 60.”
2. “I need a low-commitment draw engine that won’t give up two prizes. What fits?”
3. “Consider [a locally confirmed illegal card] for recovery in this list. What current legal card preserves that role?” Use a card verified in the local catalogue; do not assume historical legality.
4. “Discuss this Munkidori list with no Darkness source. What needs changing?” Supply/select that list.
5. “I’m not ready for a 60 yet. Just sketch the shell.”
6. “Okay, resolve the remaining slots and give me the 60.”
7. “I hate that draw engine, but don’t change the Pikachu concept.”
8. “This proposed list includes two ACE SPEC cards. Which would you keep, why, and what preserves the other role?” Supply the conflicting list.
9. “Is this list legal, and what are its structural weaknesses?” Use a locally legal but poor list.
10. “Give me the exact cards and quantities you would change, what you would remove, and why.” Use the active deck and inspect its displayed revision.
11. “Cut one [a locally confirmed absent card] from this active deck and replace that role.” Check the mismatch and actual source choices.
12. “How competitive is this against Dragapult or Alakazam?” Inspect variant resolution and qualified strength claims.
13. “Why did you choose this card instead of the other two?” Inspect facts underneath conversation.

Also check “What cards can mill my opponent?”, “Out of those cards, which fit this
weird concept?”, broad empty-retrieval discussion, proof on demand and card/attack
hover. No automatic second call or deck application should occur.

**READY FOR PM LIVE QA.** This is readiness for evaluation, not certification.
