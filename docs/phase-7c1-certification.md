# Phase 7C.1 — Selected-Card Research

**CERTIFIED / PM PASS — 2026-09-26.** Mike explicitly certified the selected-card
Research implementation at `771b341089e63217097ce145c3952c95c41d8259` following
manual live QA. This documentation-only closeout records that acceptance.

Annotated tag: `phase-7c1-selected-card-research-certified-2026-09-26`, targeting
the final closeout commit on main. Follow the established Phase 7B convention:
fast-forward only, publish main, the development branch and the annotated tag;
preserve earlier certification tags. Canonical repository:
`https://github.com/Pandakazi/pokemon-tcg-lab.git`.

## Certified scope and boundaries

Selected-card natural-language questions in active-deck context follow:
question/context → deterministic retrieval and local aggregation → bounded,
versioned evidence envelope → explicitly configured provider/model → locally
validated answer with inspectable citations. Research remains read-only. The AI
does not replace deterministic card, deck, collection, competitive or rules
authority. Facts are separated from plausible interpretation; association does
not establish causation, synergy or creator intent. Explicit provider selection
and $0 controls remain; no automatic routing, retries, fallbacks, writes or memory.

Strict JSON/Pydantic validation, outcome semantics, citation membership,
16,384-byte answer ceiling, truncation handling, safe diagnostics and secret/raw
output/reasoning quarantine remain authoritative. Human PM review evaluates
grounding and citation entailment; structural validation alone does not prove
them. The 7A packet, 7B qualification artifacts/results/hashes, evidence budgets
and retained Budew revision-157 hash remain unchanged:
`991a77f9439050275916f1933a169b7a5d886a4b1874c601e3381d9a2eb819f1`.

## PM acceptance evidence

PM manual QA passed role/purpose, copy-count, mechanics, active-deck composition,
multi-type Energy, empirical competitive evidence, bounded interpretation,
false-premise resistance, unsupported creator intent, insufficient evidence,
rules/mechanical questions, removal counterfactuals, matchup/use cases,
fail-closed contracts and safe validation diagnostics.

Notable PM-reported examples:

- Drakloak: four-copy reasoning and Recon Directive; rejected Energy-acceleration
  false premise.
- Crispin: connected its multi-type Basic Energy search/attachment effect to this
  deck's Fire/Psychic/Darkness composition.
- Special Red Card: late-game hand-disruption role.
- Fezandipiti ex: quantity, population distribution and once-per-turn Flip the
  Script, without inventing pilot intent.
- Ultra Ball: rejected use as the only card in hand because its cost requires
  discarding two other cards.
- Rohit Potti intent: insufficient evidence rather than fabricated intent.
- Night Stretcher alternatives: acknowledged the current evidence boundary;
  comprehensive discovery/comparison remains 7C.3.

These are PM-reported assessments, not fabricated retained response transcripts.

## Structured-output reliability remediation

Earlier Crispin removal, Budew matchup and Risky Ruins role prompts failed the
answer contract. A reproduced Crispin failure specifically established invalid
JSON; PokéLab failed closed and exposed safe diagnostics. Earlier unrecovered
responses retain their historically indeterminate diagnoses.

Commit `771b341089e63217097ce145c3952c95c41d8259` requests Gemini structured output
on the existing `/v1beta/openai/chat/completions` transport:
`response_format.type=json_schema`, `strict=true`, with the schema directly from
`Answer.model_json_schema()`. No compatibility projection, JSON repair, fence
stripping, substring extraction, coercion, retry or fallback was introduced.
Local validation remains authoritative.

PM subsequently reran each exact previously failing prompt once: Crispin PASS,
Budew PASS, Risky Ruins PASS, with no retries. PM accepts the demonstrated
reliability remediation as sufficient for 7C.1, not a universal compliance guarantee.

Accepted implementation verification: 270 focused tests and 550 network-blocked
backend regression tests passed. Closeout uses documentation/diff, ancestry,
artifact and Git-ref checks only; no repeated backend/frontend/browser suites,
provider calls or QA runtime restart. Git publication/ref checks are the only
network operations authorized as part of closeout.

## Non-blocking backlog and exclusions

Preserved, not implemented here: robotic prose; partner-text relevance ranking;
clearer mechanics versus empirical co-occurrence; card-click context updates;
clearing questions on card changes; hover printed text/richer card information;
context-aware competitive hover; richer strategy/piloting knowledge; QA restart
PowerShell freeze issue.

Deck-level/archetype questions belong to 7C.2; bounded alternative-card discovery
and comparison to 7C.3; proposed actions and research memory to 7D. None is included
in this certification or started by this closeout. No production behavior changes.
