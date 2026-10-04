# 7C.5.1 — Final PM routing and rendering remediation

Start: clean `phase7c5-concrete-deck-resolution`,
`2c263b1de33cd30bb9e67bc9a537427b476d7943`.

## Proven code findings

Concrete routing: `agent_deck_proposals.lifecycle` lacked replacement/substitution
phrasing and required “exactly” in its comes-out/goes-in pattern. Consequently the
PM weakest-cards-plus-replacements request selected EXPLORE, avoiding the hybrid
action contract. The existing validator could calculate counts correctly only when
a proposed diff reached it. These are deterministic code findings, not inferred
from the Agent's self-description.

Factual rendering: `agent_card_facts.reconcile` scans named subjects/predicates with
CLAIM, generates a complete correction template, then previously replaced the span
from `match.start()` to sentence termination. A match inside an existing sentence
therefore preserved a prefix like “through its signature” or “Adding a third” before
inserting “For X, the resolved printing states…”. The same regex could identify an
embedded attack name as a card subject. Backward iteration protected offsets but did
not make that partial-sentence replacement grammatical. This establishes the actual
mechanism; prior Agent speculation was not used as source evidence.

## Narrow fixes

- Classifier now recognizes explicit replacements of cards/slots/them/these, exact
  changes and comes-out/goes-in wording. Weakness analysis alone remains EXPLORE.
- Factual corrections replace the complete affected sentence rather than inserting
  a standalone template mid-sentence. A real card named earlier in that sentence
  takes precedence over an embedded component name when available locally.
- Removed “For X, the resolved printing states” templates. Printed text is presented
  directly with its card/component name. Missing details receive a complete
  conversational qualification. Ambiguity and reviewed-rules limits remain intact.
- Unverified causal tails containing exact numbers/resource math become a
  verification qualification. Immediately following dependent precision sentences
  (“It…”, “This attack…”, “You must…”, etc.) are omitted when exact facts are missing.
  Later strategic discussion survives. This bounded dependency check does not claim
  universal entailment or track every cross-paragraph implication.

Local active revision/counts, construction checks, hybrid natural prose plus hidden
actions, role handling, empirical boundaries and no writes are unchanged. No strict
JSON-only requirement, automatic retries, new provider routing or Phase 7D work.

## Files and verification

- `src/pokelab/agent_deck_proposals.py`: concrete-intent patterns.
- `src/pokelab/agent_card_facts.py`: sentence-safe replacement and bounded precision handling.
- `tests/test_agent_deck_proposals.py`: all six requested phrasings, weakness-only
  contrast, and two additional PM-count hybrid integration cases.
- `tests/test_agent_card_facts.py`: embedded wrong attack, embedded Trainer correction,
  missing premise with dependent discard/damage math and retained strategy.
- This report.

Focused tests: **110 passed**, including existing conversation/hybrid tests and
read-only assertions. New PM prompts use the count fixture and verify Area Zero
3 → 4 and Grass 6 → 7, without stale ordinal prose. Single final network-blocked
backend gate: **294 passed**, two existing dependency deprecation warnings.
Whitespace passed. No frontend changes or frontend tests needed.

## PM retest

Restart the existing configured QA runtime at the ending commit. With the current
active deck selected:

1. “What are the 3 weakest cards in the deck and what three cards would you replace them with and why?”
2. “What would you replace these three slots with?”
3. “What are the weakest parts of this deck?”
4. “How does Raging Bolt ex actually take big knockouts?”
5. “Why would you add another Boss’s Orders?”

Expect checked concrete diffs for substitution requests, ordinary strategic analysis
for weakness-only requests, no correction template spliced inside sentences, and no
unsupported precision after unresolved attack facts. Confirm no deck changes.

No live provider calls or external network calls during implementation. No push,
merge, tag or certification. READY FOR PM LIVE QA. Certification remains a later
PM decision if this retest passes.
