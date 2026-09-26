#!/bin/bash
set -euo pipefail

echo "=========================================================="
echo "  QNU.AI Platform — Backend Runtime"
echo "=========================================================="

echo "Starting QNU.AI Platform process..."
if [ "$#" -gt 0 ]; then
    exec "$@"
else
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8001}" --workers "${WORKERS:-4}"
fi
