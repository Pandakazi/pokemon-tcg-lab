# 7C.5 — Strategic recommendation permission

Start: clean `phase7c5-concrete-deck-resolution` at
`b06575970defd35bd9ee17b92c65091e3720e55b`.

## Trace and exact restriction

No classifier, Pydantic rule or completion check requires empirical evidence,
creator intent or a declared matchup before accepting proposals. The current
provider's stated belief is not itself proof of an unseen code gate.

Two locally established restrictions mattered:

1. `agent_conversation.SYSTEM` said “Missing facts remain unknown; offer conceptual
   reasoning instead.” This conflated unknown exact facts with permission to
   nominate a concrete candidate for later resolution. The same prompt permitted
   strategic inference, but did not explicitly grant exact recommendations without
   empirical proof, matchup context or creator intent.
2. `agent_conversation.run` replaced all concrete-diff paragraphs with
   `diff_paragraphs(report)`. That protected arithmetic but also removed the model's
   strategic explanation. The structured `proposal.rationale` was stored but not
   rendered. This was actual suppression, separate from provider behavior.

## Small change

The provider prompt now distinguishes objective fact, strategic inference,
recommendation/hypothesis and empirical performance claim. It explicitly permits
cuts, additions, ratios and structural changes without tournament proof, matchup
selection or creator intent. Missing empirical support affects confidence, not
permission. Unknown replacements may be nominated as roles for local resolution.

The concrete prompt identifies rationale as a strategic hypothesis, not a proof
obligation. Validated diff summaries remain authoritative. A nonempty rationale can
now appear underneath, labeled “Strategic hypothesis (not a proven tournament
improvement)”. The existing empirical detector qualifies unsupported win-rate claims.
A bounded check keeps numbers, ordinals and explicit count/state wording out of this
rationale channel; those belong in the canonical diff summary. Rejected card-premise
dependencies are not restored through rationale. These checks affect only the exact
diff rationale channel, not ordinary conversational reasoning.

No schema, provider routing, completion limit, retrieval, deck validation or write
path changed. Ordinary questions still use the small provider contract. Cuts,
current/resulting counts, revision, legality, size and copy limits retain their
existing local validation. Unresolved roles remain visible and do not suppress the
whole response. No universal semantic checker or empirical justification requirement
was introduced. Live provider adherence still needs PM evaluation.

## Verification and files

Changed `src/pokelab/agent_conversation.py`,
`src/pokelab/agent_deck_proposals.py`,
`tests/test_agent_deck_proposals.py`, and this report.

Focused tests: **81 passed**. New fixtures test an improvement question followed by
exact changes with no empirical evidence, no creator intent and no matchup; accepted
strategic rationale; qualified unsupported 8% claim; suppressed stale ordinal;
validated counts/revision; explicit unresolved replacement and no database writes.
Existing tests retain ordinary routing and direct/follow-up diff coverage.

Single final network-blocked backend gate: **265 passed**, two existing dependency
deprecation warnings. Whitespace passed. No frontend changes.
No live provider calls, external network calls, retries, deck writes, merge, tag,
certification or Phase 7D work.

## PM retest

Restart the existing configured QA runtime at this branch's ending commit. Ask
“Is there a way to make it better?” followed by “Give me exact cards and quantities.”
Do not supply a matchup or creator intent. Expect a testable structural recommendation
with locally checked counts and visible rationale, or an explicit unresolved role.
It must not require tournament proof to help, nor claim proven performance.

READY FOR PM LIVE QA.
