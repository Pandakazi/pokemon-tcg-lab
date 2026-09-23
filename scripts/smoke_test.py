"""Exercise all seven tools on an already-running local endpoint."""
import argparse
import asyncio
import json
from pathlib import Path
from uuid import uuid4

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def run(url: str):
    deck = json.loads((Path(__file__).resolve().parents[1] / "examples/bully-box-demo.json").read_text())
    # Unique versions make reruns append-only and leave the demo ready to inspect.
    run_id = uuid4().hex[:8]
    deck["version"] = "demo-" + run_id + "-v1"
    async with streamable_http_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            discovered = {t.name for t in (await session.list_tools()).tools}
            assert discovered == {"get_card", "search_cards", "validate_deck", "get_deck", "save_deck_version", "compare_decks", "analyze_deck"}

            async def call(name, arguments):
                result = await session.call_tool(name, arguments)
                assert not result.isError, (name, result.content)
                assert result.structuredContent is not None
                return result.structuredContent

            card = await call("get_card", {"card_id": "sv02-097"})
            assert card["card"]["name"] == "Mimikyu"
            search = await call("search_cards", {"query": "Mimikyu"})
            assert any(c["id"] == "sv02-097" for c in search["cards"])
            validation = await call("validate_deck", {"deck": deck})
            assert validation["total_cards"] == 60
            assert validation["status"] == "passes_supported_checks", validation
            saved = await call("save_deck_version", {"deck": deck})
            assert saved["saved"]
            loaded = await call("get_deck", {"name": deck["name"], "version": deck["version"]})
            assert loaded["deck"] == deck
            analysis = await call("analyze_deck", {"name": deck["name"], "version": deck["version"]})
            assert 0 < analysis["opening_hand"]["mulligan_probability"] < 1
            before = deck["version"]
            deck["version"] = "demo-" + run_id + "-v2"
            # Switch one printing without changing the card-name count.
            next(e for e in deck["cards"] if e["card_id"] == "sv01-181")["count"] -= 1
            deck["cards"].append({"card_id": "sv01-255", "count": 1})
            assert (await call("save_deck_version", {"deck": deck}))["saved"]
            comparison = await call("compare_decks", {"name": deck["name"], "from_version": before, "to_version": deck["version"]})
            assert sorted(c["delta"] for c in comparison["changes"]) == [-1, 1]
            print(json.dumps({"tools_tested": sorted(discovered), "deck": deck["name"],
                              "versions": [before, deck["version"]], "total_cards": validation["total_cards"],
                              "validation": validation["status"], "opening_hand": analysis["opening_hand"],
                              "comparison": comparison}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/mcp")
    asyncio.run(run(parser.parse_args().url))
