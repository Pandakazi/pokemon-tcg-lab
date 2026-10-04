# 7C.5 — Hybrid concrete recommendation output

Start: clean `phase7c5-concrete-deck-resolution` at
`7d84c2363a2c18e8aa933a988287fd67162afbd7`.

## Contract change

Previously every non-EXPLORE request used a complete Answer JSON schema; active
RECOMMEND additionally required a typed diff. The concrete provider path now sends
natural-prose instructions and **no response_schema / response_format**. It does not
ask for JSON-only visible output. EXPLORE retains the successful small conversation
contract. Strict Research and qualification contracts remain unchanged.

The provider appends one optional intent block after its prose:

```text
<POKELAB_ACTIONS>{"changes":[{"action":"remove","card_name":"Jamming Tower","quantity":1},{"action":"add","role":"single-prize draw support","quantity":1}]}</POKELAB_ACTIONS>
```

Entries contain add/remove, a name or role, and a positive integer quantity delta.
Optional rationale is strategic prose; confidence may be supplied but is not state
authority. No card IDs, revision, resulting counts, legality or evidence are required.
The block is bounded to 8192 bytes and 60 entries. The overall output/completion and
secret boundaries are unchanged. Historical valid Answer objects remain accepted
for compatibility, but are neither requested nor required.

## Parsing and authority

`agent_hybrid.parse` separates prose from the action block and validates entries
independently. Missing/invalid quantities are not guessed. Valid entries become the
existing Proposal/Candidate objects. Multiple/incomplete blocks are unresolved rather
than merged. Arbitrary prose is never converted into actions. Hidden content is
removed before display/history; only accepted structured state and bounded reason
codes survive.

With an active deck, actions enter the existing exact-revision diff evaluator.
Without an active deck, add entries represent a proposed list; removes remain
unresolved. DRAFT can be partial. FINALIZE still requires resolved complete intent
and supported construction checks before the list is called finished.

Current/resulting quantities, cuts, legality, copy limits and size come from local
validation. Strategic sentences appear first, followed by the canonical diff.
State/action sentences are replaced by that summary; separate strategic sentences
and safe “because…” tails are retained. Unsupported empirical claims retain the
existing qualification behavior. This is bounded sentence reconciliation, not a
general NLP action extractor or universal semantic checker.

## Degradation

- Valid summary: resolve and render the checked proposal with strategic prose.
- Missing/malformed summary: preserve strategic discussion and explicitly state
  that concrete changes are unresolved; no fake proposal is created.
- Partially valid summary: salvage valid entries, mark the overall report
  NEEDS_REPAIR/UNRESOLVED, and never label the subset a complete validated change.
- Unknown card/role or invalid cut: existing local explanations and alternatives
  remain available. Role search supplies legal candidates; it does not silently
  select a strategic replacement. Unresolved slots stay unresolved.
- No useful prose and no usable action intent: existing safe failure applies.
- Truncation, secrets and true internal/provider failure retain existing boundaries.

## Files and verification

- New `src/pokelab/agent_hybrid.py`: prompt, bounded action parser, prose reconciliation.
- `src/pokelab/agent_conversation.py`: hybrid request/response orchestration.
- `tests/test_agent_deck_proposals.py`: natural output, degraded summaries, PM counts,
  retained causal rationale, ambiguous discussion and no-write assertions.
- This report.

Initial focused run: 86 passed, one obsolete wording assertion failed. Updated that
assertion; an intermediate indentation typo prevented collection and was corrected.
Final focused proposal module: **43 passed**. The final gate also covers the existing
conversation module. No frontend changes, so no frontend/build work was performed.
Single final network-blocked backend gate: **271 passed**, two existing dependency
deprecation warnings. Whitespace check passed.

## Limits and PM QA

No live provider calls were made. Mock success does not prove live provider behavior.
The bounded prose reconciliation can remove a mixed strategy/state sentence if it
cannot safely separate it; standalone reasoning and causal tails are preferred.
No universal entailment claim is made. Payload syntax damage is not heuristically
repaired; valid entries are salvaged only from parseable JSON. Role choices remain
explicitly unresolved when no exact selection is established. Prose must precede the
hidden block; trailing content is not displayed. Existing cached legality limits apply.

Restart the existing configured QA runtime at this branch's ending commit, then use
the active revision-158 deck:

1. “How does this deck work?” — ordinary route remains unchanged.
2. “Give me the exact card names and quantities you would change, what you would remove, and why.” — natural reasoning plus checked proposed changes.
3. “Okay. Make those changes concrete. What exactly comes out and what exactly goes in?” — same hybrid path.
4. “I need a single-prize draw support slot. What would you change?” — role candidates or explicit unresolved slot.
5. “I might cut Jamming Tower, although I could keep it and shave Cyrano instead. Talk through the tradeoff.” — discussion must not invent committed actions.
6. “Give me the final 60.” — incomplete intent must not be labeled finished.

Check source revision, 3-to-4 Area Zero and 6-to-7 Grass arithmetic if those additions
are proposed, retained rationale, no raw hidden block, no write and no automatic retry.
Each Ask is a PM-controlled call. No merge, tag, push, certification or Phase 7D work.

READY FOR PM LIVE QA.
