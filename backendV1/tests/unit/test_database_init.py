"""Unit tests for automatic PostgreSQL database initialization on deployment."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asyncpg.exceptions import InvalidCatalogNameError

from qnu.platform import database_init


class MockAsyncContext:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.mark.asyncio
async def test_ensure_database_exists_when_already_ready():
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    
    mock_engine = MagicMock()
    mock_engine.connect.return_value = MockAsyncContext(mock_conn)
    mock_engine.dispose = AsyncMock()

    with patch("qnu.platform.database_init.create_async_engine", return_value=mock_engine):
        status = await database_init.ensure_database_exists()
        assert status == 0


@pytest.mark.asyncio
async def test_ensure_database_exists_creates_when_missing():
    # 1. Target probe fails with InvalidCatalogNameError
    probe_engine = MagicMock()
    probe_engine.connect.side_effect = InvalidCatalogNameError("database does not exist")
    probe_engine.dispose = AsyncMock()

    # 2. Maintenance connects and runs CREATE DATABASE
    maint_conn = AsyncMock()
    mock_scalar = MagicMock()
    mock_scalar.scalar.return_value = None
    maint_conn.execute = AsyncMock(return_value=mock_scalar)

    maint_engine = MagicMock()
    maint_engine.connect.return_value = MockAsyncContext(maint_conn)
    maint_engine.dispose = AsyncMock()

    def mock_create_engine(url, **kwargs):
        if url.database == "postgres":
            return maint_engine
        return probe_engine

    with patch("qnu.platform.database_init.create_async_engine", side_effect=mock_create_engine):
        status = await database_init.ensure_database_exists()
        assert status == 0
        assert maint_conn.execute.call_count >= 2
