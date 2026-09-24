"""Shared exact-variation quantity semantics for the frozen Qt and web clients."""

COLLECTION_SCHEMA = """CREATE TABLE IF NOT EXISTS collection (
    printing_id TEXT NOT NULL, variant TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK(quantity >= 0 AND quantity <= 9999),
    PRIMARY KEY(printing_id, variant))"""


def validate_quantity(variant, quantity):
    if type(quantity) is not int or not 0 <= quantity <= 9999 or not variant or len(variant) > 100:
        raise ValueError('Quantity must be a whole number from 0 to 9999.')


def read_quantity(db, printing_id, variant):
    row = db.execute('SELECT quantity FROM collection WHERE printing_id=? AND variant=?', (printing_id, variant)).fetchone()
    return row[0] if row else 0


def write_quantity(db, printing_id, variant, quantity):
    validate_quantity(variant, quantity)
    db.execute('INSERT INTO collection VALUES (?,?,?) ON CONFLICT(printing_id,variant) DO UPDATE SET quantity=excluded.quantity',
               (printing_id, variant, quantity))
    return quantity


def variant_names(card, saved=()):
    return list(dict.fromkeys(['unspecified', *[k for k,v in card.get('variants', {}).items() if v is True], *saved]))
