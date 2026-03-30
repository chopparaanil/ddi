#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"

UV_BIN=${UV_BIN:-}
if [[ -z "$UV_BIN" ]]; then
    if command -v uv >/dev/null 2>&1; then
        UV_BIN=$(command -v uv)
    elif [[ -x "/dd/home/balajid/.local/bin/uv" ]]; then
        UV_BIN="/dd/home/balajid/.local/bin/uv"
    else
        echo "uv is required but was not found in PATH or /dd/home/balajid/.local/bin/uv." >&2
        exit 1
    fi
fi

exec "$UV_BIN" run python main.py
