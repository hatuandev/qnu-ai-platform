#!/usr/bin/env bash
set -euo pipefail
MAKE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$MAKE_ROOT/backendV1/.venv/bin/python" ]]; then
  RUNNER_PYTHON="$MAKE_ROOT/backendV1/.venv/bin/python"
elif [[ -f "$MAKE_ROOT/backendV1/.venv/Scripts/python.exe" ]]; then
  RUNNER_PYTHON="$MAKE_ROOT/backendV1/.venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
  RUNNER_PYTHON=python3
else
  RUNNER_PYTHON=python
fi
exec "$RUNNER_PYTHON" "$MAKE_ROOT/scripts/run_v1.py" "$@"
