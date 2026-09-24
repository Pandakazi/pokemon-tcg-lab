"""Optional development CLI; the desktop has its own Refresh Limitless button."""
import argparse
import json
from pokelab.engine import PokeLabEngine
from pokelab.analytics import Analytics, LimitlessClient

parser = argparse.ArgumentParser()
parser.add_argument("--db", required=True)
parser.add_argument("--events", type=int, default=100)
parser.add_argument("--days", type=int, default=90)
args = parser.parse_args()
engine = PokeLabEngine(args.db)
engine.rebuild_identities()
print(json.dumps(LimitlessClient().refresh(Analytics(engine), days=args.days, max_events=args.events), indent=2))
