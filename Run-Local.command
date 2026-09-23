#!/bin/bash
# macOS built-in Bash: Intel and Apple Silicon. No Homebrew required.
set -u
cd -- "$(dirname -- "$0")" || exit 1
for python in "$PWD/.venv/bin/python" python3 /usr/local/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/3.11/bin/python3; do
    if command -v "$python" >/dev/null 2>&1 && \
        "$python" -c 'import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (4,0) else 1)' 2>/dev/null; then
        exec "$python" "$PWD/scripts/launcher.py" "$@"
    fi
done
printf '%s\n' 'Python 3.11 or newer was not found.' \
    'Install the macOS universal2 Python 3 installer from https://www.python.org/downloads/macos/' \
    'Then reopen Terminal and follow the macOS steps in README.md. Homebrew is not needed.'
exit 1
