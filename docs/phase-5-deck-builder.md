# Phase 5 — Deck Builder

Implementation for PM QA; **not certified**. Mike performs final manual QA and
explicitly approves the phase. Foundation: `22a229b`, the commit referenced by
`phase-4-certified-2026-09-24`. Earlier Phase 4 prose predates that certification.
The supplied implementation handoff is preserved in `phase-5-handoff.txt`.

## Behavior

Deck Builder is beside Analytics. Home is the application's existing `/` Library
landing route; the logo navigates there without preserving an old query. The
Library tab continues to restore its last query. Analytics' existing disabled
top-level tab is unchanged; actual competitive research remains in Card Detail.

`/deck-builder` composes the existing Library. Contextual detail uses
`/deck-builder/cards/:printingId?variant=...`. All quantity controls in that
context, including variation and unassigned-finish rows, modify the deck only.
Normal Library/Collection/Card Detail retain certified collection editing.
Ownership is static context, never a legality check or quantity constraint.

The active tray remains visible through browsing, detail and the existing full
research dashboard. Tray names reopen inspection. Category query memory,
search/filters, pagination, gallery/list, filter visibility and per-query scroll
position survive detail/research navigation. Builder and ordinary Library have
separate UI memory. The Agent is available as a collapsible rail, initially
collapsed in Builder to preserve card-reading space; it has no connected model.

PM QA fix pass #1 uses artwork-only competitive hover with a 500ms delay and the
existing 180ms crossing grace. Builder popups show the live functional deck count
in bold; ordinary Library popups have no deck count. Card Detail remains click to
enlarge with no competitive hover. All metrics/timeframes, source/exclusion states,
artwork enlargement and existing Variations placement are reused. No new analytics
calculation, browser, AI feature, export, theme or drag-and-drop was introduced.

## Identity and validation

`pokelab.decks.deck_identity` uses the existing canonical functional ID except for
curated Basic Energy recognized by `library_signature`. That exact recognition
rule is reused, with explicit `deck-basic-energy:<type>` keys. It does not change
Library grouping, canonical signatures, collection IDs or source records.
Special and ambiguous Energy retain canonical identity. Ambiguous source `Normal`
Energy is adapted to restricted Energy **only in the validation provider**, so it
cannot obtain the unlimited Basic Energy exemption accidentally.

Entries persist identity + aggregate quantity and exact allocations, each containing
printing ID, finish and quantity. Positive allocation quantities must sum to the
functional quantity. Variation controls edit only their exact allocation, with a
read-only functional total; Gallery/List, primary Detail and tray controls retain
aggregate behavior. The tray lists allocations beneath the grouped functional card.
Functional identity is not the same as the rule's name-based
copy-limit grouping: distinct gameplay entries with the same name still contribute
to the existing Python validator's name limit.

`DeckProvider` resolves an entry independently of its presentation. A source-marked
Standard-legal equivalent can establish legality for historical artwork. It never
assumes new equivalence beyond certified signatures/curated Basic Energy. Missing
functional entries remain stored and generate unknown-evidence reasons. Missing
allocations are labeled unavailable and remain stored; they are not silently reassigned.

User-level Default Printing is stored separately from deck composition and collection
ownership, keyed by deck identity (Basic Energy type included). Implicit additions
use an available default; explicit Variation additions always use that variation.
An exact Variation + also remembers its printing/finish as the default, atomically
with the addition. Decrements and implicit additions do not replace that preference.
There is no separate default button/status in Variations; inspection remains read-only.
Changing defaults never rewrites existing active/saved deck allocations, ownership,
Library preferences or validation. General decrement removes from the default/current
printing if allocated, otherwise the last remaining allocation; exact decrement never
steals from another allocation. An unavailable default remains remembered, while an
implicit add falls back to the available displayed printing/finish.

Builder variation tiles own their persistent frame class directly. Compact identity,
prominent finish/ownership, and centered quantity/total groups are enclosed together.
Normal Library presentation is unchanged. The reported disappearing frame was not
reproduced; settled-state browser checks cover data load, quantity changes, reload,
navigation and API refresh. Frame/whitespace has no competitive-hover handlers.

The authoritative `tcg_lab.service.Lab.validate` is reused. Its new keyword-only
`require_complete` defaults to true, preserving every legacy caller. An unsaved
partial draft omits only the under-60 failure; actual violations still win.
Empty unsaved decks receive EMPTY. Saved zero-card decks are INVALID. Saving a
partial deck is allowed and immediately changes its state to INVALID with the
remaining count. An unsaved/saved 60-card deck passing supported checks is VALID.
Unknown evidence receives INVALID plus “Legality needs verification”; it never
produces a false VALID claim. Collection shortages do not enter validation.

Supported checks remain 60 cards, ordinary name-based four-copy rule, Basic
Pokémon, ACE SPEC and dated provider Standard flags. Card-specific exceptions,
historical rulings, exhaustive restrictions/bans and live tournament certification
remain outside the inherited validator. These limits are available in the tray.

## Persistence and concurrency

`GET/POST /api/v1/deck-workspace` returns schema version 2, runtime commit, workspace
revision, defaults, active deck, validation and saved-deck choices. POST requires
`schema_version: 2` and supports quantity deltas (optional `exact`), remove,
default_printing, rename, save, new and open. Request fields are bounded by
Pydantic. Server-derived identity and transactional mutations are authoritative.

Storage is a separate SQLite database, `deck-workspace.sqlite3`, beside the
configured collection database, or `POKELAB_DECK_DB_PATH`. It must not equal the
card, collection or competitive database. Schema version 2 holds one active
workspace, named saved decks and the user's `default_printings` table. Every accepted edit durably stores the active
draft. Explicit Save updates the named saved copy and sets `has_saved`; autosaving
a workspace does not do so. Drafts and named saves both survive API/browser restart.

The atomic version-1 migration archives original active and saved JSON documents in
`migration_v1_backup`, converts each old representative into one exact allocation
with the old aggregate quantity, and increments the workspace revision to invalidate
stale clients. Names, IDs, saved timestamps and dirty/saved flags remain unchanged.
It does not guess historical mixtures or seed user defaults. A failed migration
rolls back; unsupported schemas are never recreated. Stop the API and retain a full
database backup before rollout. This schema is not compatible with the previous API.

`BEGIN IMMEDIATE` plus revision checks prevents cross-window lost updates; stale
edits receive 409. The UI queues deltas using the last acknowledged revision.
It stops subsequent queued edits on any failed request and presents a reload action
to reconcile with durable state. It does not blindly retry a potentially committed
request. Pending writes trigger a browser unload warning. Reload shows the last
acknowledged/stored work; failed/abandoned queued clicks are not claimed as saved.
New/Open require explicit discard confirmation for dirty work, enforced in both
UI and API. Saved decks can be reopened and edited without becoming unsaved again.

The implementation supports one active workspace per local user database, not
accounts or simultaneous collaborative editing. Limits are 100 functional entries
and 999 copies per entry for inspectable invalid drafts. Theoretical construction
is independent of inventory.

## Files and architecture

- `src/pokelab/decks.py`: identity/rule adapter, draft and saved-deck persistence.
- `src/pokelab/api.py`, `web_models.py`: deck endpoints and server-supplied deck IDs.
- `src/tcg_lab/service.py`: backward-compatible completeness option.
- `web/src/DeckBuilder.tsx`: contextual provider, serialized writes, tray, deck
  controls and static ownership rendering.
- `App.tsx`, `Shell.tsx`: routes, navigation, shared Library/state memory and Agent.
- `CardTile.tsx`, `CardDetail.tsx`, `Variations.tsx`, `Competitive.tsx`: contextual
  reuse; normal collection and competitive calculations are unchanged.
- `api.ts`, `index.css`: deck ID contract and desktop layout.
- `tests/test_deck_builder.py`, `web/src/DeckBuilder.test.tsx`,
  `web/integration/deck-builder.spec.ts`: targeted service, UI and real-data tests.
- `scripts/Start-Phase5-QA.ps1`: isolated local manual-QA startup/restart.

## Manual QA startup / restart

From this checkout, run in PowerShell:

```powershell
.\scripts\Start-Phase5-QA.ps1 -Action Start
```

Open `http://127.0.0.1:5175/deck-builder`. The API uses port 8003; the frontend uses
5175. The launcher reuses the existing Python environment and this checkout's npm
dependencies. Its `SourceRepository` defaults to Mike's certified repository.
It reads the real card and competitive databases and snapshots collection once
into `.cache/manual-qa/user-state.sqlite3` with SQLite's backup API. Manual QA decks
persist at `.cache/manual-qa/deck-workspace.sqlite3`. Neither source database nor
the production collection is edited by these deck operations.

After any backend change:

```powershell
.\scripts\Start-Phase5-QA.ps1 -Action Restart
```

Then hard-refresh with **Ctrl+Shift+R**. Verify the checkout's commit with
`git rev-parse HEAD`, the saved PID/command paths in `.cache/manual-qa/processes.json`,
and `/api/v1/deck-workspace` returning `schema_version: 2` and matching
`runtime_revision` through port 5175. `node scripts/Verify-Phase5-QA.mjs` verifies
that runtime with a cache-bypassing browser reload and read-only smoke checks. Do not
reuse another application's 8001 API for this checkout. Startup refuses occupied
ports and only stops recorded processes whose command lines match this checkout.
Logs remain in `.cache/manual-qa`. Stop with `-Action Stop`; drafts are retained.

## QA Scope Matrix

### 🟢 WIRED — must work; failure is a bug

- Navigation: Deck Builder beside Analytics; logo Home; gallery/detail/research
  return state; contextual tray remains available.
- Deck quantities from Gallery/List, tray, detail and variations; zero removes an
  entry; queued rapid edits stay consistent; ownership read-only in all Builder views.
- New/Open/Save/Rename; durable active drafts; saved incomplete reopening; visible
  storage failures; discard guard; stale-revision conflict protection.
- Functional counts across equivalent printings; distinct gameplay entries;
  presentation persistence and grouping validation; curated Basic Energy type IDs.
- Empty/In Progress/Valid/Invalid and actionable supported-rule/unknown reasons;
  saved incomplete invalid; ownership never blocks construction.
- Artwork-only 500ms competitive hover, 180ms grace, functional Builder deck count,
  and full research with unchanged source semantics.
- Exact allocation totals and mixed-printing save/reopen/restart; default persistence
  and replacement; future implicit vs explicit additions; no retroactive deck changes.
- Real artwork, click-to-enlarge, missing-image fallback; desktop gallery and
  independently scrolling tray; card names link to inspection; keyboard controls.
- Agent rail/panel visibility and toggle; no live Agent behavior.

### 🟡 PARTIAL — only documented behavior is implemented/testable

- Standard only; format is displayed, not a selector for Expanded/Unlimited.
- Legality is the existing supported Python checks over dated source evidence,
  not comprehensive tournament certification or every card-specific exception.
- Basic Energy Builder Variations use deck-type scope. Normal Library/Detail keep
  their certified scope; each energy type and Special Energy remain distinct.
- Browse UI memory survives navigation in the current application session. Deck
  content survives full restarts; transient scroll/filter-panel/view memory is not
  serialized into the deck database. Query URLs retain their normal refresh behavior.
- Conflicting multi-window edits require reload/reconciliation, not automatic merge.
- Desktop layout; narrower widths may use existing horizontal list scrolling.

### ⚪ NOT WIRED — intentionally excluded/unavailable

- Export, drag-and-drop, themes, AI generation/optimization, simulations/self-play,
  matchups, autonomous research, accounts, mobile redesign.
- Top-level Analytics workspace remains the certified disabled navigation item;
  Phase 4 card research is fully wired. Agent has no connected provider.

### 🧊 FROZEN — previously certified behavior preserved

- Normal Library/Collection/Card Detail ownership writes and exact finish keys.
- Canonical identities, Library representative/artwork preferences and category filters.
- Card artwork enlargement, variation placement and underlying collection migration.
- Competitive ingestion, calculations, thresholds, windows, source/error semantics.
- Existing MCP and Qt callers retain complete-deck validation by default.

## Artwork investigation — QA-5.5

The exact multi-card PM incident was not reproduced. Detail loading is keyed by
printing/finish with abort handling; image URLs are derived from the exact cached
record without Gallery/List or deck-membership dependencies. A reproducible stale
failure latch existed in CardImage: after an error, changing its resource did not
reset the failure state. The image renderer is now keyed by printing ID and URL;
Detail also guards against displaying the previous route's payload. Eager detail
images try the same printing's low-resolution asset once if high resolution fails,
then retain the honest unavailable fallback. No Library refresh/toggle is involved.
The enlarged modal retains its existing direct high-resolution request.
