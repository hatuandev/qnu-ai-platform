"""Permanent source deletion must preserve Repository and other Knowledge sources."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.core.exceptions import AppException, EntityNotFoundError
from app.modules.documents.models import RepositoryDocument
from app.modules.jobs.models import JobRecord
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunk,
    KnowledgeChunkSet,
    KnowledgeCollection,
    KnowledgeFact,
    KnowledgeSourceRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.schemas import KnowledgeImportBatchCreateRequest
from app.modules.knowledge.services import source_purge
from app.modules.knowledge.services.import_batch_service import import_batch_service
from app.modules.knowledge.services.scope_helper import get_scoped_binding


@pytest.fixture
async def purge_db():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        async with AsyncSession(bind=connection, expire_on_commit=False,
                                join_transaction_mode="create_savepoint") as session:
            yield session
        await transaction.rollback()
    await engine.dispose()


async def seed_source(db, status="paused"):
    suffix = uuid.uuid4().hex[:12]
    col = KnowledgeCollection(id=f"purge_col_{suffix}", name="Purge test", module_code=suffix)
    doc = RepositoryDocument(id=f"purge_doc_{suffix}", title="Original", file_name="original.pdf",
                             file_type="pdf", storage_path=f"documents/{suffix}.pdf", file_hash=suffix)
    db.add_all([col, doc])
    await db.flush()
    binding = KnowledgeBinding(collection_id=col.id, repository_document_id=doc.id, status=status)
    db.add(binding)
    await db.flush()
    revision = KnowledgeSourceRevision(binding_id=binding.id, revision_no=1,
        origin_document_id=doc.id, origin_file_hash=suffix,
        snapshot_storage_path=f"snapshots/{col.id}/{binding.id}/original.pdf",
        canonical_markdown="Nội dung OCR", status="ready")
    db.add(revision)
    await db.flush()
    binding.active_source_revision_id = revision.id
    chunks = KnowledgeChunkSet(source_revision_id=revision.id, config_hash=suffix,
                               chunk_config={"_manifest": [{"content": "OCR"}]})
    db.add_all([chunks,
        KnowledgeChunk(collection_id=col.id, binding_id=binding.id, chunk_index=0,
                       content="OCR", chunk_hash=suffix),
        KnowledgeFact(collection_id=col.id, binding_id=binding.id, entity_name="Test fact",
                      entity_type="test", attribute_name="value", attribute_value="1"),
    ])
    await db.commit()
    return col, doc, binding, revision, chunks


@pytest.mark.asyncio
async def test_purge_removes_knowledge_only_and_waits_for_external_cleanup(purge_db):
    db = purge_db
    col, doc, binding, revision, chunks = await seed_source(db)
    preview_path = revision.snapshot_storage_path + ".fixture.preview.pdf"
    revision.snapshot_metadata = {"preview_pdf_path": preview_path}
    for number in (1, 2):
        db.add(KnowledgeVectorGeneration(collection_id=col.id, embedding_model=f"fixture-model-{number}",
            provider_id="fixture", qdrant_collection_name=f"fixture_vectors_{number}",
            config_hash=f"fixture-{number}", embedding_dimension=number, status="building"))
    await db.commit()
    with patch.object(source_purge, "enqueue_arq_job", AsyncMock(return_value="test-no-dispatch")):
        job = await source_purge.request_purge(db, binding.id)
    assert binding.status == "deleting"
    assert job.status == "queued"
    with (
        patch.object(source_purge.vector_indexer, "delete_source_points", AsyncMock(return_value=4)) as vectors,
        patch.object(source_purge.storage_service, "delete_confirmed", AsyncMock()) as storage,
    ):
        await source_purge.run_purge(db, job)
    assert job.status == "completed"
    vectors.assert_awaited()
    assert {call.args[2] for call in vectors.await_args_list} == {
        "fixture_vectors_1", "fixture_vectors_2", source_purge.vector_indexer._get_collection_name(col.id),
    }
    assert {call.args[0] for call in storage.await_args_list} == {revision.snapshot_storage_path, preview_path}
    assert await db.scalar(select(RepositoryDocument.id).where(RepositoryDocument.id == doc.id)) == doc.id
    assert await db.scalar(select(KnowledgeBinding.id).where(KnowledgeBinding.id == binding.id)) is None
    assert await db.scalar(select(KnowledgeSourceRevision.id).where(KnowledgeSourceRevision.id == revision.id)) is None
    assert await db.scalar(select(KnowledgeChunkSet.id).where(KnowledgeChunkSet.id == chunks.id)) is None
    for model in (KnowledgeChunk, KnowledgeFact):
        assert await db.scalar(select(model.id).where(model.binding_id == binding.id)) is None
    # Idempotent replay after the final commit never touches Repository.
    await source_purge.run_purge(db, job)


@pytest.mark.asyncio
async def test_storage_failure_keeps_plan_for_retry(purge_db):
    db = purge_db
    _, doc, binding, revision, _ = await seed_source(db)
    with patch.object(source_purge, "enqueue_arq_job", AsyncMock(return_value="test-no-dispatch")):
        job = await source_purge.request_purge(db, binding.id)
    with (
        patch.object(source_purge.vector_indexer, "delete_source_points", AsyncMock(return_value=0)),
        patch.object(source_purge.storage_service, "delete_confirmed", AsyncMock(side_effect=OSError("offline"))),
        pytest.raises(AppException, match="snapshot"),
    ):
        await source_purge.run_purge(db, job)
    assert await db.scalar(select(KnowledgeSourceRevision.id).where(KnowledgeSourceRevision.id == revision.id)) == revision.id
    assert await db.scalar(select(RepositoryDocument.id).where(RepositoryDocument.id == doc.id)) == doc.id
    assert binding.status == "deleting"
    assert await db.scalar(select(JobRecord.id).where(JobRecord.id == job.id)) == job.id
    with (
        patch.object(source_purge.vector_indexer, "delete_source_points", AsyncMock(return_value=0)),
        patch.object(source_purge.storage_service, "delete_confirmed", AsyncMock()),
    ):
        await source_purge.run_purge(db, job)
    assert job.status == "completed"


@pytest.mark.asyncio
async def test_vector_failure_never_reports_success_or_deletes_snapshot(purge_db):
    db = purge_db
    _, _, binding, revision, _ = await seed_source(db)
    with patch.object(source_purge, "enqueue_arq_job", AsyncMock(return_value="test-no-dispatch")):
        job = await source_purge.request_purge(db, binding.id)
    with (
        patch.object(source_purge.vector_indexer, "delete_source_points", AsyncMock(side_effect=AppException("offline", code="QDRANT_UNAVAILABLE"))),
        patch.object(source_purge.storage_service, "delete_confirmed", AsyncMock()) as storage,
        pytest.raises(AppException),
    ):
        await source_purge.run_purge(db, job)
    storage.assert_not_awaited()
    assert job.status != "completed"
    assert await db.scalar(select(KnowledgeSourceRevision.id).where(KnowledgeSourceRevision.id == revision.id)) == revision.id


@pytest.mark.asyncio
async def test_deleting_source_is_blocked_and_other_source_cache_survives(purge_db):
    db = purge_db
    _, _, binding, revision, _ = await seed_source(db)
    _, _, other, other_revision, other_chunks = await seed_source(db, status="active")
    # Shared physical snapshot must remain for the other source.
    other_revision.snapshot_storage_path = revision.snapshot_storage_path
    preview_path = revision.snapshot_storage_path + ".shared.preview.pdf"
    revision.snapshot_metadata = {"preview_pdf_path": preview_path}
    other_revision.snapshot_metadata = {"preview_pdf_path": preview_path}
    await db.commit()
    with patch.object(source_purge, "enqueue_arq_job", AsyncMock(return_value="test-no-dispatch")):
        job = await source_purge.request_purge(db, binding.id)
        repeated = await source_purge.request_purge(db, binding.id)
    assert repeated.id == job.id
    with pytest.raises(AppException) as error:
        await get_scoped_binding(db, binding.id)
    assert error.value.code == "SOURCE_DELETING"
    with pytest.raises(AppException) as error:
        await import_batch_service.create_import_batch(collection_id=binding.collection_id,
            payload=KnowledgeImportBatchCreateRequest(document_ids=[binding.repository_document_id]),
            tenant_id=binding.tenant_id, workspace_id=binding.workspace_id, db=db)
    assert error.value.code == "SOURCE_DELETING"
    with (
        patch.object(source_purge.vector_indexer, "delete_source_points", AsyncMock()),
        patch.object(source_purge.storage_service, "delete_confirmed", AsyncMock()) as storage,
    ):
        await source_purge.run_purge(db, job)
    storage.assert_not_awaited()
    assert await db.scalar(select(KnowledgeBinding.status).where(KnowledgeBinding.id == other.id)) == "active"
    assert await db.scalar(select(KnowledgeChunkSet.id).where(KnowledgeChunkSet.id == other_chunks.id)) == other_chunks.id
    for model in (KnowledgeChunk, KnowledgeFact):
        assert await db.scalar(select(model.id).where(model.binding_id == other.id)) is not None


@pytest.mark.asyncio
async def test_vector_delete_uses_source_scope_and_waits_for_actual_removal():
    client = MagicMock()
    client.collection_exists = AsyncMock(return_value=True)
    client.delete = AsyncMock()
    client.count = AsyncMock(return_value=SimpleNamespace(count=0))
    with patch.object(source_purge.vector_indexer, "client", client):
        await source_purge.vector_indexer.delete_source_points("col", "binding", "namespace",
            tenant_id="tenant", workspace_id="workspace")
    args = client.delete.await_args.kwargs
    assert args["wait"] is True
    fields = {condition.key: condition.match.value for condition in args["points_selector"].filter.must}
    assert fields == {"collection_id": "col", "binding_id": "binding", "tenant_id": "tenant", "workspace_id": "workspace"}
    client.delete_collection.assert_not_called()
    client.count.return_value = SimpleNamespace(count=1)
    with patch.object(source_purge.vector_indexer, "client", client), pytest.raises(AppException) as error:
        await source_purge.vector_indexer.delete_source_points("col", "binding", "namespace",
            tenant_id="tenant", workspace_id="workspace")
    assert error.value.code == "SOURCE_VECTOR_DELETE_FAILED"


@pytest.mark.asyncio
async def test_purge_rejects_another_tenant_and_cannot_be_cancelled(purge_db):
    db = purge_db
    _, _, binding, _, _ = await seed_source(db)
    actor = SimpleNamespace(tenant_id="unrelated-tenant", workspace_id=binding.workspace_id)
    with pytest.raises(EntityNotFoundError):
        await source_purge.request_purge(db, binding.id, actor=actor)
    assert binding.status == "paused"
    with patch.object(source_purge, "enqueue_arq_job", AsyncMock(return_value="test-no-dispatch")):
        job = await source_purge.request_purge(db, binding.id)
    with pytest.raises(AppException) as error:
        await source_purge.jobs_service.cancel_job(db, job.id)
    assert error.value.code == "PURGE_NOT_CANCELLABLE"
    assert job.status == "queued"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["active", "pending", "detached"])
async def test_purge_requires_pause_and_never_reserves_or_dispatches(purge_db, status):
    db = purge_db
    col, doc, binding, revision, _ = await seed_source(db, status=status)
    epoch = col.index_epoch
    with (
        patch.object(source_purge, "enqueue_arq_job", AsyncMock(return_value=None)) as enqueue,
        pytest.raises(AppException) as error,
    ):
        await source_purge.request_purge(db, binding.id)
    assert error.value.code == "SOURCE_NOT_PAUSED"
    assert error.value.status_code == 409
    assert binding.status == status
    assert col.index_epoch == epoch
    assert await db.scalar(select(JobRecord.id).where(JobRecord.collection_id == col.id)) is None
    assert await db.get(RepositoryDocument, doc.id) is not None
    assert await db.get(KnowledgeSourceRevision, revision.id) is not None
    enqueue.assert_not_awaited()


@pytest.mark.asyncio
async def test_pause_then_purge_and_retry_remain_available(purge_db):
    from app.modules.knowledge.services.source_pause import pause_source

    db = purge_db
    _, _, binding, _, _ = await seed_source(db, status="active")
    await pause_source(db, binding.id)
    with patch.object(source_purge, "enqueue_arq_job", AsyncMock(return_value="test-no-dispatch")):
        job = await source_purge.request_purge(db, binding.id)
    assert binding.status == "deleting"
    assert job.status == "queued"
    job.status = "failed"
    await db.commit()
    with patch.object(source_purge.jobs_service, "retry_job", AsyncMock(return_value=job)) as retry:
        assert await source_purge.request_purge(db, binding.id) is job
    retry.assert_awaited_once_with(db, job.id, actor=None)
