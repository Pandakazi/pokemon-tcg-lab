"""Immutable, provider-free evidence contracts. No execution or transport types."""
from datetime import date
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field


class Frozen(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class Request(Frozen):
    question: str = Field(min_length=1, max_length=2000)
    intent: Literal['selected_card_research'] = 'selected_card_research'
    printing: str = Field(min_length=1, max_length=100)
    variant: str | None = Field(None, min_length=1, max_length=100)
    archetype: str | None = Field(None, max_length=100)
    observation: str | None = Field(None, max_length=100)
    include_composite: bool = False
    window: Literal['7','30','90','format'] = '30'
    as_of: date


class FieldValue(Frozen):
    field: str
    value: str


class CardFacts(Frozen):
    kind: Literal['card'] = 'card'
    printing: str
    functional_id: str
    deck_identity: str
    name: str
    printed: tuple[FieldValue, ...]


class DeckFacts(Frozen):
    kind: Literal['deck'] = 'deck'
    revision: int
    content_hash: str
    dirty: bool
    total: int
    categories: tuple[FieldValue, ...]
    validation_state: str
    reasons: tuple[str, ...]
    unknown: tuple[str, ...]
    limitations: tuple[str, ...]
    selected_quantity: int
    functional_entries: int


class OwnedFinish(Frozen):
    finish: str
    quantity: int


class OwnershipFacts(Frozen):
    kind: Literal['ownership'] = 'ownership'
    printing: str
    functional_id: str
    functional_total: int
    exact: tuple[OwnedFinish, ...]


class ArchetypeFact(Frozen):
    id: str
    name: str
    included: int
    eligible: int
    prevalence_percent: float | None
    status: str


class AssociationFact(Frozen):
    functional_id: str
    name: str
    decks: int
    cooccurrence_percent: float
    conservative_lift: float


class CompetitiveFacts(Frozen):
    kind: Literal['competitive'] = 'competitive'
    status: str
    period_start: str | None
    period_end: str
    sample_size: int
    included_decks: int
    usage_percent: float | None
    average_copies: float | None
    published_decklists: int
    excluded_unmapped: int
    results_without_lists: int
    tournament_count: int
    prevalence_min_decks: int
    source_error: str | None
    distribution: tuple[FieldValue, ...]
    archetypes: tuple[ArchetypeFact, ...]
    associations: tuple[AssociationFact, ...]
    limitations: tuple[str, ...]


class ObservationFacts(Frozen):
    kind: Literal['observation'] = 'observation'
    key: str
    event: str
    date: str
    placement: int
    archetype: str
    mapped: bool
    selected_quantity: int


class CompositeFacts(Frozen):
    kind: Literal['composite'] = 'composite'
    archetype: str
    algorithm: str
    status: str
    sample_size: int
    limited_evidence: bool
    total: int
    selected_quantity: int
    reasons: tuple[str, ...]
    limitations: tuple[str, ...]


class RulesFacts(Frozen):
    kind: Literal['rules'] = 'rules'
    profile: str | None
    profile_version: str | None
    handler_version: str | None
    review_support: str
    evaluated_support: str | None = None
    status: str
    scope: str
    checks: tuple[str, ...] = ()
    required_choices: tuple[str, ...] = ()
    permitted_targets: tuple[str, ...] = ()
    preview: tuple[FieldValue, ...] = ()
    transition: tuple[str, ...] = ()
    execution_authorized: Literal[False] = False
    result_type: Literal['profile-only','scoped-transition-proposal','preview','derivation','unavailable']
    missing: tuple[str, ...] = ()
    unsupported: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


Payload = Annotated[CardFacts | DeckFacts | OwnershipFacts | CompetitiveFacts | ObservationFacts | CompositeFacts | RulesFacts,
                    Field(discriminator='kind')]


class Reference(Frozen):
    id: str
    source: str
    resource: str
    checked_at: str | None = None
    event_date: str | None = None
    url: str | None = None
    content_hash: str
    version: str | None = None
    excerpt: str | None = None


class Evidence(Frozen):
    id: str
    classification: Literal['SOURCE_FACT','DERIVED_FACT','EMPIRICAL_EVIDENCE','RULES_RESULT']
    payload: Payload
    references: tuple[str, ...]


class Coverage(Frozen):
    requested: tuple[str, ...]
    included: tuple[str, ...]
    omitted: tuple[str, ...]
    unavailable: tuple[str, ...]


class Budget(Frozen):
    cap_bytes: int
    serialized_bytes: int
    estimated_tokens: int
    estimate_method: Literal['ceil(utf8_bytes/4); approximation, not tokenizer count'] = 'ceil(utf8_bytes/4); approximation, not tokenizer count'
    evidence_count: int
    archetype_cap: Literal[3] = 3
    association_cap: Literal[5] = 5
    observation_cap: Literal[3] = 3
    rules_cap: Literal[1] = 1


class Packet(Frozen):
    schema_version: Literal[1] = 1
    builder: Literal['pokelab-agent-context-v1'] = 'pokelab-agent-context-v1'
    status: Literal['ready','partial','budget_exceeded','inconsistent_snapshot']
    request: Request
    content_hash: str
    evidence: tuple[Evidence, ...]
    references: tuple[Reference, ...]
    coverage: Coverage
    budget: Budget
