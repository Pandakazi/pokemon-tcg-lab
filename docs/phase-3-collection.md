# Phase 3 — Collection & Variations

Phase 2 is PM-certified at `df02a1d`. Phase 3 extends the same React/FastAPI/Python
architecture. No Phase 4 functionality is included. Repository identity and the
`pre-web-pivot-2026-09-24` tag are preserved.

## Ownership and identity

- **Exact printing + variant** is the persisted quantity key. The engine's existing
  `collection(printing_id, variant, quantity)` schema, validation and upsert behavior
  are reused. The shared helpers also serve the preserved Qt engine.
- **Canonical functional identity** is unchanged: identical gameplay signatures
  group printings; same name alone does not imply equivalence. Card Detail's
  Variations and functional total use this identity across all recognized printings,
  not only currently source-marked Standard printings.
- **Library identity** normally matches canonical functional identity. Basic Energy
  retains the curated type grouping. PM explicitly approved rolling up all exact
  variations of a Basic Energy type for Library ownership and its artwork picker,
  while Card Detail Variations remains strictly canonical.
- A quantity is an integer from 0 to 9999 per exact variation. Zero is logically
  unowned and disappears from Collection. Increment/decrement updates run in an
  immediate SQLite transaction; concurrent increments cannot overwrite each other.
  Decrement at zero is a no-op, never a decrement of a different variation.
- Variant choices reuse source `variants` flags and saved legacy variant names.
  Internal `unspecified` ownership is never labeled as a collectible finish. When
  explicit finishes exist, it is excluded from variation/artwork choices. Existing
  owned copies remain editable under **Copies with no recorded finish**, separately
  from the artwork grid, and **Finish not recorded** in Collection/Detail. No records
  are deleted or silently reassigned. Without explicit finish data, one printing
  entry remains with that honest label. Source images may be shared across finishes.

Gallery's number is the Library group's total. Its +/− modifies only the displayed
printing/finish. Minus is disabled when that exact variation is zero, even when the
group total is positive. Library All/Owned/Unowned applies to that same group total
and combines with all existing filters before pagination.

## Storage and migration

Card-cache connections remain read-only. Web quantities and artwork preferences
are stored in **`data/user-state.sqlite3`** by default, next to `cards.sqlite3`.
A custom card-cache path uses `user-state.sqlite3` in that cache's directory unless
`POKELAB_USER_DB_PATH` is set. User-state and card-cache paths must be different.

The first use initializes user-state schema version 1 in a transaction. If the
card cache has the older Qt `collection` table, its rows are copied once with
`INSERT OR IGNORE`; existing target quantities win. The source database is never
modified or deleted. The schema version records successful initialization, so later
restarts cannot re-import ownership that the player removed. Unsupported versions
fail safely rather than recreating the database. Migration creates only collection
and Library-preference tables, not accounts or new card-source tables.

The inspected PM cache had no legacy collection table. For installations that do,
stop Qt before the first web launch. The frozen Qt client continues using its legacy
storage; later Qt edits do not synchronize into web state. Use the web client for
ongoing ownership. Back up `user-state.sqlite3` with the API stopped. Do not delete
this file to refresh cards: it contains the user's quantities and artwork choices.
All databases and personal state remain excluded from Git and source ZIPs.

## Library artwork and navigation

Use **Choose artwork / finish** on a Library card to select a printing and finish.
The choice is saved independently of ownership and survives browser/API restarts.
It applies while that printing and variant still exist and belong to the group;
invalid references fall back to Phase 2 representative selection.

The Library result pool remains based on matching Standard-legal printings.
The chosen presentation printing can be historical; its displayed exact identity,
text and source legality remain truthful. Choosing older artwork does not assert
that that exact printing is source-marked Standard. Automatic Basic Energy selection
still prefers the newest eligible image-bearing representative when no preference
overrides it. Ambiguous source Normal Energy is not reclassified.

Card Detail links use `/cards/<printing-id>?variant=<variant>`. Direct URLs without
a variant use a meaningful available finish (Normal first), unless that printing
has existing unassigned copies to show. Explicit legacy URLs still address those
exact underlying records. Inspecting or owning another
variation on Card Detail never changes the saved Library artwork. Back to library
retains the originating Library or Collection query. Category-specific Library
search/filter/page memory, Gallery/List and browser history remain intact.

Collection is an exact-variation workspace across all formats, with category/name
search, quantities, Gallery/List, detail links and pagination. It is not another
functional representative list. Missing cache records keep their stored ownership
but cannot be rendered until those records are available again.

## Card Detail artwork

Variations is collapsible and uses a four-column desktop mini-gallery with vertical
scrolling and bounded server pagination. Primary and variation artwork are capped
at the same normal 250 px image width (276 px framed component); wide columns do
not stretch them. Selecting another variation cannot change these dimensions.
Owned and unowned artwork use identical
color/opacity; quantities and Owned/Not owned labels communicate ownership.

Mouse hover enlarges the embedded artwork itself by 50 px in width, toward the
right/down with preserved aspect ratio, above adjacent content. Its fixed layout
box does not grow; pointer exit restores the image immediately. There is no detached
preview. **Enlarge artwork**, centered inside the frame, opens a keyboard/touch-accessible dialog; Escape or
Close dismisses it. Image magnification is isolated to Card Detail. Library hover
has no competitive tooltip and no magnification. No analytics or deck-printing star
control is implemented. The card-text view remains available independently of art.
Primary ownership controls are centered below the complete frame. Collection List
metadata and ownership controls occupy one row above that row's bottom separator.

## API contracts

- `GET /api/v1/cards`: existing filters plus `ownership=all|owned|unowned` (default
  all). Summaries add `ownership`: exact `variant`/`quantity`, `functional_id`,
  `library_id`, `functional_total`, and `library_total`. Saved artwork is applied
  after server selection of matching Library groups.
- `GET /api/v1/cards/{id}`: existing exact metadata; optional `variant` selects the
  quantity to show. Card images remain opt-in on existing card endpoints.
- `GET /api/v1/cards/{id}/ownership?variant=normal`: read one exact variation and
  its canonical/Library totals.
- `PUT /api/v1/collection/{id}`: JSON `{ "variant": "normal", "quantity": 2 }`
  or `{ "variant": "normal", "delta": 1 }`. Exactly one operation, delta ±1;
  booleans, fractions, negative quantities and unknown variants are rejected.
- `GET /api/v1/cards/{id}/variations`: canonical group by default; `scope=library`
  is used only by the Library artwork picker. Includes recognized finishes,
  exact ownership and image URLs. `page` 1–10000 and `page_size` 1–50, default 24.
  When relevant, `unassigned` separately carries owned copies without recorded
  finishes for printings on the current page; these do not inflate finish counts.
- `GET /api/v1/library/{id}/preference`: resolved printing/variant choice.
- `PUT /api/v1/library/{id}/preference`: JSON `{ "printing_id": "...",
  "variant": "normal" }`; target must belong to the same Library group.
- `GET /api/v1/collection`: positive exact-variation quantities; optional category,
  case-insensitive `q`, and bounded page/page_size.

Invalid IDs/values return 422; missing exact IDs return 404; unavailable cache or
user-state storage returns 503. API contracts expose no arbitrary SQL or database
mutation. Browsing never initiates synchronization or upstream card-data calls.
This remains a loopback-only, local single-user application, without authentication.

## PM launch and acceptance

Stop the existing API with Ctrl+C, then in PowerShell window 1:

```powershell
cd C:\Users\Mike\Documents\pokemon-tcg-lab
.\.venv\Scripts\python.exe -m uvicorn pokelab.api:app --host 127.0.0.1 --port 8001
```

In PowerShell window 2 (or retain the existing Vite process):

```powershell
cd C:\Users\Mike\Documents\pokemon-tcg-lab\web
npm.cmd run dev
```

Open http://127.0.0.1:5173. No new dependencies or card synchronization are required.
State initializes safely on first use. On macOS use `.venv/bin/python` and `npm`;
macOS/mobile certification is not claimed.

1. Browse/search/filter Library, then press + on one card twice. Group total rises
   twice; the exact displayed variation quantity also rises twice.
2. Open Card Detail. Check the exact quantity and functional total. Use Tab/Enter
   on +/−. Decrement to zero; another variation's quantity must not change.
3. Expand Variations. Browse four-across full-color artwork, including unowned
   entries, and use the variation-page controls if needed.
4. Add another printing/finish. Functional total updates. Inspect its artwork by
   mouse and keyboard; exact URL, primary image, finish and metadata update.
5. Hover primary and variation art. Check in-place +50 px enlargement without page
   reflow; verify normal dimensions after pointer exit and variation changes. On a
   large viewport, artwork stays card-sized in all four columns. Use Enlarge artwork
   and Escape. Quantities, variation clicks and scrolling remain usable.
6. Return to Library and verify prior category/search/filters/page. Owned includes
   the card even when copies belong to a different displayed printing; Unowned
   excludes it. Combine Owned with Basic, Ability Yes and Psychic/Dragon.
7. Choose artwork / finish from Library. Pick a zero-owned variation: total stays,
   minus is disabled, and + modifies that exact variation only.
8. Restart the API, reload/reopen the browser and return to the query. Ownership
   and chosen artwork persist. Inspect a different Card Detail variation and return:
   the saved Library artwork must not change.
9. Open Collection. Verify distinct owned exact finishes, quantities, category and
   search, Gallery/List, pagination and exact detail links. Remove the last copy of
   a variation; it is no longer owned and disappears from this workspace.
10. Recheck Basic Energy: eight current recognized type representatives, image
    preference/fallback intact unless deliberately overridden by a saved preference.

## Mandatory QA scope matrix

### 🟢 WIRED — expected to work

- Header Library/Collection navigation; retained Library query on return.
- Pokémon/Trainer/Energy tabs, per-category query memory, search/Clear search.
- All/Owned/Unowned; existing type, stage, Ability Yes/No, regulation, Trainer and
  Energy filters; Clear filters and filter-panel toggle; shareable query/history.
- Library Gallery/List, Previous/Next, cumulative progress, exact card links.
- Library +/− and total, exact variation label; Choose artwork / finish dialog,
  selectable artwork/finish, paginated choices, persisted preference and Close.
- Card Detail exact metadata/quantity +/−, functional total, Back to library.
- Variations collapse/expand, four-column scrollable gallery, previous/next variation
  pages, exact artwork links, quantity controls, full-color Owned/Not owned labels.
- Separate unassigned ownership presentation: editable existing copies, not extra finishes.
- Card Detail framed artwork, centered controls, in-place hover enlargement,
  Enlarge artwork dialog, Close/Escape and keyboard.
- Collection exact owned entries, category/search, Gallery/List, quantities and pages.
- Retry/error messages, card image fallbacks, source/legality labels.
- Agent panel collapse/expand (layout only).

### 🟡 PARTIAL — only this portion works

- Research: deterministic card data and variations, not deep Research Mode.
- Source variants/art: only supplied flags plus saved legacy names; finishes may
  share source artwork. Source legality/classification retains its known limitations.
- Responsive layout and touch enlargement fallback exist; no mobile certification.

### ⚪ NOT WIRED — intentionally inactive or absent

- Header Analytics (disabled), competitive hover, timeframe/archetypes/decklists.
- Agent chat/providers, AI calls, Preferred Deck Printing/star, pricing/master sets,
  scanning, acquisition history, imports, auth/cloud sync/billing/PWA.
- Conditions filter: future approved order is **Stage → Ability → Conditions →
  Regulation Mark**. No Conditions control until product defines the matching rule.

### 🧊 FROZEN — outside Phase 3 UI QA

- Qt reference UI/packaging and its known EXE startup failure.
- Optional MCP interface, preserved with full regression coverage.

## Validation

135 Python tests, 31 frontend tests, eight real-data browser tests, TypeScript and
production build passed. See [TEST-RESULTS.md](../TEST-RESULTS.md). Browser tests use
ports 8002/5174, temporary isolated ownership storage and blocked backend external
connections. They do not write to PM's real collection. Existing Phase 2 regression
coverage is retained. PM accepted Phase 3 functionality; these final cleanup items
await PM visual certification. No Phase 4 work is enabled.
