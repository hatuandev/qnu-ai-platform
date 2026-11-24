FROM python:3.12-slim-bookworm

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && curl --fail --silent --show-error --location \
      https://www.postgresql.org/media/keys/ACCC4CF8.asc \
      --output /usr/share/keyrings/postgresql.asc \
 && echo 'deb [signed-by=/usr/share/keyrings/postgresql.asc] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main' \
      > /etc/apt/sources.list.d/pgdg.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends postgresql-client-16 \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_HTTP_TIMEOUT=120 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN useradd --create-home --uid 10001 qnu \
 && mkdir -p /app/storage \
 && chown qnu:qnu /app/storage

# Cache third-party dependencies independently from app source code so routine
# edits under qnu/ reuse the dependency layer instead of re-downloading packages.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY qnu ./qnu
COPY alembic ./alembic
COPY alembic.ini ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

USER qnu
EXPOSE 8002
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8002/health/live', timeout=3)"

CMD ["uvicorn", "qnu.main:app", "--host", "0.0.0.0", "--port", "8002", "--proxy-headers"]
