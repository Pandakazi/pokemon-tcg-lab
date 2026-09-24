# Phase 2 — Library & Browsing

Phase 1 was manually certified by PM. Phase 2 extends that same architecture;
its new behavior is ready for PM QA after automated validation, not automatically
PM-certified. No Phase 3 collection work is included.

## Behavior and API

The library remains Standard-only, using dated TCGdex source legality flags. Browse
Pokémon, Trainers or Energy. Trainer Item/Supporter/Stadium/Tool remain subtypes,
not top-level tabs. Basic Energy is the display label for source classification
`Normal`; `Special` is Special Energy. The API supplies available filter choices.

`GET /api/v1/cards` retains Phase 1 defaults and adds:

- `category=Pokemon|Trainer|Energy` (default Pokemon)
- `q`: case-insensitive name substring or exact ID, up to 100 characters
- repeated `pokemon_types`, `stages`, `trainer_types`, `energy_types`, `regulation_marks`
- `page` 1–10000, `page_size` 1–50 (UI uses 24), `include_image` false by default

One family combines values with OR; different families combine with AND. Example:
`/api/v1/cards?category=Pokemon&pokemon_types=Psychic&pokemon_types=Dragon&stages=Basic`.
Stage values are `Basic`, `Stage1`, `Stage2`. Filters incompatible with the selected
category are rejected, as are unknown parameters/invalid values. Category changes
clear filter selections and reset pagination while preserving the name search.
Search/filter changes reset the page. Clear filters retains category and search;
Clear search retains category and filters.

The response remains compact and includes `filter_options` and per-printing source
provenance. React displays results; it does not classify/filter the card corpus.
Multiple Pokémon types remain arrays and display together.

`GET /api/v1/cards/{printing_id}` retrieves one exact printing, with structured
abilities, attacks/costs/damage/text, Trainer/Energy text, metadata and provenance.
Images remain opt-in via `include_image=true`. Missing printing: 404; malformed
ID/query: 422; missing/empty/corrupt/unsupported database: 503. Requests/responses
use Pydantic models. `/api/v1/status` remains available. The detail endpoint may
resolve a non-Standard printing by direct exact ID, and displays its actual flags.

All routes use read-only SQLite connections: no database creation, synchronization,
collection mutation, or upstream card API calls. Source records remain preserved;
this phase adds SQL filter clauses to the existing card service, not a new engine.

## URLs and presentation

Library state is represented in ordinary query parameters, for example:
`/?category=Trainer&q=Boss&trainer_types=Supporter`.
Refresh and browser Back/Forward restore the query. Cards link to
`/cards/<URL-encoded-exact-printing-ID>`; distinct printings have distinct URLs.
A direct URL loads without first visiting the library.

Gallery and List share the same server result page. Switching view does not fetch
again or reset category/search/filters/page. View mode is local React presentation
state and persists through detail navigation; a full browser refresh defaults to
Gallery. Filter-panel open/closed state is also local, not cross-device persistence.

Cards use keyboard-focusable links (Enter opens them; ordinary browser link
behavior supports touch and new tabs). Detail focuses the card heading after load.
Detail's Back to library link preserves the originating query when available;
a direct deep link falls back to the default library. Browser Back/Forward works.

## PM launch instructions

If the Phase 1 API is still running, stop it with Ctrl+C and restart: its process
must import the new routes. No database re-sync is required for this phase.

PowerShell window 1, repository root:

```powershell
cd C:\Users\Mike\Documents\pokemon-tcg-lab
.\.venv\Scripts\python.exe -m pip install -e ".[web,dev]"
.\.venv\Scripts\python.exe -m uvicorn pokelab.api:app --host 127.0.0.1 --port 8001
```

PowerShell window 2 (stop the previous Vite process first):

```powershell
cd C:\Users\Mike\Documents\pokemon-tcg-lab\web
npm.cmd ci
npm.cmd run dev
```

Open http://127.0.0.1:5173. Both processes stop with Ctrl+C. First-time clone/cache
initialization and macOS equivalents remain in the README. On macOS use
`.venv/bin/python`, `npm`, and `npx`; Windows is the exercised platform.

## PM acceptance walkthrough

1. Browse Pokémon, then Trainers; search `Boss`. Results must be Trainer printings.
2. Select Supporter. Clear search, switch to Energy, and select Special Energy.
3. Switch to Pokémon; select Psychic and Dragon, then Basic. Every result must be
   Basic and have at least one selected type. No ownership filter participates.
4. Search `a`, go to page 2, then toggle Gallery/List. Query/page/results must stay.
5. Open a card by mouse, then repeat using Tab and Enter. Check its exact printing
   URL, set/number, types/classification, card text and dated legality.
6. Use browser Back; search/filter/page and current view must return. Use Forward,
   refresh the detail URL, and try Back to library.
7. Refresh a filtered library URL. Query selections must return; Gallery is the
   expected refresh default. Copy/paste a detail URL into a fresh tab.
8. Open `/cards/nonexistent-999`: expect a useful not-found state and library link.
   Invalid query values must show a validation error with Reset library query.
9. Stop the API to check connection errors/Retry; restart to recover. Uncached
   images may show a fallback offline, while local card text remains available.

## Mandatory QA scope matrix

### 🟢 WIRED — must work

- Header Library button: navigate to library (origin query retained from detail).
- Pokémon / Trainers / Energy tabs: real category selection.
- Search field and Clear search button: server query, category/filter combination.
- Filter-panel toggle: expand/collapse; Clear filters: reset active filter families.
- Pokémon type checkboxes: multi-select, including multi-type card matches.
- Stage checkboxes and regulation-mark checkboxes: source-backed selections.
- Trainer subtype checkboxes: Item, Supporter, Stadium, Tool where present.
- Energy classification checkboxes: Basic/Normal and Special where present.
- Gallery/List buttons: same results and page, different presentation.
- Previous/Next: bounded server pagination preserving query.
- Gallery cards and list rows: mouse/touch/keyboard links to exact printing pages.
- Back to library link, browser Back/Forward, and direct card URLs.
- Retry and Reset library query links/buttons in error states.
- Card images/fallbacks, identifying text, result count, sync/provenance labels:
  real read-only information; no sync action is attached to the label.
- Agent panel collapse/expand button: layout only.

### 🟡 PARTIAL — exercise only the stated portion

- Card Detail / Research foundation: deterministic card information is wired;
  deep Research Mode, Competitive, Decks, associated-card and Agent sections are
  not implemented. Missing source fields remain absent/explicitly unavailable.
- All scope: the fixed active scope. Owned/Unowned selection is not connected.
- Narrow/mobile layout: basic usable layout, not mobile-certified this phase.

### ⚪ NOT WIRED — intentional, do not test as working features

- Header Collection and Analytics buttons (disabled).
- Owned and Unowned buttons (disabled); quantities/ownership are not shown.
- Agent workspace text: no chat, recommendations, provider settings or calls.
- No hover analytics, timeframe control, archetype links, decklist drilldown,
  prices, popularity, synergy scores, authentication, billing or PWA controls.
  These later-phase controls are absent rather than populated with mock results.

### 🧊 FROZEN — not part of Phase 2 UI certification

- Qt client and packaging, including its previously recorded EXE DLL failure.
- Existing MCP interface: preserved optional integration with regression coverage.

## Limits and follow-up gates

Standard legality is source-reported and dated. Missing metadata is not inferred.
The source may classify historical/promotional records imperfectly; no AI corrects it.
Image loading requires the asset host; card text/filtering uses SQLite. No entire
image library or card corpus is loaded into the browser. No collection, analytics,
Agent, auth, hosting, offline/PWA or Phase 3 work is enabled.

The only additional frontend runtime dependency is React Router for normal URLs.
Browser tests use isolated ports 5174/8002 so PM's 5173/8001 servers stay undisturbed.
Backend external connections remain blocked during integration tests. No approved
architecture change was needed.

## Engineering validation

109 Python tests, 14 frontend tests and all 3 real-data Chromium tests passed.
TypeScript and production build passed. All 23,736 cached records validated against
the detail response model. The rendered filtered list/detail were inspected.
The stale-query link and deferred-navigation timing defects found during browser
QA were fixed and tested. Two upstream Python test-client deprecation warnings remain.
The earlier auto-review usage-limit interruption is resolved; no validation remains
blocked. Phase 2 is ready for PM certification, not a claim of completed PM QA.
