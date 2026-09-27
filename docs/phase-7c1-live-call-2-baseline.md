# Phase 7C.1 — first successful live Research baseline

## PM-reported result

Live Call #2 succeeded under the clarified contract at implementation commit
`fff9dedfce001f07be7eec24e9f938eaebf4b81d`. This is a product Research Mode
baseline, not a provider qualification result or Phase 7C.1 certification.

- Provider/model: Gemini / `gemini-3.5-flash-lite`.
- Selected card: Budew `me02.5-221`, holo.
- Deck: Dragapult — Rohit Potti — Regional Baltimore, MD.
- Workspace revision: 157; competitive window: 30 days.
- PM PASS: end-to-end execution and rendering; selected-card/deck context;
  evidence-backed facts; citations; facts/interpretation separation; no fabricated
  creator intent; limitations and authority boundaries.
- PM quality note: strategically shallow; interpretation largely restated the
  printed Item-lock effect rather than synthesizing its role in the surrounding deck.
- No further live calls authorized.

The PM assessment above is preserved as reported, not as an independent replay or
reassessment of the missing answer. The exact submitted Call #2 wording and its
returned evidence hash were not supplied in the post-call report.

## Safe execution metadata availability

The inspected local API access log contains one Research POST returning HTTP 200
since the latest log restart. Its last modification is
`2026-09-27T02:12:31.238359+00:00`; this is a log-file timestamp, not a precise
inference timestamp or latency. No structured result/answer metadata is logged.

Latency, input/output/reasoning token counts, actual/estimated provider cost and
exact finish reason: **not available from retained local records**. A successful
product answer passes the normal-completion gate (`stop` or `end_turn`), but the
individual value must not be guessed. The unchanged $0 policy is not a recovered
provider billing measurement.

Accepted structured answer: **not available in the inspected local artifacts**.
The API returns it to the browser; the UI holds it in React state. The inspected
path does not persist the answer or execution counters to a database/file. This
review did not contact the runtime, retrieve browser state, scrape process memory,
or inspect credential storage. No answer was fabricated or reconstructed as if it
were the actual model response.

PM reports production answer/citation validation passed and citation entailment
passed human review. Structural validation checks schema and citation membership;
it does not independently prove entailment. No independent revalidation of the
unavailable Call #2 answer is claimed.

## Offline evidence review

Reviewed the retained exact revision-157 fixture, independently verifying hash
`991a77f9439050275916f1933a169b7a5d886a4b1874c601e3381d9a2eb819f1` (17,173 bytes).
This is the reconstructed prior-call envelope, not an independently captured
Call #2 response hash. Conclusions below concern that retained evidence context.

Evidence already supports more specific, cautious interpretation:

- Budew's printed attack prevents the opponent playing Items from hand during
  their next turn. The selected-card evidence includes its 10 damage and retreat 0.
- The active deck has two Budew, four Drakloak and three Dragapult ex.
- Drakloak's included Ability text permits looking at the top two deck cards and
  taking one into hand once during the user's turn.
- The competitive evidence contains observed Dragapult-family prevalence and
  co-occurrence; these remain cached population observations, not causation,
  matchup effectiveness, optimality or evidence of pilot intent.

An example of permissible synthesis, authored for this review and **not the live
model's answer**: Budew can plausibly serve as temporary disruption while the deck
develops resources, because its attack restricts the opponent's Item options and
this particular list includes four Drakloak with repeatable card selection. The
value of that disruption depends on the opponent and board; the evidence does not
establish how much time it buys or that this is the pilot's documented plan.

That interpretation can cite selected-card evidence plus `active-deck`. It should
not assert an exact turn sequence, guaranteed setup window, confirmed interaction
ruling or external strategic consensus. An omitted attack-cost field must not be
promoted to an established zero-energy-cost fact.

## Evidence limitations versus synthesis limitations

The current partner-text selector intersects associated cards with the active
deck, sorts by functional identity, and takes three. Included text is Dreepy,
Drakloak and Risky Ruins. The competitive association order is Dragapult ex,
Dreepy, Drakloak, Rosa's Encouragement, Risky Ruins. Dragapult ex is present and
ranked first there, but its printed text is absent from the envelope. Identity
sorting is stable, but is not a relevance ranking.

Thus stronger generic deck-specific synthesis is already possible with Drakloak.
Explaining a particular Dragapult attack's strategic payoff would exceed the
retained text. Names/counts or a source-card hash are not substitutes for supplied
mechanics. Other missing context includes opponent state, matchup-specific Item
dependence, sequencing/piloting evidence and reviewed Budew rules support (the
fixture records UNKNOWN/UNSUPPORTED, unavailable, execution_authorized=false).

The PM-reported shallow answer is therefore not the absolute ceiling of this
envelope. However, without its accepted text, the amount of omitted synthesis
cannot be independently audited beyond PM's description. One successful response
also does not establish consistent strategic quality across questions.

## Recommendation for PM decision

Treat the reported PASS as sufficient live end-to-end evidence for considering
7C.1 closeout, with strategic depth recorded as a non-blocking quality limitation.
Do not certify automatically or change the prompt to require a Budew/Dragapult
conclusion. No further live call is necessary to establish the reported wiring
success.

If PM instead prioritizes a deterministic quality improvement, the smallest
candidate is to preserve existing association rank when selecting active-deck
partner text, with a stable identity tie-break and the same cap/budget/provenance.
That would include Dragapult ex, Dreepy and Drakloak for this fixture, using the
same local card source. It improves available context without claiming ranked
association proves synergy. It changes retrieval behavior and therefore requires
separate approval; it is not implemented here and is not guaranteed to improve a
model's answer.

Suggested offline coverage for that optional change: multiple unrelated card/deck
fixtures, rank-preserving intersection, stable ties, selected-card exclusion,
unchanged caps and complete functional counts, explicit budget omissions,
read-only state, and no special Budew/Dragapult logic. A generic human quality
rubric should ask whether interpretations connect cited selected-card mechanics
to cited deck evidence, while accepting insufficient evidence rather than forcing
a predetermined strategic explanation.

This review made no network or provider calls, changed no production code or
prompt, and performed no retry, runtime restart, merge, certification or 7C.2 work.
