"""Typed, read-only Phase 6 resources over Phase 4 evidence."""
from typing import Literal
from pydantic import BaseModel
from .competitive_models import Window, Provenance
from .web_models import CardSummary


class PageHash(BaseModel):
    url: str
    sha256: str
    parser: str


class ResearchSummary(BaseModel):
    id: str
    source_id: str
    name: str
    source: Literal['limitless-main'] = 'limitless-main'
    window: Window
    format_available: bool
    format_start: str | None
    period_start: str | None
    period_end: str
    evidence_start: str | None
    evidence_end: str | None
    status: Literal['observed','limited_evidence','no_data','mapping_failure','format_unavailable']
    eligible_decks: int
    published_decks: int
    excluded_unmapped: int
    tournament_count: int
    results_without_lists: int
    results_without_lists_scope: str
    prevalence_min_decks: int
    source_error: str | None
    provenance: list[Provenance]


class QuantityBucket(BaseModel):
    quantity: int
    decks: int


class ResearchCard(BaseModel):
    functional_id: str
    card: CardSummary | None
    owned: int


class CardStatistic(ResearchCard):
    included_decks: int
    eligible_decks: int
    inclusion_percent: float | None
    total_copies: int
    average_when_included: float
    average_all_decks: float
    median_copies: float
    distribution: list[QuantityBucket]


class CardStatistics(BaseModel):
    archetype_id: str
    window: Window
    cards: list[CardStatistic]


class DeckObservation(BaseModel):
    id: str
    event_id: str
    event: str
    date: str
    player: str
    placement: int
    archetype_id: str
    archetype_source_id: str
    archetype: str
    source_url: str | None
    event_url: str
    mapped: bool
    fetched_at: str


class EvidencePage(BaseModel):
    archetype_id: str
    window: Window
    total: int
    page: int
    page_size: int
    next_page: int | None
    decks: list[DeckObservation]


class DeckCard(ResearchCard):
    quantity: int


class PublishedCard(BaseModel):
    name: str
    set: str
    number: str
    count: int


class TournamentDeck(BaseModel):
    source: Literal['limitless-main'] = 'limitless-main'
    observation: DeckObservation
    card_count: int
    mapped_card_count: int
    categories: dict[str,int]
    cards: list[DeckCard]
    published_cards: list[PublishedCard]
    unmapped_cards: list[PublishedCard]
    pages: list[PageHash]
    presentation_note: str


class Composite(BaseModel):
    archetype_id: str
    window: Window
    label: Literal['Archetype Composite'] = 'Archetype Composite'
    algorithm: Literal['validated-observed-medoid-v1'] = 'validated-observed-medoid-v1'
    status: Literal['available','unavailable']
    sample_size: int
    limited_evidence: bool
    total: int
    categories: dict[str,int]
    cards: list[DeckCard]
    reasons: list[str]
    limitations: list[str]
