"""Bounded library HTTP contracts; source fields remain canonical in SQLite."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Category = Literal['Pokemon', 'Trainer', 'Energy']
PokemonType = Literal['Colorless','Darkness','Dragon','Fairy','Fighting','Fire','Grass','Lightning','Metal','Psychic','Water']

class LibraryQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')
    page: int = Field(1, ge=1, le=10000)
    page_size: int = Field(24, ge=1, le=50)
    include_image: bool = False
    category: Category = 'Pokemon'
    q: str = Field('', max_length=100)
    ownership: Literal['all','owned','unowned'] = 'all'
    has_ability: bool = False
    ability: list[Literal['Yes','No']] = Field(default_factory=list, max_length=2)
    pokemon_types: list[PokemonType] = Field(default_factory=list, max_length=11)
    stages: list[Literal['Basic','Stage1','Stage2']] = Field(default_factory=list, max_length=3)
    trainer_types: list[Literal['Item','Supporter','Stadium','Tool']] = Field(default_factory=list, max_length=4)
    energy_types: list[Literal['Normal','Special']] = Field(default_factory=list, max_length=2)
    regulation_marks: list[str] = Field(default_factory=list, max_length=26)

    @field_validator('pokemon_types', 'stages', 'trainer_types', 'energy_types', 'regulation_marks', 'ability', mode='before')
    @classmethod
    def empty_selections(cls, values):
        # Empty HTML/query values are an unselected family, not an SQL constraint.
        if isinstance(values, (list, tuple)):
            return list(dict.fromkeys(value for value in values if value != ''))
        return values

    @model_validator(mode='after')
    def compatible(self):
        if self.has_ability and not self.ability:
            self.ability = ['Yes']  # Backward-compatible shared URLs.
        if (self.category != 'Pokemon' and (self.pokemon_types or self.stages or self.ability)
            or self.category != 'Trainer' and self.trainer_types
            or self.category != 'Energy' and self.energy_types):
            raise ValueError('Filter family does not apply to this category')
        if any(len(v) != 1 or not 'A' <= v <= 'Z' for v in self.regulation_marks):
            raise ValueError('Regulation marks must be single uppercase letters')
        return self

class SetInfo(BaseModel):
    id: str
    name: str | None = None
    code: str | None = None

class Provenance(BaseModel):
    source: str
    checked_at: str

class Ownership(BaseModel):
    functional_id: str
    library_id: str
    variant: str
    quantity: int
    functional_total: int
    library_total: int

class QuantityWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    variant: str = Field('unspecified', min_length=1, max_length=100)
    quantity: int | None = Field(None, strict=True, ge=0, le=9999)
    delta: int | None = Field(None, strict=True, ge=-1, le=1)

    @model_validator(mode='after')
    def one_operation(self):
        if (self.quantity is None) == (self.delta is None) or self.delta == 0:
            raise ValueError('Provide quantity or delta (-1 or 1), not both.')
        return self

class Preference(BaseModel):
    model_config = ConfigDict(extra='forbid')
    printing_id: str = Field(min_length=1, max_length=100)
    variant: str = Field('unspecified', min_length=1, max_length=100)

class CardSummary(BaseModel):
    id: str
    name: str
    category: Category
    localId: str | int
    set: SetInfo
    hp: int | None = None
    types: list[str] | None = None
    stage: str | None = None
    suffix: str | None = None
    rarity: str | None = None
    trainerType: str | None = None
    energyType: str | None = None
    regulationMark: str | None = None
    legal: dict[str, bool] = Field(default_factory=dict)
    game: str | None = None
    image_url: str | None = None
    legality_provenance: Provenance
    ownership: Ownership | None = None

class VariationPage(BaseModel):
    cards: list[CardSummary]
    total: int
    page: int
    page_size: int
    next_page: int | None

class SyncStatus(BaseModel):
    status: str
    finished_at: str | None = None
    missing: int | None = None

class FilterOption(BaseModel):
    parameter: str
    label: str
    values: list[str]

class CardPage(BaseModel):
    cards: list[CardSummary]
    page: int
    page_size: int
    total: int
    next_page: int | None
    scope: str
    sync: SyncStatus
    filter_options: list[FilterOption]

class Ability(BaseModel):
    type: str | None = None
    name: str | None = None
    effect: str | None = None

class Attack(BaseModel):
    name: str | None = None
    cost: list[str] = Field(default_factory=list)
    damage: str | int | None = None
    effect: str | None = None

class Modifier(BaseModel):
    type: str
    value: str | int | None = None

class CardText(CardSummary):
    abilities: list[Ability] = Field(default_factory=list)
    attacks: list[Attack] = Field(default_factory=list)
    effect: str | None = None
    description: str | None = None
    rules: list[str] = Field(default_factory=list)
    weaknesses: list[Modifier] = Field(default_factory=list)
    resistances: list[Modifier] = Field(default_factory=list)
    retreat: int | None = None
    evolveFrom: str | None = None
    illustrator: str | None = None

class CardDetail(BaseModel):
    card: CardText
    source: str
    fetched_at: str
    checked_at: str
    live: bool
    game: str

class Status(BaseModel):
    app: str
    ready: bool
    source: str
    cards: int
    sync: SyncStatus
