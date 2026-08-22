#!/bin/sh

set -eu

SCRIPT_DIRECTORY=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIRECTORY"

for PYTHON_COMMAND in python3.14 python3.13 python3.12 python3.11 python3; do
    if command -v "$PYTHON_COMMAND" >/dev/null 2>&1 \
        && "$PYTHON_COMMAND" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' \
            >/dev/null 2>&1; then
        exec "$PYTHON_COMMAND" -m projects.bootstrap "$@"
    fi
done

echo "Python 3.11 oder neuer wurde nicht gefunden."
echo "Python 3.11 or newer was not found."
exit 2
