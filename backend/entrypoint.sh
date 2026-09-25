#!/bin/bash
set -e

echo "=========================================================="
echo "  QNU.AI Platform — Backend Production Bootstrapper"
echo "=========================================================="

# 1. Database readiness check & migrations
echo "==> [1/3] Checking PostgreSQL & Running Migrations..."
python -m app.cli db migrate

# 2. Idempotent Data Seeding
# Seeds 05 official assistants, 05 workflow DAGs, Decree 30 taxonomy,
# default facts, and model defaults. Also verifies Qdrant collections & MinIO bucket.
if [ "${AUTO_SEED:-true}" = "true" ]; then
    echo "==> [2/3] Seeding Initial Platform Data (Workflows, Assistants, Knowledge, Taxonomy)..."
    python -m app.cli db seed --all
else
    echo "==> [2/3] Skipping Auto-Seed (AUTO_SEED is set to false)."
fi

# 3. Launch application or custom command
echo "==> [3/3] Starting QNU.AI Platform Engine..."
if [ "$#" -gt 0 ]; then
    exec "$@"
else
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8001}" --workers "${WORKERS:-4}"
fi
