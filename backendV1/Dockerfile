FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN useradd --create-home --uid 10001 qnu

COPY pyproject.toml README.md ./
COPY qnu ./qnu
COPY alembic ./alembic
COPY alembic.ini ./

RUN pip install --upgrade pip && pip install .

USER qnu
EXPOSE 8001
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8001/health/live', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "qnu.main:app", "--host", "0.0.0.0", "--port", "8001"]
