"""Real SDK client/server integration on an ephemeral loopback port."""
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
import pytest
import httpx


@pytest.fixture
def endpoint(tmp_path, request):
    root = Path(__file__).parents[1]
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {**os.environ, "PYTHONPATH": str(root / "src"), "TCG_CARD_SOURCE": "snapshot",
           "TCG_DB_PATH": str(tmp_path / "integration.sqlite3"), "TCG_PORT": str(port)}
    if getattr(request, "param", None) == "sqlite":
        from tcg_lab.card_db import SQLiteCards
        from test_card_data import card, set_record
        cards = SQLiteCards(tmp_path / "cards.sqlite3")
        cards.put_set(set_record())
        cards.put_set(set_record("base1", "base"))
        cards.put(card())
        cards.put(card("base1-58", "Pikachu"))
        env.update(TCG_CARD_SOURCE="sqlite", TCG_CARDS_DB_PATH=str(cards.path))
    with (tmp_path / "server.log").open("w+") as log:
        proc = subprocess.Popen([sys.executable, "-m", "tcg_lab.server"], env=env, cwd=root, stdout=log, stderr=log)
        try:
            for _ in range(100):
                if proc.poll() is not None:
                    log.seek(0)
                    pytest.fail(log.read())
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                        break
                except OSError:
                    time.sleep(0.1)
            else:
                pytest.fail("Server failed to start within 10 seconds")
            yield f"http://127.0.0.1:{port}/mcp"
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


def test_all_tools_over_http(endpoint):
    root = Path(__file__).parents[1]
    result = subprocess.run([sys.executable, str(root / "scripts/smoke_test.py"), "--url", endpoint],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert len(report["tools_tested"]) == 7


def test_tool_annotations_and_errors(endpoint):
    async def run():
        async with streamable_http_client(endpoint) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = {t.name:t for t in (await session.list_tools()).tools}
                assert tools["save_deck_version"].annotations.readOnlyHint is False
                assert tools["get_deck"].annotations.readOnlyHint is True
                missing = await session.call_tool("get_card", {"card_id":"missing-card"})
                assert missing.isError
                bad = await session.call_tool("validate_deck", {"deck":{"name":"x", "version":"v1", "cards":[{"card_id":"sv02-097", "count":-1}]}})
                assert bad.isError
    asyncio.run(run())


def test_browser_health_and_beginner_check(endpoint):
    health = httpx.get(endpoint.replace("/mcp", "/health")).json()
    assert health["app"] == "pokemon-tcg-lab"
    assert health["status"] == "running"
    assert health["mcp_path"] == "/mcp"
    root = Path(__file__).parents[1]
    port = endpoint.split(":")[-1].split("/")[0]
    result = subprocess.run([sys.executable, str(root / "scripts/check_server.py"), "--port", port], capture_output=True, text=True, timeout=40)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "All 7 tools" in result.stdout


@pytest.mark.parametrize("endpoint", ["sqlite"], indirect=True)
def test_sqlite_tools_contract_over_http(endpoint):
    async def run():
        async with streamable_http_client(endpoint) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = {t.name: t for t in (await session.list_tools()).tools}
                assert len(tools) == 7
                assert tools["get_card"].inputSchema["properties"]["include_image"]["default"] is False
                for name in ("Pikachu", "Dhelmise"):
                    response = await session.call_tool("search_cards", {"query": name})
                    assert not response.isError
                    result = response.structuredContent
                    assert result["cards"][0]["name"] == name
                    assert "attacks" not in json.dumps(result)
                    assert "assets.tcgdex" not in json.dumps(result)
                response = await session.call_tool("search_cards", {"set_id": "sm2", "collector_number": "59", "text": "cannot retreat"})
                assert response.structuredContent["total"] == 1
                full = await session.call_tool("get_card", {"card_id": "sm2-59"})
                assert full.structuredContent["card"]["abilities"][0]["name"] == "Steelworker"
                assert "assets.tcgdex" not in json.dumps(full.model_dump())
                image = await session.call_tool("get_card", {"card_id": "sm2-59", "include_image": True})
                assert image.structuredContent["card"]["image"]
                wrong = await session.call_tool("get_card", {"card_id": "Dhelmise"})
                assert wrong.isError
    asyncio.run(run())
