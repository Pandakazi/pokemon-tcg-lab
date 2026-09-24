# Changelog

## 0.1.1 — Installation and distribution cleanup

- Replaced fragile Windows import probes with automatic environment creation, installation checks, updates when requirements change, and an explicit repair option. Pytest is development-only.
- Added a macOS launcher using the same setup logic, with quoted paths and no Homebrew requirement.
- Added port collision detection, a bounded fallback, already-running messages, and explicit port selection. Existing processes are never stopped to free a port.
- Added `/health`, readiness confirmation, and a read-only check that discovers all seven MCP tools and retrieves a card without changing decks.
- Rewrote the README for beginners, including Windows policy troubleshooting limited to one process, Mac setup, safe resets, and current official ChatGPT connection guidance.
- Added a reproducible allowlisted ZIP builder. The archive excludes environments, caches, local settings, saved decks, logs, and build artifacts, and normalizes script line endings.
- Kept existing deck storage and the seven-tool scope. See TEST-RESULTS.md for verified behavior and platform limitations.

## Web Phase 1 — 2026-09-24

Preserved/tagged the Python/Qt prototype; imported the approved Figma source with
provenance; adopted a web-first monorepo. Added a read-only FastAPI status/cards
boundary and paginated real Standard Pokémon gallery with real images and error
states. Existing Python services and Qt/MCP behavior retained. No collection,
filtering, analytics, Agent, authentication or PWA implementation activated.

## Phase 2 — Library & Browsing (2026-09-24)

Added validated category/name/multi-select query contracts to the read-only card API,
an exact-printing detail endpoint, and source-derived filter choices. Extended the
existing SQLite search rather than duplicating filtering in JavaScript. Wired the
approved library controls and Gallery/List, URL query state, real card links, and
structured detail text. Preserved frozen Qt/MCP work. Added regression/integration
coverage and the mandatory PM QA scope matrix in docs/phase-2-library.md.

## Phase 2 QA fixes — 2026-09-24

- Normalized empty/duplicate multi-select values; hardened consecutive client query
  edits. Preserved OR within families and AND across populated families.
- Added independent category search/filter/page memory and cumulative result progress.
- Added server-authoritative Has Ability using the source's structured Ability kind.
- Following PM clarification, reused existing functional identity in the read-only
  Library adapter to select the newest eligible Standard printing before pagination.
  MCP exact-printing search, detail routes, Qt and collection state remain preserved.
- Added API, frontend and real-data browser regressions and updated the QA scope matrix.
