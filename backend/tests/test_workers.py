"""Unit Tests for ARQ Background Workers and Asynchronous Task Handlers."""

from __future__ import annotations

import pytest

from app.workers.arq_worker import WorkerSettings
from app.workers.tasks import (
    task_document_ingestion,
    task_export_document,
    task_reindex_collection,
)


@pytest.mark.asyncio
async def test_task_document_ingestion():
    ctx = {}
    res = await task_document_ingestion(
        ctx,
        document_id="doc_123",
        collection_id="col_456",
        chunk_size=600,
    )
    assert res["status"] == "completed"
    assert res["document_id"] == "doc_123"
    assert res["collection_id"] == "col_456"
    assert res["indexed_chunks"] > 0


@pytest.mark.asyncio
async def test_task_reindex_collection():
    ctx = {}
    res = await task_reindex_collection(ctx, collection_id="col_admissions")
    assert res["status"] == "completed"
    assert res["collection_id"] == "col_admissions"
    assert res["points_reindexed"] > 0


@pytest.mark.asyncio
async def test_task_export_document():
    ctx = {}
    res = await task_export_document(
        ctx,
        job_id="job_789",
        document_type="THÔNG_BÁO",
        title="Kế hoạch tuyển sinh",
        body_paragraphs=["Nội dung đoạn 1"],
    )
    assert res["status"] == "completed"
    assert res["job_id"] == "job_789"
    assert "job_789.docx" in res["output_file"]


def test_worker_settings():
    assert len(WorkerSettings.functions) == 3
    assert WorkerSettings.job_timeout == 300
    assert WorkerSettings.max_retries == 3
