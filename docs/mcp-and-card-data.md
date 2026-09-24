# Pokémon TCG Lab

Pokémon TCG Lab runs on your computer and exposes seven Pokémon card and deck tools through MCP (Model Context Protocol). Use MCP Inspector in your browser to look up cards, check deck lists, save named deck versions, and compare them.

This guide starts with an extracted ZIP and ends with a successful card lookup. You do not need Git, an OpenAI API key, or a paid account to run the local project.

## 1. Download and extract the project

Download the project ZIP from [Pandakazi/pokemon-tcg-lab](https://github.com/Pandakazi/pokemon-tcg-lab): use **Code → Download ZIP**. On Windows, right-click the ZIP and choose **Extract All**. On macOS, double-click the ZIP. Move the extracted project folder somewhere you can find it, such as Documents.

Open the extracted folder and confirm it contains `Run-Local.ps1`, `Run-Local.command`, `pyproject.toml`, and the `src` folder. Do not run the project from inside the ZIP. GitHub may name the folder `pokemon-tcg-lab-main`; that is fine. Commands below assume you renamed it `pokemon-tcg-lab` under Documents. Substitute your actual folder path if different.

## 2. Install Python

The server requires **Python 3.11 or newer, within Python 3**. Install Python from [python.org](https://www.python.org/downloads/). On Windows, enable **Add Python to PATH** if offered. On macOS, use the [macOS installer](https://www.python.org/downloads/macos/); Homebrew is not required.

After installing, close and reopen your terminal.

**Windows:** Open PowerShell and run:

```powershell
py -3 --version
```

If `py` is not found, try `python --version`. A version such as `Python 3.13.x` is suitable.

**macOS:** Open Terminal and run:

```bash
python3 --version
```

## 3. Start Pokémon TCG Lab — window 1

The first launch needs internet to download Python dependencies. The launcher creates its own `.venv` environment, installs the project, and copies `.env.example` to `.env` if `.env` does not already exist. You do not need to activate the environment or edit configuration for the first test.

### Windows

In PowerShell:

```powershell
cd "$HOME\Documents\pokemon-tcg-lab"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Run-Local.ps1
```

The execution-policy option applies to this one PowerShell process; it does not permanently change your computer's policy. If your computer is managed by an organization, its policy may still apply.

### macOS

In Terminal:

```bash
cd "$HOME/Documents/pokemon-tcg-lab"
bash ./Run-Local.command
```

Using `bash` also works when the extracted file does not have executable permission.

### Confirm the server is ready

Wait for the launcher to display:

```text
Pokemon TCG Lab is ready!
Local MCP endpoint: http://127.0.0.1:8000/mcp
Browser check:      http://127.0.0.1:8000/health
```

Keep this terminal window open. It is running the server.

Open the displayed **Browser check** address in a browser. You should see JSON containing `"app":"pokemon-tcg-lab"` and `"status":"running"`. This page is a health check, not the tool interface. The `/mcp` address is for MCP clients; opening it as a normal webpage is not a useful connection test.

If port 8000 is occupied, the launcher may choose another port. Always use the exact endpoint printed by the launcher in the next steps.

## Initialize or update cards

**Do this once after the first server launch, before trying card tools.** The launcher has now created the project's Python environment. Open a second terminal in the project folder, leaving the server window open.

**Windows (PowerShell):**

```powershell
cd "$HOME\Documents\pokemon-tcg-lab"
.\.venv\Scripts\python.exe -m tcg_lab.sync_cards
```

**macOS (Terminal):**

```bash
cd "$HOME/Documents/pokemon-tcg-lab"
./.venv/bin/python -m tcg_lab.sync_cards
```

Wait for **Card database ready** and `"status": "complete"`. The initial download takes several minutes and needs internet; progress is printed along the way. It stores the complete English TCGdex catalog in `data/cards.sqlite3`. It downloads **card data only, never card image files**. Afterward, card searches, lookups, and deck checks work offline from SQLite. There is no silent fallback to the small demo snapshot.

**Upgrading an older copy:** Open `.env` in a text editor. Change `TCG_CARD_SOURCE=snapshot` (or `live`) to `TCG_CARD_SOURCE=sqlite`. Keep your other settings. If needed, add `TCG_CARDS_DB_PATH=data/cards.sqlite3`. Save, stop the old server with Ctrl+C, and run your usual launcher again. Reconnect Inspector so it reloads the updated tool inputs. New installations already use SQLite by default. If the server was already using SQLite, completed sync updates are visible without restarting it.

**Update later:** Run the same sync command again. It discovers new printings and rechecks records last checked at least seven days ago. Recently checked cards are skipped. To force all cards to be rechecked now—especially after a rotation or a source correction—append `--refresh`:

```powershell
# Windows
.\.venv\Scripts\python.exe -m tcg_lab.sync_cards --refresh
```

```bash
# macOS
./.venv/bin/python -m tcg_lab.sync_cards --refresh
```

To inspect progress/completion later without accessing the internet, append `--status` instead. You can stop sync with Ctrl+C; completed card downloads are retained. Rerun the same command to resume. A failed or partial sync exits with an error and preserves the last good records. It reports failed/missing counts; retry when the connection or upstream service recovers. A full initial sync must finish before treating search results as the complete catalog. Sync never modifies your saved-deck database.

## 4. Install Node.js for MCP Inspector

Python runs Pokémon TCG Lab. Node.js runs the separate Inspector interface.

Install the current **LTS** version from [nodejs.org](https://nodejs.org/), using the normal installer options. Close and reopen terminals after installation. Leave or restart the server in window 1.

Open a **second** PowerShell window on Windows or Terminal window on macOS. Run these commands one at a time:

```text
node --version
npm --version
```

Both should print version numbers. Inspector requires **Node.js 22.19.0 or newer** according to its [official documentation](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/docs/2026-07-28/tools/inspector.mdx). If either command fails, reinstall Node.js and open a new terminal.

## 5. Launch MCP Inspector — window 2

On Windows, use the `.cmd` command so PowerShell does not need to run an npm PowerShell script:

```powershell
npx.cmd @modelcontextprotocol/inspector
```

On macOS:

```bash
npx @modelcontextprotocol/inspector
```

If npm asks to install the package, type `y` and press Enter. Keep this second terminal open too. Inspector should open in your browser. If it does not, open the complete local URL printed in window 2, including any authentication token. The Inspector URL is separate from the Pokémon server's port-8000 endpoint.

To reproduce the exact Inspector version tested below, use `npx.cmd @modelcontextprotocol/inspector@2.7.0` on Windows or `npx @modelcontextprotocol/inspector@2.7.0` on macOS instead of the unversioned command.

## 6. Add and connect the Pokémon server

These steps were tested in **MCP Inspector v2.7.0**, the **Servers** dashboard with **Add Servers** and example entries such as `filesystem-server-default`, `everything-server-default`, and `example-server-default`. Those examples are not Pokémon TCG Lab. You do not need to start them.

1. On **Servers**, click **Add Servers**.
2. Click **+ Add manually**.
3. In **Server ID**, enter `pokemon-tcg-lab`.
4. Open **Transport**. Change `stdio (local process)` to **streamable-http**.
5. In **URL**, enter `http://127.0.0.1:8000/mcp`. If the server printed a different port, use that endpoint instead. Leave optional authentication settings empty; this local server needs no authentication.
6. Click **Add**.
7. Find the new `pokemon-tcg-lab` card, labeled **Streamable HTTP**. It initially says **Disconnected**. Turn **on the switch at the upper right of that card** to connect.
8. After connection, Inspector shows **Pokemon TCG Lab** and navigation for **Servers**, **Tools**, **Prompts**, and **Resources**.
9. Click **Tools**. The seven tools load automatically; this version has no **List Tools** step.

If `pokemon-tcg-lab` is already present, use its switch to connect instead of adding a duplicate. Inspector releases can change the interface; the version and labels above identify the flow verified for this guide.

## 7. Run your first Pokémon tool

Select **get_card**. In the field labeled **Card Id** (the underlying argument is `card_id`), enter exactly:

```text
sv02-097
```

If Inspector shows a JSON arguments editor instead of individual inputs, enter:

```json
{"card_id": "sv02-097"}
```

Click **Execute Tool**.

A successful result contains a `card` with `id` equal to `sv02-097` and `name` equal to `Mimikyu`, plus source information and a retrieval date. This is a read-only lookup; it does not create a saved deck.

Next, try **search_cards** with `query` set to `Mimikyu`, then click **Execute Tool**. Leave `page` at `1` and `page_size` at `20` if those fields are shown. The result should include `sv02-097`. The `query` field searches names or an exact printing ID. Use the optional `text` field to search card text. Use the returned printing IDs for subsequent lookups.

## 8. Check the connection without Inspector

With window 1 still running, open another terminal in the project folder. This check connects over MCP, lists all seven tools, and retrieves Mimikyu without saving deck data.

**Windows:**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Run-Local.ps1 -Check
```

**macOS:**

```bash
bash ./Run-Local.command --check
```

Expected output:

```text
PASS: Connected to Pokemon TCG Lab. All 7 tools were found, and Mimikyu was retrieved.
No saved decks were changed.
```

If using a particular port, add `-Port 8100` on Windows or `--port 8100` on macOS, replacing 8100 with the displayed port.

## What the seven tools do

- `get_card(card_id)`: retrieve one exact TCGdex printing.
- `search_cards(query, page=1, page_size=20)`: search names and find printing IDs.
- `validate_deck(deck)`: check an explicit deck object without saving it.
- `save_deck_version(deck, allow_invalid=false)`: append a new local, immutable version. Reusing a name/version pair fails.
- `get_deck(name, version)`: retrieve a saved version; omit `version` for the latest saved version.
- `compare_decks(name, from_version, to_version)`: compare printing-level card counts between saved versions.
- `analyze_deck(name, version)`: recheck a saved deck and calculate composition and random opening-seven Basic/mulligan probabilities.

A deck object needs `name`, `version`, and `cards`; each card entry has a `card_id` and integer `count`. The optional `format` is `standard`, `expanded`, or `unlimited` and defaults to `standard`. `notes` is optional. See [examples/bully-box-demo.json](../examples/bully-box-demo.json) for a complete sample. That file is demonstration data, not your personal deck. To use it with `validate_deck`, place the whole sample object inside a top-level `deck` argument.

Validation covers supported checks and reports unknowns. A result of `passes_supported_checks` is not a complete tournament legality certification. The analysis is not a match simulator or matchup win-rate forecast.

## Card data, settings, and saved decks

Normal operation uses `TCG_CARD_SOURCE=sqlite`: the synchronized English TCGdex database. The original `snapshot` mode remains available for deterministic automated tests. Legacy `live` mode is still available explicitly, but calls TCGdex on every lookup and does not support the advanced local filters. It is not the recommended normal mode.

Card responses retain structured attacks/costs/damage, abilities, Trainer/Energy text, stage/suffix, types, weaknesses/resistances/retreat, regulation marks, provider legality, and source dates when supplied. Missing source fields are not invented. Raw source records, including extra useful fields and image references, are preserved locally. Large pricing and detailed finish-variant blocks are kept in SQLite but excluded from MCP responses. Images, set logos, and booster artwork are hidden by default; use `include_image=true` on `search_cards` or `get_card` to request URL references. No image library is downloaded or committed.

Legality is **TCGdex's dated structured assertion**, not a model's guess or tournament certification. `--refresh` updates those flags after rotations/corrections. No fixed regulation-letter rule is hard-coded. Missing legality remains unknown, including Unlimited where no flag is supplied. Reprint equivalence, card-specific rules, and official bans still need independent verification. Search excludes Pocket by default, using source set-series metadata; request `game="pocket"` explicitly to inspect it. Deck validation rejects known Pocket cards for physical TCG decks.

Other settings:

- `TCG_CARDS_DB_PATH=data/cards.sqlite3` selects the local card database (separate from saved decks).
- `TCG_DB_PATH=data/decks.sqlite3` selects the local saved-deck database.
- `TCG_PORT=8000` selects the preferred port. A launcher port argument overrides it.

The launcher starts in the project folder, so its relative database path resolves there. Saved versions persist across restarts. To back up your decks, stop the server and copy the `data` folder somewhere safe. Keep `.env` private; `.env.example` is the shareable starting configuration.

This version binds to `127.0.0.1`, so clients must run on the same computer. It has no application authentication and is intended for local use.

## Stop and restart

1. In Inspector's **Servers** view, turn off the Pokémon server card's switch if a connection is active.
2. In the Inspector terminal (window 2), press **Ctrl+C**. On Windows, answer `Y` if asked to terminate the batch job.
3. In the Pokémon server terminal (window 1), press **Ctrl+C**. Wait for shutdown before closing the window.

To restart, run the same server command from step 3, then the same Inspector command from step 5. Reconnect using the newly displayed endpoint. Existing `.env` settings and saved decks are retained. If the launcher says the server is already running, keep its original terminal open; the new launcher has detected that existing instance.

## Troubleshooting

### A command is not recognized

Reopen the terminal after installing Python or Node.js. Confirm the version commands above. Run project commands from the extracted folder containing the launcher files. If Windows opens the Microsoft Store for `python`, install Python from python.org and try `py -3`.

### PowerShell says scripts are disabled

Use the full Windows launcher command shown above with `powershell.exe -NoProfile -ExecutionPolicy Bypass -File`. For npm/Inspector, use `npm.cmd --version` and `npx.cmd @modelcontextprotocol/inspector`. No permanent execution-policy change is required.

### Setup fails or dependencies are broken

Check your internet connection and read the first error printed above the launcher message. Stop the server, then repair the installation:

```powershell
# Windows, from the project folder
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Run-Local.ps1 -Repair
```

```bash
# macOS, from the project folder
bash ./Run-Local.command --repair
```

Repair reinstalls dependencies and then starts the server. It preserves saved decks. Do not delete `data` as a troubleshooting step.

### Inspector cannot connect

Check the server terminal is still open and the displayed `/health` URL works. Set the transport to **Streamable HTTP**, and use the complete printed URL ending in `/mcp`, not `/health`. Match any changed port. The Pokémon server requires no OAuth token or API key. Inspector's own local proxy token, if present in its launch URL, is separate; reopen its complete printed browser URL if Inspector reports proxy authorization failure. Restart Inspector after changing Node.js.

### Port 8000 is busy, or another copy is already running

The launcher tries nearby free ports and prints the chosen address. To run this extracted copy separately, choose a port explicitly:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Run-Local.ps1 -Port 8100
```

```bash
bash ./Run-Local.command --port 8100
```

Update Inspector's URL to match. The launcher does not stop unrelated programs. An existing Pokémon instance may belong to another extracted folder and therefore another deck database.

### No cards found, unknown printing, or no saved deck

If the database is empty or incomplete, run the sync command above. Confirm `.env` uses `TCG_CARD_SOURCE=sqlite`, then restart the server if you changed it. A response saying `bundled snapshot only` means the old snapshot setting is still selected. First test `get_card` with `sv02-097`. Card names such as `Mimikyu` are not valid `card_id` values. `get_deck` and `analyze_deck` need a version previously created by `save_deck_version`; the example JSON file is not automatically imported.

### A save fails

Choose a new version label when a name/version pair already exists. Inspect validation errors before saving an invalid deck; `allow_invalid=true` explicitly permits that save. Saved versions are append-only through the exposed tools.

## Developer setup

Use Python 3.11+ and run commands from the project root. The beginner launcher already installs the runtime in editable mode; install the dev extra for pytest.

**Windows:**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m tcg_lab.server
```

**macOS:**

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -e '.[dev]'
test -f .env || cp .env.example .env
./.venv/bin/python -m pytest
./.venv/bin/python -m tcg_lab.server
```

The final command runs the HTTP server in the foreground. The installed `pokemon-tcg-lab` entry point is equivalent. To use an MCP client that launches stdio subprocesses, pass `--transport stdio`; Inspector's HTTP instructions above use the default `streamable-http` transport instead.

With an HTTP server running, the read-only integration check is `scripts/check_server.py --port 8000`. The broader `scripts/smoke_test.py --url http://127.0.0.1:8000/mcp` exercises all seven tools and **writes two demo deck versions** to the running server's database on each run. Run it against a separate test database if you want to keep personal data free of demos. Prefix either script command with `.\.venv\Scripts\python.exe` on Windows or `./.venv/bin/python` on macOS.

Build a clean shareable source ZIP:

```powershell
# Windows
.\.venv\Scripts\python.exe scripts/build_distribution.py --output dist/pokemon-tcg-lab.zip
```

```bash
# macOS
./.venv/bin/python scripts/build_distribution.py --output dist/pokemon-tcg-lab.zip
```

The distribution builder uses an allowlist and omits `.env`, `.venv`, and personal databases. A fresh user still needs the prerequisites and first-launch downloads described above.

Implementation guide: `src/tcg_lab/server.py` registers tools and routes; `cards.py` implements snapshot/live providers and compact projections; `card_db.py` provides indexed SQLite reads and full source storage; `sync_cards.py` refreshes TCGdex records; `models.py` defines deck inputs; `service.py` validates and analyzes; `store.py` stores versions. `scripts/launcher.py` manages setup and startup. Tests live in `tests/`.

## V1 Inspector acceptance tests

After sync and any required restart, reconnect **pokemon-tcg-lab**, open **Tools**, and run:

1. **search_cards**: `query` = `Pikachu`, `page_size` = `5`. Click **Execute Tool**. Expect matching printing IDs and compact summaries, with `scope` = `local TCGdex database`. No attacks, full card text, or image URLs should appear.
2. **search_cards**: `query` = `Dhelmise`, `page_size` = `20`. Choose an exact returned ID. The synced catalog includes `sm2-59` (Guardians Rising, collector number 59).
3. **get_card**: `card_id` = `sm2-59`, leave **Include Image** false. Expect Dhelmise, 120 HP, Psychic, the **Steelworker** ability and **Anchor Shot** attack, structured attack costs/text/damage, weaknesses/resistance/retreat, and provider legality. No image URL should appear.
4. Run the same **get_card** with **Include Image** true. An `image` URL reference should now appear. This does not download an image.
5. Optional combined search: leave `query` empty, set `set_id` = `sm2` (or source code `GRI`), `collector_number` = `59`, and `text` = `retreat`. Expect the same printing.

`get_card("Dhelmise")` is intentionally not a name lookup: many printings share a name. Search names first, then pass one exact returned printing ID to `get_card` and deck entries.

Other optional search filters are `format` (`standard`, `expanded`, `unlimited`), `legality` (`legal`, `not_legal`, `unknown`; requires `format`), `pokemon_type`, `trainer_type`, `regulation_mark`, `category`, and `game`. Filters combine with AND. `format` alone selects source-reported legal cards. Omitting `query` requires at least one filter. `text` is a case-insensitive substring across card names, abilities, attacks, and rules/effect text. Results are sorted by exact ID for deterministic pagination; page size stays capped at 50.

## V1 compatibility notes

All seven tool names and existing positional inputs remain. `get_card(card_id)` still returns a `card` object and source metadata. `search_cards(query, page, page_size)` still returns `cards`, pagination, and scope; it now offers optional filters and compact printing summaries. Both card tools add `include_image=false`. Printing IDs containing source punctuation (including `exu-%3F`) are preserved exactly.

Decks still store exact IDs and counts, never full card text. New validation responses replace the repetitive per-card `card_sources` map with a compact `sources` summary grouped by provider and retrieval-date range. Previously saved versions retain their historical validation payloads; `analyze_deck` revalidates against the current cache. Saved deck versions are not rewritten by sync.

## Verification notes

The full suite passed: **64 tests**, including all 35 original tests. V1 tests cover mocked TCGdex synchronization, conditional refresh, parsing, interrupted/partial recovery, offline SQLite reads, filters, exact IDs, image opt-in, and real MCP HTTP transport. All original deterministic snapshot tests remain. Live synchronization stored all 23,736 English catalog records with zero failures during this revision. A real MCP HTTP acceptance check found 227 Pikachu and 17 Dhelmise printings, retrieved sm2-59 with Steelworker and Anchor Shot, confirmed image opt-in, and matched the combined set-code/collector-number/text filter. Windows commands were executed; macOS commands use the same Python module but have not been run on a Mac in this session.

Source schema and behavior: [TCGdex card reference](https://tcgdex.dev/reference/card), [REST card lookup](https://tcgdex.dev/rest/card), and [filtering/pagination](https://tcgdex.dev/rest/filtering-sorting-pagination).
