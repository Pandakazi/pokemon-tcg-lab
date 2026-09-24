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
