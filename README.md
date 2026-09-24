# PokéLab

PokéLab is a web-first, PWA-capable competitive Pokémon TCG research, collection,
deckbuilding and analysis environment in development toward private alpha.
These are product directions, not a claim that every feature is available.

Architecture: React/TypeScript/Vite/Tailwind → FastAPI /api/v1 → existing Python
engine → SQLite. Card data comes from synchronized TCGdex records. The frontend
originated in the approved PokéLab Web Prototype v0.1 Figma Make artifact.

The current implementation slice connects real Standard Pokémon cards to the web
gallery. Run instructions and validated test results will accompany completion.
Collection, filters, competitive analytics and the provider-independent Agent are
later web slices. Existing analytics use cached Play! Limitless evidence with
explicit coverage/mapping limitations, not a complete paper-tournament census.
PWA installation, authentication and hosted persistence are not yet implemented.

MCP is an optional integration. Qt is a frozen earlier reference prototype.
See [architecture decision](docs/adr-001-web-first.md),
[frontend provenance](docs/figma-provenance.md),
[historical Qt guide](docs/qt-prototype.md), and
[MCP/card-data guide](docs/mcp-and-card-data.md).
