# ==============================================================================
# QNU.AI Platform — Backend Production Dockerfile
# Python 3.12-slim runtime with UV package manager, Liberation Serif fonts (NĐ 30),
# PyMuPDF C-dependencies, non-root user and automated healthchecks.
# ==============================================================================

# Stage 1: Fast & Reliable UV Binary Extraction
FROM ghcr.io/astral-sh/uv:0.11.16@sha256:440fd6477af86a2f1b38080c539f1672cd22acb1b1a47e321dba5158ab08864d AS uv_bin

# Match the PostgreSQL 16 infrastructure; no Docker socket is needed for dumps.
FROM postgres:16-bookworm@sha256:0ea6700a3b4f0ae6ce746519073558aed4d88a79d8d07622a9a644946c7319c4 AS pg_tools

# Stage 2: Final Production Runtime Image
FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258

# Prevent Python from writing .pyc files and force unbuffered output for real-time logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_HTTP_TIMEOUT=300 \
    UV_CONCURRENT_DOWNLOADS=2 \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app

# 1. Install required system packages:
# - curl: for container healthchecks
# - fontconfig & fonts-liberation: metric-compatible Times New Roman required for Decree 30/2020/NĐ-CP documents
# - ca-certificates: secure HTTPS outbound calls to OpenAI/Gemini APIs
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    fontconfig \
    fonts-liberation \
    libgl1 \
    libglib2.0-0 \
    libpq5 \
    liblz4-1 \
    libzstd1 \
 && rm -rf /var/lib/apt/lists/* \
 && fc-cache -f > /dev/null

# 2. Copy UV package manager binary from official Astral image
COPY --from=uv_bin /uv /uvx /bin/
COPY --from=pg_tools /usr/lib/postgresql/16/bin/pg_dump /usr/local/bin/pg_dump
COPY --from=pg_tools /usr/lib/postgresql/16/bin/pg_restore /usr/local/bin/pg_restore

# 3. Create non-privileged system user for hardened container security
RUN groupadd -g 10001 qnu \
 && useradd -u 10001 -g qnu -m -s /bin/bash qnu

WORKDIR /app

# 4. Dependency caching layer: Copy dependency manifests first.
# The production image is built from the repository root so versioned platform
# configs can be baked into the image instead of relying on a host bind mount.
COPY backend/pyproject.toml backend/uv.lock ./

# 5. Install third-party dependencies into .venv
# Fail if pyproject and the committed lock disagree. Local model runtimes are
# not installed: inference/OCR/embedding/reranking use the configured API providers.
RUN uv sync --locked --no-dev --no-install-project --no-cache

# 6. Copy application source code, migrations, entrypoint, and versioned configs
COPY backend/app/ ./app
COPY backend/alembic/ ./alembic
COPY backend/alembic.ini ./alembic.ini
COPY backend/entrypoint.sh ./entrypoint.sh
COPY backend/README.md ./README.md
COPY configs/ ./configs

# 6b. Install the project from the same lock without editable source linkage.
RUN uv sync --locked --no-dev --no-editable --no-cache

# 7. Create storage directories for uploads/artifacts and set non-root ownership
RUN mkdir -p /app/storage/uploads /app/storage/artifacts /app/storage/backups \
 && sed -i 's/\r$//' /app/entrypoint.sh \
 && chmod +x /app/entrypoint.sh \
 && chown -R qnu:qnu /app/storage /app/configs

# 8. Switch to non-root user
USER qnu

# Expose FastAPI HTTP Service port
EXPOSE 8001

# Container Healthcheck Probe
HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8001/health/live || exit 1

# Runtime entrypoint only launches the requested process. Database bootstrap is
# handled by the one-shot Compose service before API and worker startup.
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command: Launch production Uvicorn server with 4 asynchronous workers
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]
