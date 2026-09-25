# PokéLab

PokéLab is a **web-first, PWA-capable competitive Pokémon TCG research, collection,
deckbuilding and analysis environment**, in development toward private alpha.
Phases 1–5 are PM-certified. Phase 5 Deck Builder was certified September 25, 2026,
including the accepted Variation Family correction and current finish visualization
with persistent shimmer. `phase-5-certified-2026-09-25` preserves this milestone;
cosmetic refinement remains non-blocking. See [scope, architecture and QA startup](docs/phase-5-deck-builder.md).

The approved PokéLab Web Prototype v0.1 Figma Make frontend supplies the visual
and interaction direction. We reuse its generated source, not a screenshot recreation.

## What works now

- Real TCGdex-backed Standard Pokémon, Trainer and Energy printings from local SQLite.
- Server-backed search and category-specific multi-select filters (OR within / AND across groups).
- Gallery/List views and shareable query URLs; exact-printing card-detail routes.
- Exact printing IDs, names, sets, collector numbers and dated legality provenance.
- Real, lazily loaded images; meaningful missing-image fallback.
- Pagination, loading/error states and retry; collapsible side panels.
- Normal browsing reads SQLite and never initiates TCGdex synchronization.
- Persistent exact printing/finish quantities, functional Owned/Unowned filtering,
  and independently saved Library artwork preferences.
- Card Detail variations, quantity controls and artwork magnification; an exact
  owned-printing Collection workspace.

- Main-Limitless tournament analytics: Library preview and continuous Card Detail
  research with usage, copies, archetypes, four-window trends and association/lift.
  See [Phase 4 setup, definitions and manual QA](docs/phase-4-competitive.md).

- Persistent Deck Builder with shared Library/detail/research, functional counts,
  read-only ownership context, saved drafts, and Python-backed validation.

Variation Family discovery includes supported equivalent and historical printings
without merging cards by name alone or changing deck/collection identity. Exact
Holo and Reverse Holo visualization uses distinct masks and slow staggered shimmer;
touch receives autonomous light, while reduced motion retains a static treatment.

Agent and authentication remain
disabled/unconnected. PWA installation,
offline service workers, hosting and billing are not implemented.

## Architecture

React 19 + TypeScript + Vite + Tailwind (`web/`)
→ same-origin `/api/v1` → FastAPI (`src/pokelab/api.py`)
→ existing Python card services → SQLite.

Card text is synchronized from TCGdex. Images load on demand from TCGdex assets;
no image library is bundled. Standard legality uses structured source flags and
shows source freshness; it is not guessed by AI.
Card data remains read-only during browsing and collection edits. Ownership and
artwork preferences live separately in `data/user-state.sqlite3` (override with
`POKELAB_USER_DB_PATH`). Existing Qt collection rows, when present, are copied once
by a transactional versioned migration; source records are never overwritten.
Back up the user-state file with the API stopped. See the
[Phase 3 ownership model, migration, acceptance walkthrough and QA matrix](docs/phase-3-collection.md).

Existing collection, filtering, functional/printing identities, competitive analytics
and provider-independent Agent groundwork remain in the Python engine. Analytics
uses source-isolated cached main-Limitless research for the web UI; legacy Play!
Limitless evidence remains separate. Unresolved mappings are excluded and coverage
is explicitly limited; it is not a full paper metagame census. The Agent remains
read-only and provider-independent; only its Anthropic
adapter exists today, with live-provider QA deferred.

MCP remains an optional adapter. Qt is preserved as an earlier reference prototype,
not the primary product. Its packaged EXE has a known DLL startup failure and is
not certified. See [the architecture decision](docs/adr-001-web-first.md),
[pre-pivot checkpoint](docs/pre-web-pivot.md), [Figma provenance](docs/figma-provenance.md),
[historical Qt instructions](docs/qt-prototype.md), and
[optional MCP/card-data instructions](docs/mcp-and-card-data.md).

## Local setup — Windows

Prerequisites: Python 3.11+ and Node.js 22.12+ (tested with Python 3.13.15 and Node
22.22.1). Download them from [python.org](https://www.python.org/downloads/) and
[nodejs.org](https://nodejs.org/). Open PowerShell in this repository folder.
Do not use the old Run-Local launcher for the web UI; it starts the optional MCP adapter.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[web,dev]"
cd web
npm.cmd ci
cd ..
```

An existing `.venv` may be reused; skip its creation. No API key is needed.
If this is a fresh clone/ZIP, initialize card data once:

```powershell
.\.venv\Scripts\python.exe -m tcg_lab.sync_cards
```

The initial English catalog download can take time. The existing local synchronized
`data/cards.sqlite3` can be reused without downloading it again. Refresh later with:

```powershell
.\.venv\Scripts\python.exe -m tcg_lab.sync_cards --refresh
```

Start the API from the repository root and leave this window open:

```powershell
.\.venv\Scripts\python.exe -m uvicorn pokelab.api:app --host 127.0.0.1 --port 8001
```

Open a second PowerShell window in the repository root:

```powershell
cd web
npm.cmd run dev
```

Open **http://127.0.0.1:5173**. The frontend proxies `/api` to port 8001. The optional
MCP service can continue using port 8000 independently.

## Local setup — macOS

Install Python 3.11+ and Node.js 22.12+. In Terminal at the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[web,dev]'
cd web
npm ci
cd ..
.venv/bin/python -m tcg_lab.sync_cards
.venv/bin/python -m uvicorn pokelab.api:app --host 127.0.0.1 --port 8001
```

Skip synchronization if the cache already exists. In a second Terminal, enter the
repository's `web` directory and run `npm run dev`, then open the same browser URL.
macOS instructions use standard tooling; this milestone was executed on Windows.

## Stop, restart and troubleshoot

- Stop each server with Ctrl+C in its terminal; restart with the same commands.
- Database unavailable: run synchronization from the repository root. The API uses
  `data/cards.sqlite3` by default and deliberately does not create a missing cache.
- A custom cache path can be supplied before API startup via
  `$env:TCG_CARDS_DB_PATH = 'C:\path\cards.sqlite3'` in PowerShell or
  `export TCG_CARDS_DB_PATH='/path/cards.sqlite3'` on macOS. The web API reads process
  environment variables; it does not automatically load `.env`.
- API not reachable: verify the API terminal is still running and visit
  `http://127.0.0.1:8001/api/v1/status`. Click Retry after fixing the problem.
- Port occupied: stop your earlier web dev server before restarting. Integration
  tests require ports 8002 and 5174 free; they launch and stop isolated servers.
- Missing images: the text cache still works offline, but uncached images need
  access to `assets.tcgdex.net`. A fallback is expected when an image cannot load.
- Disabled Analytics and Agent features are intentional Phase 3 boundaries.
- Collection unavailable: check write permission for `data/user-state.sqlite3` or
  your `POKELAB_USER_DB_PATH`. Do not delete ownership storage to repair card data.

## Tests and build

From the repository root on Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[web,dev,desktop]"
.\.venv\Scripts\python.exe -m pytest -q
cd web
npm.cmd test
npm.cmd run build
npx.cmd playwright install chromium
npm.cmd run test:integration
```

`desktop` installs the optional Qt dependencies so preserved UI regression tests run.
The build explicitly runs TypeScript type checking. Browser integration requires a
synchronized database, internet access for real-image verification, and free ports
8002/5174. It compares the first two pages against SQLite and blocks non-loopback
outbound connections from the backend. Unit tests use deterministic fixtures.
On macOS use `.venv/bin/python`, `npm`, and `npx` equivalents.
If Windows pytest cannot access its default temp folder, supply `--basetemp` with a
new disposable directory (pytest owns and may clear that directory).

Validated on September 24, 2026: **172 Python tests, 45 frontend tests, 11
Chromium integration tests; TypeScript and production build passed**. Two upstream
Python test-client deprecation warnings remain. See [test results](TEST-RESULTS.md).

## Roadmap and history

Certified roadmap:

- Phase 1 — Real Cards / Web Foundation: certified.
- Phase 2 — Library & Browsing: certified.
- Phase 3 — Collection & Variations: certified.
- Phase 4 — Competitive Analytics: certified.
- Phase 5 — Deck Builder: certified September 25, 2026.

Next milestone: **Phase 6 — Archetypes & Decklist Research** is implemented on

`phase6-archetype-research` for PM QA, **not merged or certified**. See
[Phase 6 architecture, composite algorithm, runtime and QA scope](docs/phase-6-research.md).
Later work includes authentication before hosted private/paid use, Agent with metering,
cross-device persistence, PWA/mobile hardening, and private-alpha QA. Public beta is later.
The Phase 5 certification tag remains unchanged. Phase 6 uses the same stored main-Limitless evidence; no new ingestion or Agent work is included.

Non-blocking polish backlog:

- Main Deck Builder Gallery +/- control alignment/centering.
- Further finish distinction, intensity, realism, masking, or artistic refinement;
  the current Holo/Reverse visualization and persistent shimmer are accepted.
- Other minor visual inconsistencies found during normal use.

These are future polish items, not Phase 5 certification defects.

See [Phase 2 behavior, API contracts, PM walkthrough and QA scope matrix](docs/phase-2-library.md).
For current controls, use the [Phase 3 QA scope matrix](docs/phase-3-collection.md#mandatory-qa-scope-matrix).
Restart the API and run `npm ci` in `web/` when upgrading from Phase 1.
Browser library URL: `/`; exact-printing detail URL: `/cards/<printing-id>`.
The Phase 2 QA pass adds independent category browsing state, cumulative page
progress and a structured Pokémon **Ability: Yes / No** filter. Empty filter families
are unrestricted; selections OR within a family and AND across families. The
Library displays the newest matching Standard-legal representative per existing
functional-card identity, with a Library-only Basic Energy type grouping, retaining
exact detail IDs. Canonical engine identity and MCP remain unchanged. Restart the API after this
update; no database migration or re-sync is required. Other categories' remembered
queries last for the mounted client session; the active URL survives refresh.

The annotated `pre-web-pivot-2026-09-24` tag preserves Python/Qt/MCP history.
The `web-pivot` development line contains the Figma import and web implementation.
Phase 2 is preserved on `phase-2-library`; Phase 3 on `phase-3-collection`;
Phase 4 on `phase-4-competitive` and its unchanged certification tag.
The complete accepted Phase 5 history is retained on `phase5-deck-builder` and main.
SQLite files, credentials, personal profiles, generated executables and dependencies
are excluded from Git. Never put provider keys in browser configuration.
