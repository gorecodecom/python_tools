#!/bin/sh

SCRIPT_DIRECTORY=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec /bin/sh "$SCRIPT_DIRECTORY/python-tools.sh" "$@"
