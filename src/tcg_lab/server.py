import argparse
import os
from typing import Any, Literal

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from starlette.responses import JSONResponse

from .engine import create_lab
from .models import Deck, Label
from .service import Lab


def create_server(lab: Lab | None = None) -> FastMCP:
    load_dotenv()
    source = os.getenv("TCG_CARD_SOURCE", "sqlite")
    if source not in ("sqlite", "snapshot", "live"):
        raise ValueError("TCG_CARD_SOURCE must be sqlite, snapshot or live.")
    lab = lab or create_lab(source)
    mcp = FastMCP("Pokemon TCG Lab", host="127.0.0.1", port=int(os.getenv("TCG_PORT", "8000")),
                  stateless_http=True, json_response=True,
                  instructions="Use exact printing IDs. Never treat the demo as the user's canonical deck. Report validation unknowns and dated sources. Saving creates an immutable version.")
    read = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=source == "live")
    write = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=source == "live")

    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(request):
        return JSONResponse({"app": "pokemon-tcg-lab", "status": "running", "version": "0.1.1",
                             "pid": os.getpid(), "mcp_path": "/mcp", "startup_id": os.getenv("TCG_STARTUP_ID")})

    @mcp.tool(annotations=read)
    def get_card(card_id: str, include_image: bool = False) -> dict[str, Any]:
        """Full text for one exact printing ID from search_cards. SQLite is offline; images opt-in."""
        return lab.cards.get(card_id, include_image=include_image)

    @mcp.tool(annotations=read)
    def search_cards(query: str = "", page: int = 1, page_size: int = 20,
                     set_id: str | None = None, collector_number: str | None = None,
                     text: str | None = None, format: Literal["standard", "expanded", "unlimited"] | None = None,
                     legality: Literal["legal", "not_legal", "unknown"] | None = None,
                     pokemon_type: str | None = None, trainer_type: str | None = None,
                     regulation_mark: str | None = None, category: Literal["Pokemon", "Trainer", "Energy"] | None = None,
                     game: Literal["tcg", "pocket", "unknown"] | None = None,
                     include_image: bool = False) -> dict[str, Any]:
        """Compact local name/ID search. Optional filters combine with AND; text searches rules. format defaults to legal flags only, never inferred. Pocket excluded by default. Fetch full text with get_card."""
        return lab.cards.search(query, page, page_size, include_image,
                                set_id=set_id, collector_number=collector_number, text=text, format=format,
                                legality=legality, pokemon_type=pokemon_type, trainer_type=trainer_type,
                                regulation_mark=regulation_mark, category=category, game=game)

    @mcp.tool(annotations=read)
    def validate_deck(deck: Deck) -> dict[str, Any]:
        """Check an explicit deck's count, duplicate names across printings, Basic Pokemon, ACE SPEC and provider legality; report unsupported/unknown rules."""
        return lab.validate(deck)

    @mcp.tool(annotations=read)
    def get_deck(name: Label, version: Label | None = None) -> dict[str, Any]:
        """Read a saved deck and its version history. Omit version for the most recently saved version. Validation is the historical save-time result."""
        return lab.store.get(name, version)

    @mcp.tool(annotations=write)
    def save_deck_version(deck: Deck, allow_invalid: bool = False) -> dict[str, Any]:
        """Save a new immutable local deck version. Duplicate versions fail. Invalid decks require allow_invalid=true; incomplete checks remain clearly labeled."""
        return lab.save(deck, allow_invalid)

    @mcp.tool(annotations=read)
    def compare_decks(name: Label, from_version: Label, to_version: Label) -> dict[str, Any]:
        """Compare two saved versions of the same deck, returning exact printing-level additions and removals."""
        return lab.compare(name, from_version, to_version)

    @mcp.tool(annotations=read)
    def analyze_deck(name: Label, version: Label | None = None) -> dict[str, Any]:
        """Read and revalidate a saved deck, summarize composition and compute random opening-seven Basic/mulligan probabilities."""
        return lab.analyze(Deck.model_validate(lab.store.get(name, version)["deck"]))

    return mcp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["streamable-http", "stdio"], default="streamable-http")
    args = parser.parse_args()
    create_server().run(transport=args.transport)


if __name__ == "__main__":
    main()
