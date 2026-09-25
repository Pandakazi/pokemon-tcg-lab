"""Versioned Phase 4 API boundary, independent of evidence materialization."""
from typing import Literal
from pydantic import BaseModel

Window = Literal['7','30','90','format']


class Archetype(BaseModel):
    id: str
    name: str
    decks: int
    eligible_decks: int
    share_percent: float | None
    prevalence_percent: float | None
    status: Literal['observed','insufficient_sample','unclassified']


class CopyBucket(BaseModel):
    copies: str
    decks: int
    percent: float | None


class AssociatedCard(BaseModel):
    functional_id: str
    name: str
    decks: int
    cooccurrence_percent: float
    field_percent: float
    lift: float
    conservative_lift: float


class TrendPoint(BaseModel):
    date: str
    sample_size: int
    included_decks: int
    usage_percent: float | None


class TrendSeries(BaseModel):
    window: Window
    available: bool
    points: list[TrendPoint]


class Provenance(BaseModel):
    id: str
    name: str
    date: str
    url: str
    fetched_at: str
    format: str
    players: int | None = None


class CompetitiveResearch(BaseModel):
    schema_version: Literal[1]
    source: Literal['limitless-main']
    source_label: Literal['Limitless']
    functional_id: str
    window: Window
    status: Literal['observed','format_unavailable','mapping_failure','source_failure','no_data']
    format_available: bool
    format_start: str | None
    period_start: str | None
    period_end: str
    sample_size: int
    included_decks: int
    usage_percent: float | None
    average_copies: float | None
    copy_distribution: list[CopyBucket]
    archetypes: list[Archetype]
    top_archetypes: list[Archetype]
    associated_cards: list[AssociatedCard]
    association_status: Literal['observed','insufficient_sample','no_qualifying_pairs']
    trend: list[TrendSeries]
    tournament_count: int
    published_decklists: int
    excluded_unmapped: int
    results_without_lists: int
    last_updated: str | None
    source_error: str | None
    provenance: list[Provenance]
    parser_version: str
