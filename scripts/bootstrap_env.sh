#!/usr/bin/env sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
VENV_DIR="$REPO_ROOT/venv"
VENV_PYTHON="$VENV_DIR/bin/python"

python_version() {
    "$1" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'
}

is_supported_python() {
    "$1" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'
}

find_python() {
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            resolved=$(command -v "$candidate")
            if is_supported_python "$resolved"; then
                printf '%s\n' "$resolved"
                return 0
            fi
        fi
    done
    return 1
}

if [ -x "$VENV_PYTHON" ] && is_supported_python "$VENV_PYTHON"; then
    BOOTSTRAP_PYTHON="$VENV_PYTHON"
    REUSING_VENV=1
else
    if ! BOOTSTRAP_PYTHON=$(find_python); then
        echo "bootstrap_env.sh: Python 3.11+ is required, but neither repo-local ./venv/bin/python nor system python3/python is compatible." >&2
        exit 1
    fi
    REUSING_VENV=0
fi

PYTHON_VERSION=$(python_version "$BOOTSTRAP_PYTHON")
echo "Using Python $PYTHON_VERSION from $BOOTSTRAP_PYTHON"

if [ "$REUSING_VENV" -eq 1 ]; then
    echo "Reusing existing repo-local virtualenv at $VENV_DIR"
elif [ -d "$VENV_DIR" ]; then
    if [ -x "$VENV_PYTHON" ]; then
        OLD_VENV_VERSION=$(python_version "$VENV_PYTHON" || echo "unknown")
        echo "Existing repo-local virtualenv uses unsupported Python $OLD_VENV_VERSION; recreating $VENV_DIR"
    else
        echo "Existing repo-local virtualenv is incomplete; recreating $VENV_DIR"
    fi
    rm -rf "$VENV_DIR"
    "$BOOTSTRAP_PYTHON" -m venv "$VENV_DIR"
else
    echo "Creating repo-local virtualenv at $VENV_DIR"
    "$BOOTSTRAP_PYTHON" -m venv "$VENV_DIR"
fi

echo "Installing requirements from $REPO_ROOT/requirements.txt"
"$VENV_PYTHON" -m pip install -r "$REPO_ROOT/requirements.txt"

if [ ! -f "$REPO_ROOT/.env" ]; then
    echo
    echo "Next step: copy .env.example to .env and set M2C_PROJECT_ID."
    echo "Recommended: also set GOOGLE_APPLICATION_CREDENTIALS in .env."
fi

echo
echo "Bootstrap complete."
echo "Run from the repo root with:"
echo "  ./venv/bin/python -m m2c_pipeline fixtures/minimal-input.md --dry-run --translation-mode fallback"
