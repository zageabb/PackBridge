#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${PACKBRIDGE_VENV:-$ROOT/.venv}"

if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
fi

"$VENV/bin/pip" install -q -r "$ROOT/requirements.txt"
exec "$VENV/bin/python" "$ROOT/app.py"
