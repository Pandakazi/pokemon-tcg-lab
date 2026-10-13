#!/bin/bash
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Python 3.11+ is required. Install Python from python.org, reopen Terminal, then rerun setup.' >&2
  exit 1
fi
if ! python3 -c 'import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (4,0) else 1)'; then
  echo 'Python 3.11+ is required. Install Python from python.org, reopen Terminal, then rerun setup.' >&2
  exit 1
fi
exec python3 "$ROOT/scripts/local-web.py" setup "$@"
