# Changelog

## Phase 3 final PM cleanup — 2026-09-24

- Suppressed synthetic Unspecified finish choices; preserved and separately exposed
  existing unassigned quantities without guessing or migrating finishes.
- Framed and bounded Card Detail/variation artwork, centered primary controls,
  replaced detached hover preview with in-place +50 px enlargement without reflow.
- Kept all Collection List ownership content inside its row separator.
- Preserved canonical grouping, artwork preferences and exact quantity semantics.

## Phase 3 — Collection & Variations (2026-09-24)

- Reused exact printing/variant quantity semantics in separate versioned user-state
  storage, with a transactional one-time copy of legacy Qt ownership when present.
- Added functional Library ownership filters/totals and exact +/− controls, persisted
  Library artwork preferences, canonical Card Detail variations and exact quantities.
- Added full-color four-column variation browsing, detail-only artwork enlargement,
  and an exact owned-printing Collection workspace. Preserved Phase 2 identity,
  Basic Energy selection, navigation, filtering and optional MCP behavior.
- Documented ownership boundaries, migration, local QA and the complete scope matrix.
  Conditions and all Phase 4 features remain unimplemented.

## Phase 2 Basic Energy image fix — 2026-09-24

Prefer the newest eligible Standard Basic Energy printing with usable TCGdex image
metadata. Retain the correct image-less representative when none is eligible.
Special Energy, canonical identity and MCP behavior remain unchanged. Added
selection regressions and browser image decoding checks for all eight Basic types.

## Phase 2 final cleanup — 2026-09-24

- Curated Basic Energy grouping by type only in the human-facing Library; canonical
  functional identities, Special Energy grouping and exact-printing access retained.
- Replaced Has Ability with an Ability Yes/No family between Stage and Regulation.
  Neither/both are unrestricted; single selections use structured Ability presence.
  Legacy `has_ability=true` links remain supported.
- Updated regression/browser coverage and the final PM QA scope matrix.

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
