# ==============================================================================
# QNU.AI Platform — Backend Production Dockerfile
# Python 3.12-slim runtime with UV package manager, Liberation Serif fonts (NĐ 30),
# PyMuPDF C-dependencies, non-root user and automated healthchecks.
# ==============================================================================

# Stage 1: Fast & Reliable UV Binary Extraction
FROM ghcr.io/astral-sh/uv:latest AS uv_bin

# Stage 2: Final Production Runtime Image
FROM python:3.12-slim

# Prevent Python from writing .pyc files and force unbuffered output for real-time logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_HTTP_TIMEOUT=300 \
    UV_CONCURRENT_DOWNLOADS=2 \
    UV_TORCH_BACKEND=cpu \
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
 && rm -rf /var/lib/apt/lists/* \
 && fc-cache -f > /dev/null || true

# 2. Copy UV package manager binary from official Astral image
COPY --from=uv_bin /uv /uvx /bin/

# 3. Create non-privileged system user for hardened container security
RUN groupadd -g 10001 qnu \
 && useradd -u 10001 -g qnu -m -s /bin/bash qnu

WORKDIR /app

# 4. Dependency caching layer: Copy dependency manifests first
COPY pyproject.toml uv.lock* ./

# 5. Install third-party dependencies into .venv
# Pre-install official CPU-only PyTorch (~180MB) instead of multi-gigabyte CUDA binaries (>5GB)
# Then install remaining dependencies from standard PyPI with unsafe-best-match strategy
RUN uv venv /app/.venv \
 && uv pip install --no-cache --find-links https://download.pytorch.org/whl/cpu torch torchvision \
 && (uv pip install --no-cache --index-strategy unsafe-best-match -r pyproject.toml --python /app/.venv/bin/python || \
     (echo "Retrying dependency install (attempt 2)..." && sleep 5 && uv pip install --no-cache --index-strategy unsafe-best-match -r pyproject.toml --python /app/.venv/bin/python) || \
     (echo "Retrying dependency install (attempt 3)..." && sleep 10 && uv pip install --no-cache --index-strategy unsafe-best-match -r pyproject.toml --python /app/.venv/bin/python))

# 6. Copy application source code, migrations, and entrypoint
COPY app/ ./app
COPY alembic/ ./alembic
COPY alembic.ini ./alembic.ini
COPY entrypoint.sh ./entrypoint.sh
COPY README.md ./README.md

# 6b. Install project package in editable mode without re-fetching dependencies
RUN uv pip install -e . --no-deps --python /app/.venv/bin/python

# 7. Create storage directories for uploads/artifacts and set non-root ownership
RUN mkdir -p /app/storage/uploads /app/storage/artifacts /app/storage/backups /app/configs \
 && chmod +x /app/entrypoint.sh \
 && chown -R qnu:qnu /app/storage /app/configs

# 8. Switch to non-root user
USER qnu

# Expose FastAPI HTTP Service port
EXPOSE 8001

# Container Healthcheck Probe
HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8001/health/live || exit 1

# Entrypoint automatically checks DB, runs migrations & seeds initial data
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command: Launch production Uvicorn server with 4 asynchronous workers
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]
