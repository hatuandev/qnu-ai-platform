from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.jobs.models import JobRecord
from app.modules.knowledge.models import KnowledgeBinding, KnowledgeSourceRevision
from app.modules.knowledge.services.source_pages import merge_edited_manifest
from app.modules.knowledge.services.source_reparse import (
    ensure_source_idle,
    lock_source,
    queue_reparse,
    run_reparse,
)


@pytest.mark.asyncio
async def test_lock_source_uses_row_lock():
    db = AsyncMock()
    await lock_source(db, "source")
    assert "FOR UPDATE" in str(db.execute.await_args.args[0])


@pytest.mark.asyncio
async def test_pending_revision_rejects_second_request_before_dispatch():
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = "revision_pending"
    db.execute.return_value = result
    with pytest.raises(AppException) as error:
        await ensure_source_idle(db, "source")
    assert error.value.code == "REPARSE_ALREADY_IN_PROGRESS"
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_queue_persists_revision_and_job_when_broker_is_down():
    db = AsyncMock()
    db.add = MagicMock()
    result = MagicMock()
    result.scalar.return_value = 4
    db.execute.return_value = result
    binding = SimpleNamespace(
        active_source_revision=SimpleNamespace(
            origin_document_id="doc",
            origin_file_hash="hash",
            snapshot_storage_path="snapshot.pdf",
            snapshot_metadata={},
        )
    )

    async def assign_ids():
        for call in db.add.call_args_list:
            if isinstance(call.args[0], KnowledgeSourceRevision):
                call.args[0].id = "revision_new"

    db.flush.side_effect = assign_ids
    with (
        patch("app.modules.knowledge.services.source_reparse.lock_source", new_callable=AsyncMock),
        patch(
            "app.modules.knowledge.services.source_reparse.ensure_source_idle",
            new_callable=AsyncMock,
        ),
        patch(
            "app.modules.knowledge.services.source_ingestion_service.source_ingestion_service.get_source",
            new_callable=AsyncMock,
            return_value=binding,
        ),
        patch(
            "app.modules.knowledge.services.source_reparse.enqueue_arq_job",
            new_callable=AsyncMock,
            return_value=None,
        ) as dispatch,
    ):
        revision = await queue_reparse(
            db, "col", "source", "vision_ocr", None, "tenant", "workspace"
        )
    assert revision.status == "queued" and revision.revision_no == 5
    job = next(c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], JobRecord))
    assert job.dispatch_status == "pending" and job.payload["revision_id"] == revision.id
    assert job.tenant_id == "tenant" and job.workspace_id == "workspace"
    db.commit.assert_awaited_once()
    dispatch.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_reparse_is_persisted_without_changing_active_source():
    revision = KnowledgeSourceRevision(id="new", binding_id="source", status="queued")
    db = AsyncMock()
    db.get.return_value = revision
    result = MagicMock()
    result.scalar_one_or_none.return_value = revision
    db.execute.return_value = result
    job = JobRecord(
        collection_id="col",
        payload={"revision_id": "new", "source_id": "source", "parser_profile": "vision_ocr"},
    )
    with (
        patch(
            "app.modules.knowledge.services.source_ingestion_service.source_ingestion_service.execute_reparse",
            new_callable=AsyncMock,
            side_effect=AppException("offline", code="OCR_UNAVAILABLE", status_code=503),
        ),
        pytest.raises(AppException),
    ):
        await run_reparse(db, job)
    assert revision.status == "failed" and revision.failure_code == "OCR_UNAVAILABLE"
    assert revision.finished_at is not None
    assert db.commit.await_count == 1


@pytest.mark.asyncio
async def test_delete_deactivates_each_vector_space_and_keeps_snapshot():
    from app.modules.knowledge.services.binding_service import binding_service

    db = AsyncMock()
    binding = KnowledgeBinding(id="source", collection_id="col", status="active", active_epoch=2)
    collection = SimpleNamespace(index_epoch=7)
    revision = SimpleNamespace(id="index", vector_generation_id="gen", status="active")
    result = MagicMock()
    result.scalars.return_value.all.return_value = [revision]
    db.execute.return_value = result
    db.get.return_value = SimpleNamespace(qdrant_collection_name="custom_vectors")
    with (
        patch(
            "app.modules.knowledge.services.binding_service.get_scoped_binding",
            new_callable=AsyncMock,
            return_value=binding,
        ),
        patch(
            "app.modules.knowledge.services.binding_service.get_scoped_collection",
            new_callable=AsyncMock,
            return_value=collection,
        ),
        patch(
            "app.modules.knowledge.services.source_reparse.ensure_source_idle",
            new_callable=AsyncMock,
        ),
        patch.object(binding_service, "get_binding", new_callable=AsyncMock),
        patch(
            "app.modules.rag.vector_indexer.vector_indexer.deactivate_index_revision",
            new_callable=AsyncMock,
        ) as deactivate,
    ):
        await binding_service.detach_binding(db, "source")
    deactivate.assert_awaited_once_with("col", "index", qdrant_collection_name="custom_vectors")
    assert binding.status == "detached" and binding.active_index_revision_id is None
    assert binding.active_epoch == 3 and collection.index_epoch == 8
    db.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_does_not_report_success_when_qdrant_fails():
    from app.modules.knowledge.services.binding_service import binding_service

    db = AsyncMock()
    binding = KnowledgeBinding(id="source", collection_id="col", status="active")
    result = MagicMock()
    result.scalars.return_value.all.return_value = [
        SimpleNamespace(id="index", status="active", vector_generation_id=None)
    ]
    db.execute.return_value = result
    with (
        patch(
            "app.modules.knowledge.services.binding_service.get_scoped_binding",
            new_callable=AsyncMock,
            return_value=binding,
        ),
        patch(
            "app.modules.knowledge.services.source_reparse.ensure_source_idle",
            new_callable=AsyncMock,
        ),
        patch(
            "app.modules.rag.vector_indexer.vector_indexer.deactivate_index_revision",
            new_callable=AsyncMock,
            side_effect=AppException("offline", code="QDRANT_UNAVAILABLE", status_code=503),
        ),
        pytest.raises(AppException),
    ):
        await binding_service.detach_binding(db, "source")
    db.commit.assert_not_awaited()
    assert binding.status == "active"


def test_edit_keeps_snapshot_layout_but_marks_text_alignment_stale():
    original = [
        {
            "page": 1,
            "chars": 3,
            "dimensions": {"width": 1200, "height": 1600},
            "blocks": [{"id": "b1"}],
            "has_tables": True,
        }
    ]
    merged = merge_edited_manifest(original, [{"page": 1, "chars": 12}])
    assert merged[0]["blocks"] == original[0]["blocks"]
    assert merged[0]["dimensions"] == original[0]["dimensions"]
    assert merged[0]["chars"] == 12
    assert merged[0]["layout_text_alignment"] == "stale"
    assert "layout_text_alignment" not in original[0]


def test_edit_does_not_invent_layout_for_unmapped_or_new_pages():
    assert merge_edited_manifest(
        [{"page": 1, "blocks": [{"id": "b1"}]}],
        [{"page": None, "chars": 4}, {"page": 2, "chars": 8}],
    ) == [{"page": None, "chars": 4}, {"page": 2, "chars": 8}]
