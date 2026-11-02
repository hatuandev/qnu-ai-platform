FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN useradd --create-home --uid 10001 qnu \
 && mkdir -p /app/storage \
 && chown qnu:qnu /app/storage

COPY pyproject.toml uv.lock README.md ./
COPY qnu ./qnu
COPY alembic ./alembic
COPY alembic.ini ./

RUN uv sync --frozen --no-dev --no-editable

USER qnu
EXPOSE 8002
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8002/health/live', timeout=3)"

CMD ["uvicorn", "qnu.main:app", "--host", "0.0.0.0", "--port", "8002"]
