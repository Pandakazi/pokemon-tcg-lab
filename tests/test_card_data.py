"""Deterministic TCGdex HTTP fixtures; no live network needed for the suite."""
import copy
import json
import sqlite3
from contextlib import closing

import httpx
import pytest

from tcg_lab.card_db import SQLiteCards, parse_card
from tcg_lab.cards import CardLookupError, SnapshotCards, LiveCards
from tcg_lab.models import Deck, DeckEntry
from tcg_lab.service import Lab
from tcg_lab.store import DeckStore
from tcg_lab.sync_cards import SyncError, request, synchronize


def card(card_id="sm2-59", name="Dhelmise"):
    return {"id": card_id, "name": name, "localId": card_id.rsplit("-", 1)[1],
            "set": {"id": card_id.rsplit("-", 1)[0], "name": "Guardians Rising", "logo": "https://assets.tcgdex.net/logo"},
            "category": "Pokemon", "hp": 120, "types": ["Psychic"], "stage": "Basic", "rarity": "Rare",
            "abilities": [{"name": "Steelworker", "type": "Ability", "effect": "Metal Pokemon attacks do 10 more damage."}],
            "attacks": [{"name": "Anchor Shot", "cost": ["Psychic", "Colorless", "Colorless"], "damage": 70, "effect": "The Defending Pokemon cannot retreat."}],
            "weaknesses": [{"type": "Darkness", "value": "x2"}], "resistances": [{"type": "Fighting", "value": "-20"}],
            "retreat": 2, "legal": {"standard": False, "expanded": True}, "regulationMark": "A",
            "image": "https://assets.tcgdex.net/en/sm/sm2/59", "updated": "2026-01-01T00:00:00Z",
            "boosters": [{"id": "b1", "artwork_front": "https://assets.tcgdex.net/art"}],
            "pricing": {"unused": 123}, "variants_detailed": [{"type": "normal"}], "futureUsefulField": {"rule": "keep me"}}


def set_record(set_id="sm2", serie="sm"):
    return {"id": set_id, "name": "Guardians Rising", "serie": {"id": serie}, "tcgOnline": "GRI"}


@pytest.fixture
def db(tmp_path):
    return SQLiteCards(tmp_path / "cards.sqlite3")


def transport(records, calls, *, fail=None, conditional=False):
    def handle(req):
        calls.append(req)
        path = req.url.path
        if path.endswith("/cards"):
            return httpx.Response(200, json=[{"id": c["id"], "name": c["name"]} for c in records])
        if "/sets/" in path:
            set_id = path.rsplit("/", 1)[1]
            return httpx.Response(200, json=set_record(set_id, "tcgp" if set_id == "A1" else "sm"))
        if fail:
            return httpx.Response(fail)
        if conditional and req.headers.get("If-None-Match") == '"v1"':
            return httpx.Response(304)
        for c in records:
            if path.endswith("/" + c["id"]):
                return httpx.Response(200, json=c, headers={"ETag": '"v1"'})
        return httpx.Response(404)
    return httpx.MockTransport(handle)


def sync(db, records, **kwargs):
    calls = []
    with httpx.Client(transport=transport(records, calls)) as client:
        report = synchronize(db, client=client, progress=lambda _: None, **kwargs)
    return report, calls


def test_initial_sync_roundtrip_and_no_images_downloaded(db):
    report, calls = sync(db, [card(), card("base1-58", "Pikachu")])
    assert report["status"] == "complete" and report["catalog"] == 2
    assert all(r.url.host == "api.tcgdex.net" for r in calls)
    with closing(db.connect()) as sql:
        raw = json.loads(sql.execute("SELECT raw FROM cards WHERE id='sm2-59'").fetchone()[0])
    assert raw == card()  # Every source field retained, including inexpensive extras.
    reopened = SQLiteCards(db.path)
    result = reopened.get("sm2-59")
    for key in ("abilities", "attacks", "weaknesses", "resistances", "retreat", "updated", "futureUsefulField"):
        assert result["card"][key] == card()[key]
    assert result["live"] is False and result["game"] == "tcg"


def test_local_search_filters_pagination_and_compact_response(db, monkeypatch):
    newer = card("sv08-001")
    newer.update(regulationMark="H", legal={"standard": True, "expanded": True})
    sync(db, [card(), newer, card("base1-58", "Pikachu")])
    monkeypatch.setattr(httpx.Client, "get", lambda *a, **k: pytest.fail("Local reads must not use HTTP"))
    result = db.search("dHeLmIsE", page_size=1)
    assert result["total"] == 2 and result["next_page"] == 2
    assert db.search("Dhelmise", page=2, page_size=1)["next_page"] is None
    brief = result["cards"][0]
    assert {"id", "name", "set", "localId", "hp", "types", "legal"} <= brief.keys()
    assert not ({"attacks", "abilities", "effect", "pricing", "image", "futureUsefulField"} & brief.keys())
    assert "assets.tcgdex" not in json.dumps(result)
    assert len(db.search("Pikachu")["cards"]) == 1
    assert db.search("sm2-59")["cards"][0]["id"] == "sm2-59"
    assert db.search("", set_id="sm2", collector_number="59", pokemon_type="psychic", text="cannot retreat", format="expanded")["total"] == 1
    assert db.search("", set_id="GRI", collector_number="59")["total"] == 1
    assert db.get("sm2-59")["card"]["set"]["code"] == "GRI"
    assert db.search("Dhelmise", format="standard")["cards"][0]["id"] == "sv08-001"
    assert db.search("Dhelmise", format="standard", legality="not_legal")["cards"][0]["id"] == "sm2-59"
    assert db.search("", regulation_mark="H")["total"] == 1
    assert db.search("' OR 1=1 --")["total"] == 0
    assert db.search("%_")["total"] == 0


def test_missing_empty_and_unknown_legality(db):
    with pytest.raises(CardLookupError, match="database is empty"):
        db.search("Pikachu")
    with pytest.raises(CardLookupError, match="database is empty"):
        db.get("sm2-59")
    c = card()
    c.pop("legal")
    db.put(c)
    assert db.search("Dhelmise", format="standard")["total"] == 0
    assert db.search("Dhelmise", format="standard", legality="unknown")["total"] == 1
    assert db.search("Dhelmise", format="unlimited")["total"] == 0
    with pytest.raises(CardLookupError, match="Search by name first"):
        db.get("Dhelmise")


def test_images_opt_in_all_providers(db):
    db.put(card())
    assert "assets.tcgdex" not in json.dumps(db.get("sm2-59"))
    full = db.get("sm2-59", include_image=True)["card"]
    assert full["image"] and full["set"]["logo"] and full["boosters"][0]["artwork_front"]
    assert "image" in db.search("Dhelmise", include_image=True)["cards"][0]
    snapshot = SnapshotCards()
    assert "assets.tcgdex" not in json.dumps(snapshot.get("sv02-097"))
    assert "image" in snapshot.get("sv02-097", True)["card"]
    live = LiveCards(httpx.MockTransport(lambda r: httpx.Response(200, json=card())))
    assert "assets.tcgdex" not in json.dumps(live.get("sm2-59"))
    assert live.get("sm2-59", True)["card"]["image"]


def test_incremental_skips_then_refresh_updates_legality(db):
    sync(db, [card()])
    changed = card()
    changed["legal"]["standard"] = True
    report, calls = sync(db, [changed])
    assert report["skipped"] == 1
    assert not any(r.url.path.endswith("/cards/sm2-59") for r in calls)
    report, _ = sync(db, [changed], refresh=True)
    assert report["updated"] == 1
    assert db.get("sm2-59")["card"]["legal"]["standard"] is True


def test_conditional_refresh(db):
    sync(db, [card()])
    original = db.get("sm2-59")["fetched_at"]
    calls = []
    with httpx.Client(transport=transport([card()], calls, conditional=True)) as client:
        report = synchronize(db, client=client, refresh=True, progress=lambda _: None)
    assert report["unchanged"] == 1
    assert db.get("sm2-59")["fetched_at"] == original
    assert db.get("sm2-59")["checked_at"] >= original


def test_upstream_failure_preserves_last_good_and_resumes(db):
    sync(db, [card()])
    previous = db.get("sm2-59")
    records = [card(), card("base1-58", "Pikachu")]
    calls = []
    with httpx.Client(transport=transport(records, calls, fail=404)) as client:
        report = synchronize(db, client=client, refresh=True, progress=lambda _: None)
    assert report["status"] == "partial" and report["missing"] == 1
    assert db.get("sm2-59") == previous
    report, _ = sync(db, records)
    assert report["status"] == "complete" and report["skipped"] == 1 and report["updated"] == 1


@pytest.mark.parametrize("payload", [[], {}, [{"id": "../../bad"}], [{"id": "sm2-59"}, {"id": "sm2-59"}]])
def test_invalid_catalog_never_destroys_cache(db, payload):
    db.put(card())
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload))) as client:
        with pytest.raises(SyncError, match="catalog"):
            synchronize(db, client=client, progress=lambda _: None)
    assert db.get("sm2-59")["card"]["name"] == "Dhelmise"


@pytest.mark.parametrize("change", [{"id": "wrong-id"}, {"category": None}, {"legal": {"standard": "true"}}, {"attacks": "bad"}, {"set": None}, {"localId": None}])
def test_parsing_rejects_corruption(change):
    bad = card()
    bad.update(change)
    with pytest.raises(CardLookupError):
        parse_card(bad, "sm2-59")


@pytest.mark.parametrize("status", [429, 500, 503])
def test_retries_bounded_and_retry_after_honored(status):
    calls, delays = [], []
    def handle(r):
        calls.append(r)
        return httpx.Response(status, headers={"Retry-After": "1"})
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(SyncError):
            request(client, "https://api.tcgdex.net/v2/en/cards", sleep=delays.append)
    assert len(calls) == 3 and delays == [1, 1]


def test_network_down_graceful():
    def fail(r):
        raise httpx.ConnectError("offline")
    with httpx.Client(transport=httpx.MockTransport(fail)) as client:
        with pytest.raises(SyncError):
            request(client, "https://api.tcgdex.net/v2/en/cards", sleep=lambda _: None)


def test_trainer_energy_and_pocket_filters(db):
    trainer = card("sm2-100", "Test Trainer")
    trainer.update(category="Trainer", trainerType="Item", effect="Draw a card.")
    energy = card("sm2-101", "Test Energy")
    energy.update(category="Energy", energyType="Special", effect="Provides Energy.")
    pocket = card("A1-1", "Dhelmise")
    sync(db, [trainer, energy, pocket])
    assert db.search("", trainer_type="item", category="Trainer")["total"] == 1
    assert db.get("sm2-101")["card"]["effect"] == "Provides Energy."
    assert db.search("Dhelmise")["total"] == 0
    assert db.search("Dhelmise", game="pocket")["total"] == 1
    lab = Lab(db, DeckStore(db.path.parent / "decks.sqlite3"))
    deck = Deck(name="pocket", version="v1", cards=[DeckEntry(card_id="A1-1", count=60)])
    result = lab.validate(deck)
    assert any("Pocket" in e for e in result["errors"])
    assert "assets.tcgdex" not in json.dumps(result) and "attacks" not in json.dumps(result)
    assert "card_sources" not in result and "sources" in result


def test_special_exact_printing_ids(db):
    for card_id in ("exu-!", "exu-%3F"):
        db.put(card(card_id, "Unown"))
        assert db.get(card_id)["card"]["id"] == card_id
        assert DeckEntry(card_id=card_id, count=1).card_id == card_id


def test_sync_lock_releases_after_process_or_context(db):
    lock = sqlite3.connect(str(db.path) + ".sync-lock.sqlite3")
    try:
        lock.execute("BEGIN IMMEDIATE")
        with pytest.raises(SyncError, match="already running"):
            synchronize(db)
    finally:
        lock.close()
    assert sync(db, [card()])[0]["status"] == "complete"


def test_snapshot_filters_reuse_local_semantics():
    result = SnapshotCards().search("", set_id="sv02", collector_number="097")
    assert result["cards"][0]["id"] == "sv02-097"
    assert result["scope"] == "bundled snapshot only"


def test_bad_filter_and_argument_bounds(db):
    db.put(card())
    for options in ({"format": "made-up"}, {"legality": "legal"}, {"unused": "x"}, {"page": 0}, {"page_size": 51}):
        with pytest.raises(ValueError):
            db.search("Dhelmise", **options)


def test_bad_replacement_does_not_overwrite_good_card(db):
    sync(db, [card()])
    previous = db.get("sm2-59")
    broken = card()
    broken["legal"] = {"standard": "guess"}
    report, _ = sync(db, [broken], refresh=True)
    assert report["status"] == "partial" and report["failed"] == 1
    assert db.get("sm2-59") == previous


def test_interrupted_sync_preserves_progress_and_can_resume(db):
    def interrupted(message):
        if message.startswith("Downloading/checking"):
            raise KeyboardInterrupt
    calls = []
    with httpx.Client(transport=transport([card()], calls)) as client:
        with pytest.raises(KeyboardInterrupt):
            synchronize(db, client=client, progress=interrupted)
    assert db.status()["last_sync"]["status"] == "interrupted"
    assert sync(db, [card()])[0]["status"] == "complete"
