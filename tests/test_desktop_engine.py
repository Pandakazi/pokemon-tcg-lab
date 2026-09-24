"""Native engine acceptance without live APIs or an AI model."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path

import httpx
import pytest

from pokelab.engine import PokeLabEngine, CardQuery, functional_signature
from pokelab.analytics import Analytics, LimitlessClient
from pokelab.agent import SelectedCardAgent, AnthropicProvider
from pokelab.images import TCGdexImages
from pokelab.secrets import SecretStore
from test_card_data import card, set_record


@pytest.fixture
def engine(tmp_path):
    engine = PokeLabEngine(tmp_path / "cards.sqlite3")
    engine.cards.put_set(set_record())
    psychic = card("sm2-1", "Psychic Card")
    psychic["legal"]["standard"] = True
    psychic["variants"] = {"normal": True, "holo": True}
    dragon = card("sm2-2", "Dragon Card")
    dragon.update(types=["Dragon"], legal={"standard": True})
    water = card("sm2-3", "Water Card")
    water.update(types=["Water"], legal={"standard": True})
    energy = card("sm2-4", "Basic Energy")
    energy.update(category="Energy", energyType="Normal", legal={"standard": True})
    energy.pop("attacks")
    energy.pop("abilities")
    old = card("sm2-5", "Old Card")
    unknown = card("sm2-6", "Unknown Card")
    unknown.pop("legal")
    for record in (psychic, dragon, water, energy, old, unknown):
        engine.cards.put(record)
    engine.rebuild_identities()
    return engine


def event(engine, event_id="event1", days_ago=1, **extras):
    return {"id": event_id, "name": "Fixture Cup", "game": "PTCG", "format": "STANDARD", "date": (datetime.now(timezone.utc)-timedelta(days=days_ago)).isoformat(), **extras}


def standing(player, copies=2, archetype="dragon", number="1"):
    return {"player": player, "name": player, "placing": 1,
            "deck": {"id": archetype, "name": archetype.title()},
            "decklist": {"pokemon": [{"name": "Psychic Card", "set": "GRI", "number": number, "count": copies}],
                         "energy": [{"name": "Basic Energy", "set": "GRI", "number": "4", "count": 60-copies}], "trainer": []}}


def test_standard_pool_excludes_illegal_and_unknown(engine):
    assert engine.browse(CardQuery())["total"] == 4
    assert engine.browse(CardQuery(text="Old"))["total"] == 0
    assert engine.browse(CardQuery(text="Unknown"))["total"] == 0


def test_ownership_and_multiselect_filter_semantics(engine):
    engine.set_quantity("sm2-1", "normal", 3)
    engine.set_quantity("sm2-1", "holo", 2)
    engine.set_quantity("sm2-3", "unspecified", 1)
    query = CardQuery(category="Pokemon", ownership="owned", types=("Psychic", "Dragon"))
    result = engine.browse(query)
    assert [c["id"] for c in result["cards"]] == ["sm2-1"]
    assert result["cards"][0]["owned"] == 5
    assert engine.browse(CardQuery(category="Pokemon", types=("Psychic", "Dragon")))["total"] == 2
    assert engine.browse(CardQuery(ownership="unowned", types=("Psychic", "Dragon"), category="Pokemon"))["cards"][0]["id"] == "sm2-2"
    assert PokeLabEngine(engine.path).collection_quantity("sm2-1", "holo") == 2


def test_quantity_bounds_and_bad_query(engine):
    for value in (-1, 1.5, True, 10000):
        with pytest.raises(ValueError):
            engine.set_quantity("sm2-1", "normal", value)
    with pytest.raises(ValueError):
        engine.set_quantity("missing-card", "normal", 1)
    with pytest.raises(ValueError):
        engine.browse(CardQuery(ownership="made-up"))
    with pytest.raises(ValueError):
        engine.browse(CardQuery(types=("'); DROP TABLE cards;--",)))


def test_functional_identity_keeps_same_name_different_rules_apart(engine):
    a = card("sm2-10", "Same Name")
    b = card("sm2-11", "Same Name")
    assert functional_signature(a) == functional_signature(b)
    b["attacks"][0]["damage"] = 999
    assert functional_signature(a) != functional_signature(b)
    engine.cards.put(a)
    engine.cards.put(b)
    engine.set_quantity("sm2-10", "normal", 2)
    engine.rebuild_identities()
    assert engine.identity("sm2-10") != engine.identity("sm2-11")
    assert engine.collection_quantity("sm2-10", "normal") == 2
    assert engine.collection_quantity("sm2-11", "normal") == 0


def test_same_function_different_printing_does_not_merge_ownership(engine):
    printing = engine.cards.get("sm2-1")["card"]
    printing.update(id="sm2-100", localId="100", rarity="Ultra Rare")
    engine.cards.put(printing)
    engine.rebuild_identities()
    assert engine.identity("sm2-100") == engine.identity("sm2-1")
    engine.set_quantity("sm2-100", "normal", 4)
    assert engine.collection_quantity("sm2-1", "normal") == 0


def test_limitless_aggregation_timeframes_and_drilldown(engine):
    analytics = Analytics(engine)
    analytics.import_event(event(engine), [standing("one", 2), standing("two", 4), standing("other", 3, "water", "3")])
    analytics.import_event(event(engine, "old-event", 45), [standing("old", 4)])
    identity = engine.identity("sm2-1")
    result = analytics.stats(identity, 30)
    assert result["sample_size"] == 3 and result["included_decks"] == 2
    assert result["usage_percent"] == 66.67 and result["average_copies"] == 3
    assert result["top_archetypes"][0]["share_percent"] == 100
    assert analytics.stats(identity, 60)["sample_size"] == 4
    drill = analytics.drilldown(identity, "dragon", 30)
    assert len(drill) == 2 and drill[0]["source"].startswith("https://play.limitlesstcg.com/")
    assert sum(c["count"] for group in drill[0]["cards"].values() for c in group) == 60
    # Idempotent refresh, not duplicated observations.
    analytics.import_event(event(engine), [standing("one", 2), standing("two", 4), standing("other", 3, "water", "3")])
    assert analytics.stats(identity, 30)["sample_size"] == 3


def test_unresolved_lists_excluded_not_counted_as_absence(engine):
    analytics = Analytics(engine)
    unresolved = standing("unknown")
    unresolved["decklist"]["pokemon"][0].update(name="Unmapped", number="999")
    analytics.import_event(event(engine), [standing("known"), unresolved])
    result = analytics.stats(engine.identity("sm2-1"))
    assert result["sample_size"] == 1 and result["excluded_unresolved"] == 1
    assert result["usage_percent"] == 100


def test_bad_update_and_custom_rules_preserve_cached_event(engine):
    analytics = Analytics(engine)
    analytics.import_event(event(engine), [standing("known")])
    bad = standing("bad")
    bad["decklist"]["pokemon"][0]["count"] = "2"
    with pytest.raises(ValueError):
        analytics.import_event(event(engine), [bad])
    with pytest.raises(ValueError):
        analytics.import_event(event(engine, bannedCards=["some-card"]), [standing("known")])
    assert analytics.stats(engine.identity("sm2-1"))["sample_size"] == 1


def test_no_evidence_is_unknown_not_zero_and_current_format_explicit(engine):
    analytics = Analytics(engine)
    assert analytics.stats(engine.identity("sm2-1"))["usage_percent"] is None
    with pytest.raises(ValueError, match="start date"):
        analytics.stats(engine.identity("sm2-1"), None)
    engine.setting("format_start", "2026-01-01")
    assert analytics.stats(engine.identity("sm2-1"), None)["period_start"].startswith("2026-01-01")


def test_compact_agent_context_no_images_raw_corpus_or_collection(engine):
    analytics = Analytics(engine)
    analytics.import_event(event(engine), [standing("private-player-name")])
    engine.set_quantity("sm2-1", "normal", 3)
    agent = SelectedCardAgent(engine, analytics)
    context = agent.context("sm2-1")
    serialized = json.dumps(context)
    assert len(serialized) < 16000
    assert all(value not in serialized for value in ("private-player-name", "assets.tcgdex.net", "decklist", "quantity"))
    class FakeProvider:
        def answer(self, question, evidence):
            assert evidence["analytics"]["sample_size"] == 1
            return "Grounded fixture response"
    assert agent.ask(FakeProvider(), "sm2-1", "What pairs with this?") == "Grounded fixture response"
    assert engine.collection_quantity("sm2-1", "normal") == 3


def test_provider_contract_and_safe_error(engine):
    context = SelectedCardAgent(engine, Analytics(engine)).context("sm2-1")
    def handle(request):
        payload = json.loads(request.content)
        assert payload["max_tokens"] == 700 and "tools" not in payload
        assert request.headers["x-api-key"] == "fake-test-secret"
        return httpx.Response(200, json={"content": [{"type": "text", "text": "Test answer"}]})
    assert AnthropicProvider("fake-test-secret", transport=httpx.MockTransport(handle)).answer("Explain", context) == "Test answer"
    with pytest.raises(ValueError, match="HTTP 401") as error:
        AnthropicProvider("fake-test-secret", transport=httpx.MockTransport(lambda _: httpx.Response(401, text="fake-test-secret"))).answer("Explain", context)
    assert "fake-test-secret" not in str(error.value)


def test_limitless_failure_does_not_erase_cache(engine):
    analytics = Analytics(engine)
    analytics.import_event(event(engine), [standing("known")])
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(503))) as http:
        with pytest.raises(httpx.HTTPStatusError):
            LimitlessClient(http, delay=0).refresh(analytics)
    assert analytics.stats(engine.identity("sm2-1"))["sample_size"] == 1


def test_image_provider_only_allows_expected_assets():
    provider = TCGdexImages()
    assert provider.url({"image": "https://assets.tcgdex.net/en/sm/sm2/59"}).endswith("/low.webp")
    assert provider.url({"image": "https://assets.tcgdex.net/en/sm/sm2/59"}, True).endswith("/high.webp")
    assert provider.url({"image": "file:///C:/secrets"}) is None
    assert provider.url({"image": "https://evil.example/img"}) is None


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI")
def test_secret_storage_is_encrypted_and_user_bound(tmp_path):
    secrets = SecretStore(tmp_path)
    secrets.save("fake-secret-for-test")
    assert b"fake-secret-for-test" not in secrets.path.read_bytes()
    assert secrets.load() == "fake-secret-for-test"
    secrets.delete()
    assert secrets.load() == ""


def test_official_set_abbreviation_resolves_ambiguous_names(engine):
    original = engine.cards.get("sm2-1")["card"]
    alternate = dict(original, id="sm2-99", localId="99", hp=999)
    engine.cards.put(alternate)
    engine.cards.put_set({"id": "sm2", "name": "Example", "serie": {"id": "sm"}, "abbreviation": {"official": "GRI"}})
    engine.rebuild_identities()
    analytics = Analytics(engine)
    assert len(analytics.resolver()[1]["psychic card"]) == 2
    analytics.import_event(event(engine), [standing("known")])
    assert analytics.stats(engine.identity("sm2-1"))["sample_size"] == 1
    assert engine.cards.search("", set_id="GRI", collector_number="1")["total"] == 1
    assert analytics.remap_cached() == 1
    assert analytics.stats(engine.identity("sm2-1"))["sample_size"] == 1


def test_refresh_can_be_canceled_without_network():
    import threading
    canceled = threading.Event()
    canceled.set()
    with httpx.Client(transport=httpx.MockTransport(lambda r: pytest.fail("No HTTP after cancel"))) as http:
        with pytest.raises(InterruptedError):
            LimitlessClient(http, cancel_event=canceled).get("/tournaments")
