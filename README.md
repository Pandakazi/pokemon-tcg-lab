# PokéLab

PokéLab is a **web-first, PWA-capable competitive Pokémon TCG research, collection,
deckbuilding and analysis environment**, in development toward private alpha.
The roadmap describes future capabilities; Phase 1 currently provides a read-only
web gallery of real Standard Pokémon printings.

The approved PokéLab Web Prototype v0.1 Figma Make frontend supplies the visual
and interaction direction. We reuse its generated source, not a screenshot recreation.

## What works now

- Real TCGdex-backed Standard Pokémon printings from local SQLite.
- Exact printing IDs, names, sets, collector numbers and dated legality provenance.
- Real, lazily loaded images; meaningful missing-image fallback.
- Pagination, loading/error states and retry; collapsible side panels.
- Normal browsing reads SQLite and never initiates TCGdex synchronization.

Filters, Trainer/Energy navigation, list view, collection, competitive analytics,
Agent and authentication are disabled/unconnected in this slice. PWA installation,
offline service workers, hosting and billing are not implemented.

## Architecture

React 19 + TypeScript + Vite + Tailwind (`web/`)
→ same-origin `/api/v1` → FastAPI (`src/pokelab/api.py`)
→ existing Python card services → SQLite.

Card text is synchronized from TCGdex. Images load on demand from TCGdex assets;
no image library is bundled. Standard legality uses structured source flags and
shows source freshness; it is not guessed by AI.

Existing collection, filtering, functional/printing identities, competitive analytics
and provider-independent Agent groundwork remain in the Python engine. Analytics
currently represents cached **Play! Limitless** submitted lists, with unresolved
mappings excluded and coverage explicitly limited; it is not a full paper metagame
census. The Agent remains read-only and provider-independent; only its Anthropic
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
  tests require ports 8001 and 5173 free; they launch and stop their own servers.
- Missing images: the text cache still works offline, but uncached images need
  access to `assets.tcgdex.net`. A fallback is expected when an image cannot load.
- Disabled controls are intentional Phase 1 boundaries, not broken connections.

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
8001/5173. It compares the first two pages against SQLite and blocks non-loopback
outbound connections from the backend. Unit tests use deterministic fixtures.
On macOS use `.venv/bin/python`, `npm`, and `npx` equivalents.
If Windows pytest cannot access its default temp folder, supply `--basetemp` with a
new disposable directory (pytest owns and may clear that directory).

Validated on September 24, 2026: **94 Python tests, 6 frontend tests, 1 real-data
Chromium integration test; TypeScript and production build passed**. Two upstream
Python test-client deprecation warnings remain. See [test results](TEST-RESULTS.md).

## Roadmap and history

Next, after PM review: real filtering, user-aware collection, competitive analytics,
archetype evidence, authentication before hosted private/paid use, Agent with metering,
cross-device persistence, PWA/mobile hardening, and private-alpha QA. Public beta is later.
No later slice is activated by this milestone.

The annotated `pre-web-pivot-2026-09-24` tag preserves Python/Qt/MCP history.
The `web-pivot` development line contains the Figma import and web implementation.
SQLite files, credentials, personal profiles, generated executables and dependencies
are excluded from Git. Never put provider keys in browser configuration.
