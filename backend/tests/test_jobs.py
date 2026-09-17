"""Unit & API Tests for Background Job Tracking (enqueue, cancel, retry, stats)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.exceptions import AppException, EntityNotFoundError
from app.main import app
from app.modules.jobs.models import JobRecord
from app.modules.jobs.service import jobs_service


def _fresh_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


def _execute_result(scalar=None, all_rows=None):
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=scalar)
    result.all = MagicMock(return_value=all_rows or [])
    return result


@pytest.mark.asyncio
async def test_enqueue_rejects_unknown_type():
    with pytest.raises(AppException) as exc_info:
        await jobs_service.enqueue_job(AsyncMock(), job_type="teleport")
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_enqueue_job_success():
    session = _fresh_session()
    session.execute = AsyncMock()
    with patch(
        "app.modules.jobs.service.enqueue_arq_job", new=AsyncMock(return_value="arq-xyz")
    ):
        job = await jobs_service.enqueue_job(
            session, job_type="reindex", collection_id="col_1"
        )
    assert isinstance(job, JobRecord)
    assert job.status == "queued"
    assert job.arq_job_id == "arq-xyz"
    assert job.collection_id == "col_1"


@pytest.mark.asyncio
async def test_enqueue_job_worker_offline_stays_queued():
    session = _fresh_session()
    session.execute = AsyncMock()
    with patch(
        "app.modules.jobs.service.enqueue_arq_job", new=AsyncMock(return_value=None)
    ):
        job = await jobs_service.enqueue_job(session, job_type="reindex")
    assert job.status == "queued"
    assert job.arq_job_id is None
    assert "offline" in (job.error or "")


@pytest.mark.asyncio
async def test_cancel_terminal_job_rejected():
    job = SimpleNamespace(id="job_1", status="completed")
    session = _fresh_session()
    session.execute = AsyncMock(return_value=_execute_result(scalar=job))
    with pytest.raises(AppException) as exc_info:
        await jobs_service.cancel_job(session, "job_1")
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_cancel_running_job():
    job = SimpleNamespace(id="job_2", status="running", error=None)
    session = _fresh_session()
    session.execute = AsyncMock(return_value=_execute_result(scalar=job))
    cancelled = await jobs_service.cancel_job(session, "job_2")
    assert cancelled.status == "cancelled"


@pytest.mark.asyncio
async def test_retry_non_failed_job_rejected():
    job = SimpleNamespace(id="job_3", status="running")
    session = _fresh_session()
    session.execute = AsyncMock(return_value=_execute_result(scalar=job))
    with pytest.raises(AppException) as exc_info:
        await jobs_service.retry_job(session, "job_3")
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_retry_failed_job_requeues():
    job = SimpleNamespace(
        id="job_4", status="failed", job_type="reindex",
        progress=100.0, error="boom", result={"a": 1},
    )
    session = _fresh_session()
    session.execute = AsyncMock(return_value=_execute_result(scalar=job))
    with patch(
        "app.modules.jobs.service.enqueue_arq_job", new=AsyncMock(return_value="arq-2")
    ):
        retried = await jobs_service.retry_job(session, "job_4")
    assert retried.status == "queued"
    assert retried.progress == 0.0
    assert retried.arq_job_id == "arq-2"


@pytest.mark.asyncio
async def test_get_missing_job_raises_404():
    session = _fresh_session()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))
    with pytest.raises(EntityNotFoundError):
        await jobs_service.get_job(session, "job_missing")


@pytest.mark.asyncio
async def test_job_stats_counts():
    session = _fresh_session()
    session.execute = AsyncMock(
        return_value=_execute_result(all_rows=[("queued", 2), ("completed", 1)])
    )
    stats = await jobs_service.get_stats(session)
    assert stats == {
        "total": 3, "queued": 2, "running": 0,
        "completed": 1, "failed": 0, "cancelled": 0,
    }


@pytest.mark.asyncio
async def test_api_enqueue_and_list_jobs():
    mock_session = _fresh_session()
    mock_session.execute = AsyncMock(return_value=_execute_result(scalar=None))

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch(
            "app.modules.jobs.service.enqueue_arq_job", new=AsyncMock(return_value="arq-9")
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                created = await ac.post(
                    "/platform/v1alpha1/jobs",
                    json={"job_type": "reindex", "collection_id": "col_1"},
                )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert created.status_code == 200
    data = created.json()
    assert data["job_type"] == "reindex"
    assert data["status"] == "queued"
    assert data["arq_job_id"] == "arq-9"
