"""Readable player-facing text, independent of Qt widgets."""


def card_text(card: dict) -> str:
    lines = [card["name"], f"{card.get('set', {}).get('name', '')} • {card.get('localId', '')}", ""]
    if card.get("hp"):
        lines.append(f"HP {card['hp']} • {', '.join(card.get('types', []))} • {card.get('stage', '')}")
    for ability in card.get("abilities", []):
        lines.extend(["", f"{ability.get('type', 'Ability')}: {ability.get('name', '')}", ability.get("effect", "")])
    for attack in card.get("attacks", []):
        lines.extend(["", f"{attack.get('name', '')}   {attack.get('damage', '')}",
                      "Cost: " + ", ".join(attack.get("cost", [])), attack.get("effect", "")])
    if card.get("effect"):
        lines.extend(["", card["effect"]])
    for key, label in (("trainerType", "Trainer type"), ("energyType", "Energy type"), ("regulationMark", "Regulation mark"), ("retreat", "Retreat cost")):
        if key in card:
            lines.append(f"{label}: {card[key]}")
    for key in ("weaknesses", "resistances"):
        if card.get(key):
            lines.append(key.title() + ": " + ", ".join(f"{v.get('type','')} {v.get('value','')}" for v in card[key]))
    legal = card.get("legal", {}).get("standard")
    lines.extend(["", "TCGdex Standard flag: " + ("Legal" if legal is True else "Not legal" if legal is False else "Unknown"), f"Printing: {card['id']}"])
    return "\n".join(str(line) for line in lines)


def deck_text(deck: dict) -> str:
    lines = []
    for category in ("pokemon", "trainer", "energy"):
        lines.append(category.title())
        for card in deck.get(category, []):
            lines.append(f"{card['count']} × {card['name']} ({card.get('set','')} {card.get('number','')})")
        lines.append("")
    return "\n".join(lines)
