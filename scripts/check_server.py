"""Read-only sanity check: no pytest, Node or sample-deck writes."""
import argparse
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def check(port):
    async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = {tool.name for tool in (await session.list_tools()).tools}
            expected = {"get_card", "search_cards", "get_deck", "save_deck_version", "compare_decks", "validate_deck", "analyze_deck"}
            if names != expected:
                raise RuntimeError("The tools do not match this version.")
            card = await session.call_tool("get_card", {"card_id": "sv02-097"})
            if card.isError or not card.structuredContent or card.structuredContent["card"]["name"] != "Mimikyu":
                raise RuntimeError("Card lookup failed.")
            print("PASS: Connected to Pokemon TCG Lab. All 7 tools were found, and Mimikyu was retrieved.")
            print("No saved decks were changed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    try:
        asyncio.run(asyncio.wait_for(check(parser.parse_args().port), timeout=30))
    except Exception:
        print("The check could not finish. Keep the server window open, check its displayed address, and rerun with -Check -Port NUMBER (Windows) or --check --port NUMBER (Mac). Live card lookup also needs internet.")
        raise SystemExit(1)
