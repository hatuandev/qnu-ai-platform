# Narrow, disposable Ubuntu compatibility harness; no live volumes or services.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 ENVIRONMENT=test STORAGE_DRIVER=local
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /venv \
    && /venv/bin/pip install --no-cache-dir pytest pytest-asyncio fastapi pydantic-settings 'sqlalchemy[asyncio]' asyncpg httpx structlog cryptography PyJWT redis
ENV PATH="/venv/bin:$PATH"
RUN pip install --no-cache-dir bcrypt arq boto3
WORKDIR /verify
COPY backend/app/ ./app/
COPY backend/tests/conftest.py backend/tests/test_backup_launcher.py backend/tests/test_backups.py backend/tests/test_backup_phase2.py ./tests/
CMD ["python", "-m", "pytest", "tests/test_backup_launcher.py", "tests/test_backups.py", "tests/test_backup_phase2.py", "-q", "--basetemp=/tmp/qnu-backup-424"]
