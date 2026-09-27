# Phase 7C.1 — selected-card research in the active deck

Implementation for PM QA, **not certified**. Base:
`665cf76e56e16d6d08b79f8a19eaf33a03942773`.
Branch: `phase7c1-selected-card-research`.

## Product boundary

Selected printing + natural-language question + acknowledged active-deck revision
→ deterministic read-only snapshot → versioned compact evidence → explicitly
configured Phase 7B transport → validated answer → existing Agent panel.

Provider and model are explicit environment configuration. No preferred model is
hardcoded into product research. No routing, fallback, retry, memory, writes,
replacement recommendations, whole-deck composite comparison, new qualification,
web retrieval or Phase 7C.2 work. Prior answers never enter a request.

The certified 7A builder/models/snapshot adapters and the 7B provider transport,
qualification code/configuration and qualification records are unchanged.
The legacy native desktop Agent is not involved.

## API contract

`GET /api/v1/agent/status` returns version `pokelab-research-v1`, scope,
availability/reason, explicitly configured provider/model, `read_only=true` and
`max_output_tokens=4096`. It does not return credentials or environment contents.

`POST /api/v1/agent/research` accepts JSON:

```json
{
  "scope": "selected_card_research",
  "question": "What role could this card play in my deck?",
  "printing": "an-existing-printing-id",
  "variant": "normal",
  "revision": 118,
  "window": "30"
}
```

`variant` is optional. Window is `7`, `30`, `90` or `format`. Revision is the
currently acknowledged workspace revision, not the example value above.
Question length is 1–2000 characters; body limit is 8192 UTF-8 bytes. Unknown
fields, arbitrary provider selections, client deck contents, paths and URLs are
not accepted. Invalid requests return bounded errors without echoing input.
Cross-host browser origins and non-JSON POSTs are rejected. Run locally on
loopback with one API worker, as in the existing QA launcher.

The server resolves card, functional identity, ownership and deck contents. The
selected functional card must be in the active deck; presentation printing/finish
does not change allocations or identity. Dirty drafts are valid context.

Response fields:

- `status`, optional bounded `reason`, and `answer` (null on failure).
- `envelope` when retrieval completed: immutable 7A packet and deck supplement.
- `execution` when transport returned: configured provider/model, safe finish
  reason, latency, input/output/reasoning counts, estimated/reported cost when
  available. No raw provider body, exception text or arbitrary diagnostics.

Answer version is `pokelab-research-answer-v1`, with `outcome`, `facts`,
`interpretation` and `limitations`. Each factual/interpretive statement has text
and one or more existing evidence IDs. Unsupported questions cannot carry claims.
Structural/citation validation does **not** prove semantic entailment. PM QA must
review grounding and the distinction between plausible interpretation and intent.

## Evidence and budgets

The 7A builder runs unchanged with a 16,384-byte packet budget. Its optional
evidence omission behavior remains intact. Product research composes that packet
with a typed active-deck supplement inside a 24,576-byte total envelope; system
instructions plus envelope remain below the transport's 32,768-byte input cap.

Both are retrieved through the same read-only SQLite snapshots. The supplement
contains the complete functional count vector, deck revision/name/dirty flag and
document hash. Representative printings are chosen by sorted existing allocation
ID, not by changing allocations or preferences. Entries carry TCGdex source,
checked time and source-card hash.

Optional partner text: intersect the packet's associated-card IDs with the active
deck, exclude the selected functional card, sort by deck identity, take at most
three. Include printed category/types/stage/abilities/attacks/effect/energy type
when available. Association remains observational, not proof of synergy.
Partner text is dropped first if necessary; the complete count vector is never
silently truncated. If the envelope still exceeds its budget, stop before calling
the provider. Explicit omission records remain visible.

Envelope content hash covers the version, original packet, supplement and
omissions, excluding only its own hash. Packet/input/qualification-suite hashes
and all historical qualification records remain independent and unchanged.

The UI can inspect packet evidence, deck supplement, source references, dates,
population denominators, coverage limitations and the envelope hash. Only
server-supplied allowlisted source URLs become clickable links. Model text is
rendered as text, never HTML or executable links.

## Request lifecycle and failure states

A process-wide nonblocking single-flight lock spans retrieval, provider execution
and assessment. Requests are not queued for later inference. SQLite snapshots
close before transport. A 95-second API response deadline and 105-second client
deadline bound waiting; the certified transport retains its 90-second per-operation
timeout and byte/token caps. A response deadline does not forcibly terminate the
underlying synchronous transport: its worker retains the lock until it exits.
No second provider request can overlap it in this API process.

The unchanged transport's log quarantine remains inside this single-flight path.
Use one API worker for this controlled slice; multi-process hosting is not an
implemented concurrency policy. A separately launched benchmark is not coordinated
with this product process and should not be run during controlled Research QA.

Explicit states include busy, unavailable, context changed/unavailable, selected
card not in deck, inconsistent snapshot, evidence budget exceeded, provider
failure, request timeout, invalid answer contract, internal processing/assessment
failure, insufficient evidence and unsupported question. `length`/`max_tokens`
produce `output_token_limit_reached` with no partial answer. A normal completion
reason is required. Internal assessment errors never produce model-quality grades.

The panel keeps submitted context with its answer, warns when current context
changes, disables Ask during pending deck saves/inference, and does not regenerate
on navigation. Selecting a card opens the existing panel. Below 1200px it becomes
a readable drawer. No hover targets or collection/deck controls were changed.

## Configuration — only after PM authorizes live QA

Keep keys in the existing environment only. Never paste keys into the question,
source files, shell scripts, reports or Git. No browser credential UI was added.

Required common variables:

- `POKELAB_RESEARCH_PROVIDER`: an explicit provider ID supported by Phase 7B.
- `POKELAB_RESEARCH_MODEL`: an explicit model ID.
- `POKELAB_RESEARCH_ENABLED=PM_APPROVED_ZERO_COST`: product opt-in.
- `POKELAB_7B_LIVE_AUTHORIZATION=PM_APPROVED_ZERO_COST`: unchanged transport gate.

For OpenRouter: existing `POKELAB_OPENROUTER_API_KEY`; explicit
`organization/model:free` only. Transport enforces zero prompt/completion/request
prices and disables fallbacks. For Gemini: existing `POKELAB_GEMINI_API_KEY`,
`POKELAB_GEMINI_FREE_TIER_CONFIRMED=NO_BILLING`, and the transport's permitted
`gemini-3.5-flash-lite` ID. For Ollama: `POKELAB_OLLAMA_LOCAL_CONFIRMED=LOCAL_ONLY`
and an explicit local model, with the fixed loopback endpoint. Paid providers
remain disabled by the certified transport. Missing configuration disables Ask.

No live provider call was made during implementation. Enabling configuration is
not itself a call; pressing Ask is. Authorize provider/model and one submission
before live QA. Do not submit again on a failure without further PM approval.

## PM manual QA

1. Use this branch's checkout and confirm its commit with `git rev-parse HEAD`.
2. In the PowerShell session containing the chosen environment configuration,
   start the existing guarded launcher from this checkout:

   ```powershell
   .\scripts\Start-Phase5-QA.ps1 -Action Restart -PhaseLabel 'Phase 7C.1'
   ```

   It uses canonical read-only card/competitive data and the existing isolated,
   persistent QA deck/collection files. It launches this checkout's code. No
   credential values are logged. It defaults to API 8003 and UI 5175.
3. Open `http://127.0.0.1:5175/deck-builder`, hard-refresh, and compare
   `/api/v1/deck-workspace` `runtime_revision` with the checked-out commit.
4. Without enabling Research, open Card Detail and click **Ask about this card**.
   Confirm context, disabled state and absence of any inference request.
5. For an authorized live submission, use an existing QA deck containing Budew
   (or another card). Select its Card Detail and click **Ask about this card**.
   Check selected printing/finish, active deck and competitive window. Wait for
   any pending edits to finish. Ask “What's the point of running Budew in this
   deck?” exactly once, only if Budew is the selected card.
6. Inspect facts, plausible interpretation, limitations and evidence links.
   Check printed effects, actual deck quantities, ownership, population/window
   labels and rules boundaries. Reject unsupported creator-intent claims.
7. Navigate away and back or edit the deck after completion. The answer must
   retain its original snapshot label and show a changed-context warning when
   applicable. It must not trigger another inference automatically.
8. Verify gallery/list/detail, exact-printing controls and artwork-only competitive
   hover still work. Research itself must not change deck/ownership/preferences.
9. Check the panel at 1440px and 900px. Close the narrow drawer to access the deck
   behind it. No additional model submissions are needed for layout QA.
10. Disable `POKELAB_RESEARCH_ENABLED` and restart the QA server after the authorized
    live check. Record the observed result for PM review; do not certify here.

## Deterministic verification

Network-blocked tests cover multiple unrelated Pokémon/Energy fixtures, a reviewed
Trainer, neutral provider mocks, shared read-only snapshots, functional identity,
revision protection, complete count vectors, budget rejection, changed snapshots,
normal completion/truncation, unknown citations, invalid contracts, internal
assessment exceptions, secret quarantine, default-disabled configuration, origin
checks and timeout/single-flight behavior.

Frontend tests cover pending deck saves, acknowledged revision submission,
duplicate clicks and failure states. Browser tests use the real local API/evidence
path plus `httpx.MockTransport`, never a live model. The acceptance server's fake
transport is test-only; production has no canned-answer configuration switch.

Frozen qualification/hash assertions run with the certified 7A/7B regression
tests. Existing qualification artifacts are additionally compared against the
certified base. No certification, merge, tag or Phase 7C.2 implementation occurs.

Verified September 26, 2026:

- 436 backend tests passed with external socket connections blocked (Agent
  research/context/qualification, web API, collection, deck/allocations,
  research/copy, competitive and rules foundation/cost/modifier regressions).
- 76 frontend tests passed, including six new Research panel tests; the six
  focused tests passed again after the final context-label adjustment.
- Three real-browser checks passed with fake transport: 1440px and 900px
  context/answer/citation/read-only/stale-state checks, and truncation/provider
  failure checks. Both panel screenshots were inspected.
- TypeScript and production build passed.
- Two existing Starlette/AnyIO dependency deprecation warnings remain.
- Zero live model calls. A single separately authorized real Research request is
  recommended to assess natural-answer quality and the full live provider path;
  the deterministic tests establish wiring, not model reasoning quality.
