#!/bin/bash
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Python 3.11+ is required to stop this launch safely. Install Python from python.org.' >&2
  exit 1
fi
exec python3 "$ROOT/scripts/local-web.py" stop "$@"
