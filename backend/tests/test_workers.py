"""Unit Tests for Real ARQ Background Tasks (ingestion, reindex, export)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.workers.tasks as tasks_module
from app.workers.arq_worker import WorkerSettings
from app.workers.tasks import (
    task_document_ingestion,
    task_export_document,
    task_reindex_collection,
)


def _session_factory(mock_session: AsyncMock):
    """Patch target replacing AsyncSessionFactory with an async CM factory."""
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=mock_cm)


def _execute_result(scalar=None, scalars_list=None):
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=scalar)
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=scalars_list or [])
    result.scalars = MagicMock(return_value=scalars)
    return result


def _fresh_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_task_document_ingestion_happy_path():
    job = SimpleNamespace(
        id="job_1", status="queued", document_id="doc_1",
        collection_id="col_1", payload={},
    )
    doc = SimpleNamespace(id="doc_1", collection_id="col_1", file_name="a.pdf", storage_path="u/a.pdf")
    collection = SimpleNamespace(module_code="admissions")
    session = _fresh_session()
    session.execute = AsyncMock(return_value=_execute_result(scalar=job))

    with (
        patch.object(tasks_module, "AsyncSessionFactory", _session_factory(session)),
        patch.object(tasks_module.knowledge_service, "get_document", new=AsyncMock(return_value=doc)),
        patch.object(tasks_module.knowledge_service, "get_collection", new=AsyncMock(return_value=collection)),
        patch.object(
            tasks_module.knowledge_service, "prepare_ingestion",
            new=AsyncMock(return_value={"parsed": None}),
        ),
        patch.object(
            tasks_module.knowledge_service, "replace_document_content",
            new=AsyncMock(return_value=7),
        ),
        patch.object(tasks_module.storage_service, "get", new=AsyncMock(return_value=b"%PDF")),
    ):
        res = await task_document_ingestion({}, "job_1")

    assert res["status"] == "completed"
    assert res["indexed_chunks"] == 7
    assert res["document_id"] == "doc_1"
    assert job.status == "completed"


@pytest.mark.asyncio
async def test_task_document_ingestion_missing_job():
    session = _fresh_session()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))
    with patch.object(tasks_module, "AsyncSessionFactory", _session_factory(session)):
        res = await task_document_ingestion({}, "job_missing")
    assert res["status"] == "failed"


@pytest.mark.asyncio
async def test_task_document_ingestion_cooperative_cancel():
    running = SimpleNamespace(
        id="job_2", status="running", document_id="doc_1",
        collection_id="col_1", payload={},
    )
    cancelled = SimpleNamespace(
        id="job_2", status="cancelled", document_id="doc_1",
        collection_id="col_1", payload={},
    )
    doc = SimpleNamespace(id="doc_1", collection_id="col_1", file_name="a.pdf", storage_path="u/a.pdf")
    collection = SimpleNamespace(module_code="admissions")
    session = _fresh_session()
    session.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=running),
            _execute_result(scalar=running),
            _execute_result(scalar=cancelled),
        ]
    )
    with (
        patch.object(tasks_module, "AsyncSessionFactory", _session_factory(session)),
        patch.object(tasks_module.knowledge_service, "get_document", new=AsyncMock(return_value=doc)),
        patch.object(tasks_module.knowledge_service, "get_collection", new=AsyncMock(return_value=collection)),
        patch.object(tasks_module.storage_service, "get", new=AsyncMock(return_value=b"%PDF")),
        patch.object(
            tasks_module.knowledge_service, "prepare_ingestion",
            new=AsyncMock(return_value={"parsed": None}),
        ),
    ):
        res = await task_document_ingestion({}, "job_2")
    assert res["status"] == "cancelled"


@pytest.mark.asyncio
async def test_task_reindex_collection_happy_path():
    job = SimpleNamespace(id="job_3", status="queued", collection_id="col_1", payload={})
    chunks = [
        SimpleNamespace(id="chk_1", content="a", document_id="d1", section=None, page_number=1, chunk_metadata={}),
        SimpleNamespace(id="chk_2", content="b", document_id="d1", section=None, page_number=1, chunk_metadata={}),
    ]
    session = _fresh_session()
    session.execute = AsyncMock(
        side_effect=[
            _execute_result(scalar=job),
            _execute_result(scalars_list=chunks),
            _execute_result(scalar=job),
        ]
    )
    with (
        patch.object(tasks_module, "AsyncSessionFactory", _session_factory(session)),
        patch(
            "app.modules.rag.vector_indexer.vector_indexer.index_chunks",
            new=AsyncMock(return_value=2),
        ),
    ):
        res = await task_reindex_collection({}, "job_3")
    assert res["status"] == "completed"
    assert res["points_reindexed"] == 2
    assert res["total_chunks"] == 2


@pytest.mark.asyncio
async def test_task_export_document_renders_real_docx():
    session = _fresh_session()
    session.execute = AsyncMock(return_value=_execute_result(scalar=None))
    with (
        patch.object(tasks_module, "AsyncSessionFactory", _session_factory(session)),
        patch.object(tasks_module.storage_service, "save", new=AsyncMock()) as mock_save,
    ):
        res = await task_export_document(
            {}, job_id="job_789", document_type="THONG_BAO",
            title="Ke hoach", body_paragraphs=["Noi dung 1"],
        )
    assert res["status"] == "completed"
    assert res["output_file"] == "exports/THONG_BAO_job_789.docx"
    saved_bytes = mock_save.await_args.args[1]
    assert saved_bytes[:2] == b"PK"  # real OOXML zip payload


def test_worker_settings():
    assert len(WorkerSettings.functions) == 3
    assert WorkerSettings.job_timeout == 300
    assert WorkerSettings.max_retries == 3
