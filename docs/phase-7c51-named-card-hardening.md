# Phase 7C.5.1 — Named-card factual hardening

Starting SHA: `56de0545bea1d2be1a522185e327d5fe2c664e7a`, verified clean.
Branch: `phase7c5-concrete-deck-resolution`. Implementation commit containing this
report is the ending state; no merge, push, tag or certification.

## Changes

- New `src/pokelab/agent_card_facts.py`: bounded local factual-clause correction.
- `src/pokelab/agent_conversation.py`: replace the old name-only automatic premise
  fallback with correction before identity/prose handling; preserve local corrected
  facts through the hybrid quantity filter.
- New `tests/test_agent_card_facts.py`; update two obsolete fixed-wording expectations
  in `tests/test_agent_conversation.py` to accept specific unresolved qualification.
- This report.

The previous fallback resolved names but did not reconcile normal attack/Ability
prose. It could reject an ambiguous name before applying active-printing priority.
Hybrid natural prose also did not pass through that name-only fallback. Correction
now operates on both normal parsed prose and separated hybrid prose.

## Exact trigger and correction

A bounded capitalized named subject followed by uses, attacks with, has an
attack/Ability, gives, recovers/retrieves, discards, draws, heals, blocks/prevents,
requires/costs, evolves from, is legal/illegal, or possessive attack/Ability phrasing
triggers local resolution. Maximum twelve triggered sentences, first subject per
sentence. A casual name mention or generic strategic judgment does not open the
correction snapshot. This is intentionally not exhaustive natural-language parsing.

The existing Resolver/DeckProvider and read-only Sources snapshot provide facts.
Requested active revision and card-source stamp must still match. Exact active
allocation printings take priority; materially different active records remain
ambiguous. Without an active match, existing local resolution applies. No arbitrary
same-name historical version is chosen.

A matched component name selects that printed component. A wrong name with no
matching component renders the applicable local components rather than guessing
which attack the model meant. Printed effects/costs/damage replace the factual
clause. Trainer/Stadium/Tool text uses the existing effect field. Evolution and
cached Standard legality get source-owned wording. Block/prevention interactions
explicitly remain unestablished by printed text alone; no new rules authority is
inferred.

Adjacent strategic sentences survive. A causal tail is retained as a hypothesis
to reassess after correction, not as a proven conclusion from the old premise.
Ambiguity or missing data substitutes a narrow factual qualification and continues
the answer. No entire-response rejection or universal citation requirement is added.

Corrections run before the old identity guard. Source-owned corrections survive the
hybrid filter that removes model-owned quantities. Their card facts are inspectable
in the envelope, with existing source/hash metadata and secret quarantine.

## Preservation and limits

The hybrid provider prompt, hidden action contract, natural output, action salvage,
proposed diffs, revision/count reconciliation, legality checks, role alternatives,
empirical protections and no-write boundary are unchanged. Ordinary provider routing
is unchanged. No frontend, transport, database schema or external data changes.

This is not semantic entailment or a complete rules parser. Lowercase names,
pronouns, predicates outside the bounded list and facts after the twelve-sentence
cap can escape detection. Already-correct factual clauses can be normalized to
printed wording. Multiple possible attacks are listed instead of silently assigning
a wrong attack name to one. Printed text cannot establish every interaction or
matchup implication; these remain qualified. Cached legality has existing freshness
limits. Large printed effects may be verbose; no response-length feature was added.

## Tests and PM QA

Final focused new suite: **11 passed**. Covers wrong attack name/effect, wrong
Ability, Trainer effect, active-printing priority, ambiguity, missing facts, casual
mention/no lookup, unchanged strategic inference, interaction qualification and
hybrid correction with an intact validated diff. Database byte comparisons establish
no writes. Earlier focused integration run: 95 passed, two wording-only assertions
updated for the more specific unresolved wording. No frontend work/tests required.
Single final network-blocked backend gate: **282 passed**, two existing dependency
deprecation warnings. Whitespace check passed.

No live provider or external network calls. Restart the existing configured QA
runtime on the ending commit, then use the current active deck:

1. “How does this deck work?”
2. “Why is Latias ex useful here?”
3. “How does Raging Bolt ex actually take big knockouts?”
4. “How does this deck do into Dragapult?”
5. “Give me the exact card names and quantities you would change, what you would remove, and why.”

Check attack/Ability names against the exact active printing, truthful interaction
qualifications, retained strategic explanation, hidden actions, checked quantities,
and unchanged deck state. Each Ask remains PM-controlled; no automatic retries.

READY FOR PM LIVE QA. This is not certification or a live quality claim.
