import copy
import json
from concurrent.futures import ThreadPoolExecutor
from math import comb
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from tcg_lab.cards import CardLookupError, LiveCards, SnapshotCards
from tcg_lab.models import Deck, DeckEntry
from tcg_lab.service import Lab
from tcg_lab.store import DeckStore


@pytest.fixture
def deck():
    return Deck.model_validate_json((Path(__file__).parents[1] / "examples/bully-box-demo.json").read_text())


@pytest.fixture
def lab(tmp_path):
    return Lab(SnapshotCards(), DeckStore(tmp_path / "decks.sqlite3"))


def test_demo_and_probability(lab, deck):
    result = lab.analyze(deck)
    assert result["validation"]["status"] == "passes_supported_checks"
    assert result["validation"]["categories"] == {"Pokemon": 10, "Trainer": 32, "Energy": 18}
    assert result["validation"]["tournament_legal"] is None
    assert result["opening_hand"]["mulligan_probability"] == pytest.approx(comb(50, 7) / comb(60, 7))


@pytest.mark.parametrize("count", [0, -1, 1.5, True, "4", 61])
def test_bad_counts(count):
    with pytest.raises(ValidationError):
        DeckEntry(card_id="sv02-097", count=count)


def test_total_and_standard_rotation(lab, deck):
    deck.cards[-1].count -= 1
    assert "exactly 60" in lab.validate(deck)["errors"][0]
    deck.format = "standard"
    assert any("not legal in standard" in x for x in lab.validate(deck)["errors"])


def test_duplicates_across_rows_and_printings(lab, deck):
    deck.cards.append(DeckEntry(card_id="sv01-255", count=1))
    deck.cards[-2].count -= 1
    assert any("nest ball: 5" in x for x in lab.validate(deck)["errors"])
    deck.cards[-1].card_id = "sv01-181"
    assert any("nest ball: 5" in x for x in lab.validate(deck)["errors"])


def test_ace_spec_includes_special_energy(lab, deck):
    deck.cards[-1].count -= 1
    deck.cards.append(DeckEntry(card_id="sv05-162", count=1))
    assert any("2 ACE SPEC" in x for x in lab.validate(deck)["errors"])


def test_missing_and_unknown_legality(lab, deck):
    lab.cards.cards = copy.deepcopy(lab.cards.cards)
    lab.cards.cards["sv02-097"].pop("legal")
    result = lab.validate(deck)
    assert result["status"] == "incomplete"
    assert lab.analyze(deck)["opening_hand"]["probability_at_least_one_basic"] is None
    deck.cards[0].card_id = "not-found"
    assert "not in the bundled snapshot" in " ".join(lab.validate(deck)["unknown"])


def test_no_basics(lab, deck):
    deck.cards = [DeckEntry(card_id="sv03.5-207", count=60)]
    assert any("at least one Basic" in x for x in lab.validate(deck)["errors"])


def test_immutable_versions_persist_and_compare(lab, deck):
    assert lab.save(deck)["saved"]
    with pytest.raises(ValueError, match="already exists"):
        lab.save(deck)
    deck.version = "v0-saved-later"
    deck.cards[0].count -= 1
    deck.cards[-1].count += 1
    lab.save(deck)
    reopened = DeckStore(lab.store.path)
    assert reopened.get("  BULLY BOX (DEMO)  ")["deck"]["version"] == "v0-saved-later"
    assert reopened.get(deck.name, "demo-v1")["deck"]["cards"][0]["count"] == 4
    diff = lab.compare(deck.name, "demo-v1", "v0-saved-later")
    assert sorted(c["delta"] for c in diff["changes"]) == [-1, 1]


def test_concurrent_duplicate_version(lab, deck):
    validation = lab.validate(deck)
    def save(_):
        try:
            lab.store.save(deck, validation)
            return True
        except ValueError:
            return False
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(save, range(4))) == 1


def test_invalid_draft_requires_opt_in(lab, deck):
    deck.cards[-1].count -= 1
    assert lab.save(deck)["saved"] is False
    assert lab.save(deck, allow_invalid=True)["saved"] is True


def test_missing_version(lab):
    with pytest.raises(ValueError, match="not found"):
        lab.store.get("unknown")


def test_snapshot_search_and_input_bounds(lab):
    assert len(lab.cards.search("Nest Ball")["cards"]) == 2
    assert len(lab.cards.search("Nest Ball", page=2, page_size=1)["cards"]) == 1
    with pytest.raises(ValueError):
        lab.cards.search("", 0, 100)
    with pytest.raises(ValueError):
        lab.cards.get("../../etc/passwd")


def test_live_adapter_contract():
    def handle(request):
        if request.url.path.endswith("/cards/sv02-097"):
            return httpx.Response(200, json={"id":"sv02-097", "name":"Mimikyu", "category":"Pokemon", "pricing":{}})
        assert request.url.params["name"] == "like:Mimikyu"
        assert request.url.params["pagination:itemsPerPage"] == "2"
        return httpx.Response(200, json=[{"id":"sv02-097", "name":"Mimikyu"}])
    live = LiveCards(httpx.MockTransport(handle))
    assert live.get("sv02-097")["live"] is True
    assert "pricing" not in live.get("sv02-097")["card"]
    assert live.search("Mimikyu", page_size=2)["next_page"] is None


@pytest.mark.parametrize("status", [404, 429, 500])
def test_provider_failures_are_explicit(status):
    live = LiveCards(httpx.MockTransport(lambda _: httpx.Response(status)))
    with pytest.raises(CardLookupError, match="lookup failed"):
        live.get("sv02-097")
