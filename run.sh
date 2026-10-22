#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VENV_DIR="$PROJECT_DIR/.venv"
INSTALL_STAMP="$VENV_DIR/.dash-browser-install-stamp"

case "$(uname -s)" in
    Linux) ;;
    *)
        printf '%s\n' "Dash Browser's source launcher is currently supported on Linux only." >&2
        exit 1
        ;;
esac

if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' "Python 3.10 or newer is required. Install Python 3 and try again." >&2
    exit 1
fi

if [ ! -x "$VENV_DIR/bin/dash-browser" ] || \
   [ ! -f "$INSTALL_STAMP" ] || \
   [ "$PROJECT_DIR/pyproject.toml" -nt "$INSTALL_STAMP" ]; then
    if [ ! -x "$VENV_DIR/bin/python" ] && ! python3 -m venv "$VENV_DIR"; then
        printf '%s\n' "Could not create .venv. Install your OS's Python venv package and retry." >&2
        exit 1
    fi
    if ! "$VENV_DIR/bin/python" -m pip install -e "$PROJECT_DIR"; then
        printf '%s\n' "Dash Browser setup failed. Check the error above and the README troubleshooting steps." >&2
        exit 1
    fi
    if ! touch "$INSTALL_STAMP"; then
        printf '%s\n' "Could not record the completed setup in .venv." >&2
        exit 1
    fi
fi

exec "$VENV_DIR/bin/dash-browser" "$@"
