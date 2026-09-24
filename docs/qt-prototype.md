> Historical Qt reference guide. The web-first decision supersedes this product direction. The packaged EXE remains uncertified with a known DLL startup failure. See [ADR 001](adr-001-web-first.md).

# PokéLab Desktop

**The agent proposes. The player decides. PokéLab remembers.**

PokéLab is a Windows-first, local-first Standard Pokémon TCG card browser, collection tracker, and competitive research tool. Python and SQLite own the business logic. The desktop does not require MCP, Inspector, or a separately running server.

This is an engineering QA candidate. Mike is the final usability and certification gate. The [architecture assessment](pokelab-architecture.md) explains the changes and known source limitations; the [manual QA checklist](pokelab-qa.md) covers certification.

## Run PokeLab.exe

1. Open `PokeLab.exe` from the delivered build folder. No Python installation is required for the executable.
2. Wait a few seconds on first launch. The build includes the complete synchronized English card-text catalog; it creates a writable local copy automatically.
3. Browse Gallery or List. Use the left filter rail for collection scope, Pokémon/Trainers/Energy, and multiple Pokémon types.
4. Choose a physical finish and change quantity using minus, the number field, or plus. Ownership persists for that printing/finish.
5. Click **Refresh Limitless** to obtain recent competitive evidence. This runs in the background, is deliberately paced, and may take several minutes. Hover analytics become useful after data is cached.
6. Select a card and open **Agent** for a grounded question after configuring your provider.

Data lives in `%LOCALAPPDATA%\PokeLab`, independently of where the executable is stored. Upgrading the executable never overwrites an existing profile. To back up ownership/settings/evidence, close PokéLab and copy that folder. The encrypted API credential is tied to your Windows account and is not a portable backup credential.

## Card pool, filters, and images

Normal browsing includes only physical English cards marked Standard legal by TCGdex. The initial build's complete 23,736-record catalog contains 3,345 such printings, as synchronized September 23, 2026. The toolbar shows source sync status and date. Source flags can be wrong or outdated; this is not independent official legality certification.

- All / Owned / Unowned refer to the total owned across finishes of each exact printing.
- Psychic + Dragon means Psychic OR Dragon. Adding Owned and Pokémon means Pokémon AND Owned AND (Psychic OR Dragon).
- Trainers is the parent category; Item is not a peer of Trainers.
- Functional identities group identical gameplay records conservatively, while collection ownership always retains printing and variant. Same name alone is not proof of identical gameplay.
- Thumbnails and larger images are requested from TCGdex only when needed. A bounded 100 MB disk cache helps repeated/offline browsing. No image library is packaged.

## Initialize or refresh card data

The shipped executable initializes the complete card-text cache on first launch. Click **Refresh cards** to recheck the current source, update the local database, rebuild functional identities, and remap cached competitive evidence. Keep the app open while it works. **Cancel refresh** preserves completed downloads; incomplete coverage remains labeled until a full sync succeeds.

For a development checkout without a seed, initialize the database from the project folder:

```powershell
.\.venv\Scripts\python.exe -m tcg_lab.sync_cards
```

The initial sync needs internet and takes several minutes. The same command resumes incomplete downloads and discovers new cards. Add `--refresh` to recheck all existing records immediately; add `--status` for an offline status report. These CLI commands target the original `data/cards.sqlite3`; the desktop uses its separate profile. To update a particular desktop profile from the CLI, pass `--db "C:\path\to\profile\pokelab.sqlite3"`, then refresh/restart the desktop as needed to rebuild identities. Prefer the desktop button for normal operation.

On a Mac development environment the equivalent interpreter is `./.venv/bin/python`. The certified target for this desktop milestone is Windows 11 x64; macOS desktop packaging is not part of this MVP.

## Limitless evidence and analytics

**Refresh Limitless** imports up to 25 recent public PTCG Standard events within a 90-day search window from the supported **Play! Limitless** API. Events with custom rules/bans or nonfinal results are excluded. This API's coverage is not the same as all official paper tournaments. No scraping or website embedding is used.

The refresh caches event, player, placing, date, source, archetype, and decklist. Already cached events are normally reused for 24 hours. Rate-limit waits stop or delay work; cached evidence remains available offline. Retry after the displayed wait if the service limits requests.

Hover intentionally for approximately two seconds to open the interactive analytics popup. Moving into it keeps it open; leaving both card and popup closes it after a short grace period. Choose 7/30/60/90 days. For **Current Format**, first enter your intended start date in Settings—PokéLab does not guess a rotation/new-set boundary.

Usage is the share of fully mapped, 60-card submitted lists containing the functional card. Average copies is calculated only among lists containing it. Archetype percentages divide the included lists, not every list in the archetype. All panels expose sample/coverage; unresolved lists are excluded and counted. Click an archetype for underlying decklists and event references. These figures are neither win rates nor causal synergy claims.

Optional development refresh:

```powershell
.\.venv\Scripts\python.exe scripts/refresh_competitive.py --db "C:\path\to\profile\pokelab.sqlite3" --events 25 --days 90
```

## Configure the read-only Agent

1. Open **Settings**. The first supported provider is Anthropic; the default model is `claude-haiku-4-5-20251001`, and the model field is editable.
2. Enter your API credential directly in the masked field, then Save. Windows DPAPI encrypts the key for your account. No plaintext fallback is used. No credential belongs in Git or `.env.example`.
3. Select a card, open Agent, choose the analytics period, and use **Preview exact evidence sent to AI**.
4. Enter a question and click **Ask provider**. This contacts your provider and may incur API charges. A chat subscription is not an API credential.

The agent receives one selected card plus compact locally computed statistics and pairings. It never receives the full card database, raw tournament corpus, collection quantities, or image library. Requests are bounded; output is capped at 700 tokens. There are no AI execution tools or write actions. Provider output is displayed as plain text. The provider interface is replaceable; additional vendors are not implemented or claimed validated in this MVP.

Mike requested that live paid-provider validation happen during his QA. Automated tests validate request construction, context boundaries, and failure handling with mocks.

## Development setup (Windows)

Install Python 3.11 or newer, extract/clone the project, and open PowerShell in its folder. For a fresh checkout:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,desktop,build]"
.\.venv\Scripts\python.exe -m tcg_lab.sync_cards
.\.venv\Scripts\python.exe -m pokelab.desktop
```

If `.venv` already exists, use it and start with the install command. The desktop can initialize from the completed development card cache. Use `--data-dir "C:\path\to\qa-profile"` for an isolated QA profile; this never redirects or overwrites your normal profile.

Run the complete regression suite:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

All data-source and provider tests use deterministic fixtures/mocks. Qt interaction tests require the desktop extra and run offscreen. The original snapshot and real local MCP HTTP tests remain supported. No paid API call is required by the test suite.

## Package PokeLab.exe

On Windows x64, after syncing `data/cards.sqlite3` and installing the build extra:

```powershell
.\.venv\Scripts\python.exe scripts/build_desktop.py
```

The executable is written to `dist/PokeLab.exe`. It includes Python, Qt, and the text-only source cache. The packager rejects seeds containing non-card tables: never point `--seed` at your personal desktop profile. `--output` selects another build folder. Include dependency notices alongside a distributed build. This QA build is unsigned; clean-machine testing and PM certification remain required before release.

## Troubleshooting

- **No cards:** check the displayed sync status; run Refresh cards. An incomplete sync is not the complete Standard pool.
- **No image:** connect to the internet for uncached art. Some source printings lack artwork; text browsing still works.
- **No analytics:** refresh Limitless, widen the timeframe, and inspect the unresolved-list count. No evidence is shown as unavailable, not fabricated 0% usage.
- **Rate limited:** follow the displayed retry delay. Do not repeatedly hammer Refresh. Your existing cache is retained.
- **Current Format error:** configure its start date in Settings.
- **AI authentication/billing error:** verify the API credential, model access, and provider billing in your own account. Keys/errors are not logged into source files.
- **Build import error:** install `.[dev,desktop,build]` using the same `.venv` interpreter used for packaging.
- **Need the earlier MCP workflow:** see [MCP and card-data instructions](mcp-and-card-data.md). That adapter remains optional and uses the same reusable card/deck code.

## Scope

Included: Standard card browser, collection quantities, multi-type filters, cached competitive evidence, intentional interactive hover, archetype drill-down, selected-card read-only Agent, and Windows executable packaging.

Not included: deck-building UI, notebook/research mode, simulation, self-play, mobile, Expanded browser, automated synergy discovery, or AI write workflows. Existing legacy deck-engine functions remain available through the optional MCP adapter.

