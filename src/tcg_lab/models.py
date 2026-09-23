from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
CardId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9.-]{0,79}$")]
Format = Literal["standard", "expanded", "unlimited"]


class DeckEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    card_id: CardId
    count: Annotated[int, Field(strict=True, ge=1, le=60)]


class Deck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Label
    version: Label
    format: Format = "standard"
    cards: Annotated[list[DeckEntry], Field(min_length=1, max_length=100)]
    notes: Annotated[str, Field(max_length=4000)] = ""

    def counts(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for entry in self.cards:
            result[entry.card_id] = result.get(entry.card_id, 0) + entry.count
        return result
