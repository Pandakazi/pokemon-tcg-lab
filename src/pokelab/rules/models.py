"""Versioned contracts for isolated scenarios, not persistent matches."""
from hashlib import sha256
from typing import Annotated, Literal
import json

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Key = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=120)]
Digest = Annotated[str, StringConstraints(strict=True, pattern=r'^[a-f0-9]{64}$')]
Count = Annotated[int, Field(strict=True, ge=0)]
Status = Literal['SUPPORTED_LEGAL', 'SUPPORTED_ILLEGAL', 'NEEDS_CHOICE',
                 'INSUFFICIENT_INFORMATION', 'UNSUPPORTED']
Support = Literal['REVIEWED', 'UNKNOWN', 'UNREVIEWED', 'STALE', 'MISSING_EVIDENCE', 'VERSION_MISMATCH']


def digest(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    @model_validator(mode='before')
    @classmethod
    def integer_schema_version(cls, value):
        if isinstance(value, dict) and 'schema_version' in value and type(value['schema_version']) is not int:
            raise ValueError('schema_version must be an integer, not a coerced value.')
        return value


class Ruleset(StrictModel):
    id: Key
    version: Key
    language: Literal['en'] = 'en'
    jurisdiction: Literal['international'] = 'international'
    game: Literal['physical-tcg'] = 'physical-tcg'
    scope: Literal['isolated-interactions'] = 'isolated-interactions'
    # An implementation scope pin, not an assertion of an official rulebook edition.
    effective_date: str | None = None


class Evidence(StrictModel):
    id: Key
    kind: Literal['CARD_TEXT', 'OFFICIAL_GAME_RULE', 'OFFICIAL_CARD_RULING', 'ERRATA', 'POKELAB_INTERPRETATION']
    reference: str = Field(min_length=1)
    field_path: str = Field(min_length=1)
    content: str = Field(min_length=1)
    content_hash: Digest
    retrieved_at: str | None = None
    published_at: str | None = None
    effective_from: str | None = None
    applicability: str = Field(min_length=1)


class ProfileRef(StrictModel):
    id: Key
    version: Key


class MechanicProfile(StrictModel):
    schema_version: Literal[1] = 1
    ref: ProfileRef
    ruleset: Ruleset
    printing_id: Key
    functional_id: Key
    source_fingerprint: Digest
    fingerprint_version: Literal['mechanics-v1'] = 'mechanics-v1'
    handler: Key
    handler_version: Key
    review_status: Literal['REVIEWED', 'UNREVIEWED', 'STALE']
    reviewed_by: str | None = None
    review_note: str | None = None
    evidence: tuple[Evidence, ...] = ()
    scope: Literal['switch-effect-only', 'printed-damage-preview', 'ultra-ball-effect-only', 'evidence-gathering-only']
    limitations: tuple[str, ...]


class ProfileResolution(StrictModel):
    support: Support
    profile: MechanicProfile | None = None
    reason: str
    actual_fingerprint: Digest | None = None


class Location(StrictModel):
    player: Key
    zone: Literal['active', 'bench', 'resolving', 'hand', 'discard', 'deck']
    position: Annotated[int, Field(strict=True, ge=0, le=199)] = 0

    @model_validator(mode='after')
    def active_slot(self):
        if self.zone == 'active' and self.position != 0:
            raise ValueError('Active has one slot at position 0.')
        return self


class CardInstance(StrictModel):
    id: Key
    owner: Key
    controller: Key
    functional_id: Key
    printing_id: Key
    profile: ProfileRef | None = None
    location: Location


class Usage(StrictModel):
    turn: Key
    player: Key
    effect: Key
    scope: Literal['instance', 'player', 'named-effect']
    instance: Key | None = None

    @model_validator(mode='after')
    def scope_key(self):
        if (self.scope == 'instance') != (self.instance is not None):
            raise ValueError('Only instance-scoped usage requires an instance.')
        return self


class Scenario(StrictModel):
    schema_version: Literal[1] = 1
    ruleset: Ruleset
    revision: Count
    players: tuple[Key, Key]
    turn_player: Key
    instances: tuple[CardInstance, ...] = Field(max_length=200)
    # Mandatory caller-supplied boundary. None means dependencies were not assessed.
    unresolved_dependencies: tuple[Key, ...] | None
    isolation_confirmed: bool = Field(strict=True)
    # Caller-owned turn token. No automatic turn progression/reset is inferred.
    turn: Key | None = None
    usage: tuple[Usage, ...] = ()

    @model_validator(mode='after')
    def consistent(self):
        if len(set(self.players)) != 2 or self.turn_player not in self.players:
            raise ValueError('Scenario requires two distinct players and a valid turn owner.')
        ids, slots = set(), set()
        for card in self.instances:
            if card.id in ids:
                raise ValueError('Duplicate card instance ID.')
            ids.add(card.id)
            if any(p not in self.players for p in (card.owner, card.controller, card.location.player)):
                raise ValueError('Unknown player reference.')
            slot = (card.location.player, card.location.zone, card.location.position)
            if slot in slots:
                raise ValueError('Two instances occupy the same location.')
            slots.add(slot)
        usage_keys = set()
        for entry in self.usage:
            if entry.player not in self.players or (entry.instance is not None and entry.instance not in ids):
                raise ValueError('Invalid usage reference.')
            key = (entry.turn, entry.player, entry.effect, entry.scope, entry.instance)
            if key in usage_keys:
                raise ValueError('Duplicate usage entry.')
            usage_keys.add(key)
        return self

    def state_hash(self) -> str:
        value = self.model_dump(mode='json')
        value['instances'] = sorted(value['instances'], key=lambda c: c['id'])
        # Preserve A/B hashes when the additive C context is absent.
        if self.turn is None and not self.usage:
            value.pop('turn')
            value.pop('usage')
        else:
            value['usage'] = sorted(value['usage'], key=lambda u: (u['turn'], u['player'], u['effect'], u['scope'], u['instance'] or ''))
        return digest(value)


class Choices(StrictModel):
    payment: tuple[Key, ...] | None = None
    search: Key | None = None
    # Trusted resolver input, never an exposed deck-order choice for a player.
    shuffle: tuple[Key, ...] | None = None
    exchange: Key | None = None


class Choice(StrictModel):
    id: Literal['payment', 'search', 'shuffle', 'exchange']
    kind: Literal['cost', 'search', 'resolution', 'exchange']
    cardinality: Count
    candidates: tuple[Key, ...]
    supplied: tuple[Key, ...] | None = None
    constraint: str
    rejection: str | None = None


class Action(StrictModel):
    schema_version: Literal[1] = 1
    profile: ProfileRef
    actor: Key
    source: Key
    target: Key | None = None
    expected_revision: Count
    expected_state_hash: Digest
    choices: Choices = Choices()


class Check(StrictModel):
    code: Key
    message: str


class Move(StrictModel):
    instance: Key
    before: Location
    after: Location


class Step(StrictModel):
    phase: Literal['cost', 'effect']
    operation: Literal['discard', 'search', 'reveal', 'move-to-hand', 'shuffle', 'exchange', 'record-usage']
    instances: tuple[Key, ...] = ()


class Delta(StrictModel):
    base_revision: Count
    base_hash: Digest
    next_revision: Count
    moves: tuple[Move, ...]
    steps: tuple[Step, ...] = ()
    usage_added: tuple[Usage, ...] = ()


class DamagePreview(StrictModel):
    attack: Key
    printed_damage: Count
    printed_energy_cost: tuple[Key, ...]
    target: Key
    executable: Literal[False] = False
    scope: Literal['printed-base-only'] = 'printed-base-only'


class Evaluation(StrictModel):
    schema_version: Literal[1] = 1
    action: Action
    ruleset: Ruleset
    state_revision: Count
    state_hash: Digest
    status: Status
    support: Support
    scope: str
    checks: tuple[Check, ...] = ()
    legal_targets: tuple[Key, ...] = ()
    required_choices: tuple[str, ...] = ()
    choices: tuple[Choice, ...] = ()
    missing_information: tuple[str, ...] = ()
    unsupported_dependencies: tuple[str, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    interpretation: ProfileRef | None = None
    handler_version: str | None = None
    limitations: tuple[str, ...] = ()
    delta: Delta | None = None
    preview: DamagePreview | None = None


class ApplyResult(StrictModel):
    applied: bool
    evaluation: Evaluation
    state: Scenario
