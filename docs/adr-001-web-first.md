# ADR 001 — Web-first PokéLab (2026-09-24)

Approved: PokéLab adopts a web-first, PWA-capable architecture while preserving
its existing Python engine. The Qt client is frozen as a reference prototype,
and MCP remains an optional adapter.

One React/TypeScript/Vite/Tailwind frontend will serve desktop, tablet and mobile.
A thin FastAPI /api/v1 boundary calls existing Python services and local SQLite.
This retains the approved functional Figma prototype and tested engine, provides
paths to cross-device persistence and installability, and avoids maintaining two
primary presentation layers.

Tradeoffs: authentication, multi-user isolation, hosted persistence, internet-facing
security, deployment/operations, PWA/mobile requirements, infrastructure and AI costs.
These responsibilities are not implemented by Phase 1.

Phase 1 is limited to status and paginated Standard Pokémon summaries, real images,
loading/errors/fallbacks, and tests. No collection, filters, analytics, Agent, auth,
billing, service worker or production deployment is connected. Later competitive
analytics must retain Play! Limitless provenance and incomplete mapping caveats.
Provider-independent Agent groundwork remains preserved; provider allowances and
BYOA policy await a later decision.

Historical references: qt-prototype.md, pokelab-architecture.md, pokelab-qa.md,
mcp-and-card-data.md, pre-web-pivot.md. The Qt EXE remains uncertified with a known
DLL startup failure. No packaging remediation is part of the pivot.
