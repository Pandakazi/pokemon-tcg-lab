# Phase 7C.4 — Optional conversational annotations

Verified clean branch `phase7c4-conversational-agent` at `69e8ab677952979dd660e22b78a0ac70fff3e727`. This report supersedes the annotation requirements in the initial 7C.4 handoff; retrieval, orchestration, context and strict research are unchanged.

## Established cause and actual path

`ResearchService._run` dispatches `scope=conversation` directly to `agent_conversation.run`. The configured provider receives `agent_conversation.SYSTEM` and, for Gemini, `Answer.model_json_schema()`. After normal completion, `agent_conversation.assess` runs. It never invokes the legacy `agent_research.assess`, `research_grounding.violation`, or card-pool prose validator.

The initial conversational Answer really had three required fields: literal `version`, `paragraphs`, and `fact_ids`. Each paragraph required `text` and `evidence`. Missing/null/wrong-shaped annotations failed Pydantic validation. Unknown fact/evidence IDs and duplicated **fact_ids** then caused `invalid_reference`, blanking the entire answer. Valid duplicate paragraph evidence IDs were not rejected at that second check; they are now deduplicated. Thus the separate conversational path still imposed rigid requirements on optional annotations.

This establishes the code-level choke point and deterministic reproductions, **not the exact historical model-output defect**. No rejected historical response or safe condition code was provided for these failures, and rejected output is not persisted. The Agent's self-diagnosis is not evidence of which condition occurred.

## Small correction

Only the conversational prompt, schema/adapter and validator changed. Core JSON still requires `version="pokelab-conversation-answer-v1"` and 1–10 paragraphs with nonblank text of at most 2000 characters. `fact_ids` and each paragraph's `evidence` are optional arrays of IDs. The provider is asked for up to twelve exact IDs; receiving imperfect optional metadata no longer controls answer visibility.

Missing annotations default to empty. Null, string/object/scalar containers become empty rather than being guessed/coerced into citations. Within arrays, non-string, blank/overlong and duplicate entries are ignored. Only exact IDs present in the supplied envelope survive, capped at twelve resolved references per array. Valid mixed-in IDs remain inspectable. No unknown reference is promoted into a fact, and source IDs are not translated into evidence IDs. Prose is not rewritten when annotations are removed. Facts remain projections of server-owned evidence, never provider-authored payloads.

No UI rewrite is needed: the API still returns normalized `paragraphs[*].evidence` arrays and source-owned `facts`. The renderer already supports empty arrays and still exposes the full snapshot underneath. No repair inference, retry, fallback or new transport behavior was introduced.

## Content and strict boundaries

The existing independent empirical check still withholds recognizable unsupported tournament-statistic/result paragraphs and adds a qualification; tests now exercise this with malformed/unresolved annotations too. The initial conversational implementation did not independently detect invented identities in free prose. To satisfy the explicit identity regression without reinstating the old universal prose gate, this pass adds a narrow check for explicit named card/printed-effect assertions: named `ex` cards, explicit “The card …”/“A card called …” introductions, and named subjects claiming an Ability/attack must resolve against supplied card/component names. Known names and ordinary/hypothetical strategic reasoning remain accepted. This is a bounded guard, **not comprehensive entity recognition or semantic entailment**.

Malformed JSON, wrong/missing core version/paragraph/text structure, empty prose, extra generated factual fields, output-budget violations, recognized invented-card fact assertions, source/internal errors, quarantine failures, unsuccessful provider completion and truncation still prevent a completed answer. An unsupported empirical paragraph remains withheld even when its annotations are ignored. Optional annotation removal does not grant factual authority to the remaining prose; exact-fact injection and existing authority instructions remain unchanged.

Strict research Answer/Statement fields, citation membership, minimum evidence requirements and grounding are untouched. Direct tests show null, empty, unknown and object-shaped citations still fail closed in strict research. The final gate also covers production strict selected-card, deck and card-pool paths.

## Verification

- Focused conversation tests: **43 passed** (13.79 seconds).
- One final network-blocked gate: **268 passed** (48.54 seconds), including **44 conversational cases** after adding the Gemini schema/wiring regression. Two existing dependency deprecation warnings only.
- Gate modules: conversation, selected-card service/contract, deck research service, strict card-pool answer/service, numeric interpretation.
- Required first-attempt prompts covered with missing annotations: damage-counter flexibility, self-mill, Pokémon Tool disruption. Tests use local fixtures and fake transports, asserting one call and a visible answer; this proves wiring, not live model quality.
- Mixed valid/invalid/duplicate annotations preserve valid IDs; malformed annotations do not change prose. Invented-card facts are rejected, empirical claims qualified, failed answers excluded from history, and secret/truncation/internal-error tests remain passing.
- Gemini mock verifies the actual outgoing response schema makes only core fields required and accepts a completed answer without annotations in one request.
- `git diff --check` passed. No frontend changes/tests/build were needed. Retrieval, strict validators, provider transport, frozen qualification records and fixtures have no diff from the starting SHA.

Changed files: `src/pokelab/agent_conversation.py`, `tests/test_agent_conversation.py`, this report. Ending SHA is the commit containing these changes and is supplied in the PM closeout.

**READY FOR PM LIVE QA.** Restart using the existing Phase 7C.4 launcher/configuration and try each critical question once. No live provider or external-network calls, merge, tag, certification, persistent memory or retrieval retuning occurred during this pass.
