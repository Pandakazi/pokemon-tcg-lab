#!/bin/bash
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [ ! -x "$ROOT/.venv/bin/python" ]; then
  echo 'Setup is required first. Run bash setup.sh, then bash start.sh.' >&2
  exit 1
fi
exec "$ROOT/.venv/bin/python" "$ROOT/scripts/local-web.py" start "$@"
