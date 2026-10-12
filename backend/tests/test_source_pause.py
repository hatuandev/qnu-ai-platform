"""Stopping a Knowledge source preserves artifacts and changes the serving epoch."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.core.exceptions import AppException, EntityNotFoundError
from app.modules.documents.models import RepositoryDocument
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
    KnowledgeVectorGeneration,
)
from app.modules.rag.retriever import hybrid_retriever


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["active", "pending"])
async def test_pause_is_idempotent_preserves_pointers_and_never_touches_vectors(status):
    from app.modules.knowledge.services import source_pause as service

    db = AsyncMock()
    db.scalar.return_value = None
    binding = SimpleNamespace(id="source", collection_id="col", status=status,
        active_epoch=3, active_source_revision_id="md", active_index_revision_id="index")
    collection = SimpleNamespace(id="col", index_epoch=7, tenant_id="tenant", workspace_id="workspace")
    with (
        patch.object(service, "get_scoped_binding", AsyncMock(return_value=binding)),
        patch.object(service, "get_scoped_collection", AsyncMock(return_value=collection)),
        patch.object(service, "ensure_source_idle", AsyncMock()),
        patch.object(service.binding_service, "get_binding", AsyncMock(return_value=binding)),
    ):
        await service.pause_source(db, "source")
        assert binding.status == "paused"
        assert binding.active_index_revision_id == "index"
        assert binding.active_source_revision_id == "md"
        assert binding.active_epoch == 4
        assert collection.index_epoch == 8
        db.delete.assert_not_awaited()
        await service.pause_source(db, "source")
        assert collection.index_epoch == 8
        db.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("busy", ["parse", "index", "job"])
async def test_pause_refuses_concurrent_work(busy):
    from app.modules.knowledge.services import source_pause as service

    db = AsyncMock()
    db.scalar.side_effect = ["index" if busy == "index" else None, "job" if busy == "job" else None]
    binding = SimpleNamespace(collection_id="col", status="active")
    idle = AsyncMock(side_effect=AppException("busy", code="REPARSE_ALREADY_IN_PROGRESS", status_code=409)) if busy == "parse" else AsyncMock()
    with (
        patch.object(service, "get_scoped_binding", AsyncMock(return_value=binding)),
        patch.object(service, "get_scoped_collection", AsyncMock()),
        patch.object(service, "ensure_source_idle", idle),pytest.raises(AppException)
    ):
        await service.pause_source(db, "source")
    assert binding.status == "active"
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_live_pause_excludes_source_changes_cache_key_and_preserves_artifacts():
    from app.modules.knowledge.services.source_pause import pause_source

    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                async with AsyncSession(bind=connection, expire_on_commit=False,
                                        join_transaction_mode="create_savepoint") as db:
                    suffix = uuid.uuid4().hex[:12]
                    col = KnowledgeCollection(name="Pause fixture", module_code=suffix)
                    doc = RepositoryDocument(title="Pause fixture", file_name="fixture.pdf",
                        file_type="pdf", storage_path=f"fixtures/{suffix}.pdf", file_hash=suffix)
                    db.add_all([col, doc])
                    await db.flush()
                    generation = KnowledgeVectorGeneration(collection_id=col.id, embedding_model="fixture",
                        provider_id="fixture", qdrant_collection_name=f"fixture_{suffix}",
                        config_hash=suffix, embedding_dimension=2)
                    db.add(generation)
                    await db.flush()
                    col.collection_metadata = {"active_vector_generation_id": generation.id}
                    bindings = []
                    for number in (1, 2):
                        binding = KnowledgeBinding(collection_id=col.id, status="active")
                        db.add(binding)
                        await db.flush()
                        revision = KnowledgeSourceRevision(binding_id=binding.id, revision_no=1,
                            origin_document_id=doc.id, origin_file_hash=suffix,
                            snapshot_storage_path=f"fixtures/{suffix}-{number}.pdf",
                            canonical_markdown="Pause fixture content", status="ready")
                        db.add(revision)
                        await db.flush()
                        index = KnowledgeIndexRevision(binding_id=binding.id,
                            source_revision_v2_id=revision.id, vector_generation_id=generation.id,
                            revision_no=1, chunk_count=1, status="active")
                        db.add(index)
                        await db.flush()
                        binding.active_source_revision_id = revision.id
                        binding.active_index_revision_id = index.id
                        bindings.append(binding)
                    await db.commit()
                    before = await hybrid_retriever.resolve_retrieval_snapshot(db, col.id)
                    with pytest.raises(EntityNotFoundError):
                        await pause_source(db, bindings[0].id, actor=SimpleNamespace(tenant_id="other", workspace_id="other"))
                    result = await pause_source(db, bindings[0].id)
                    after = await hybrid_retriever.resolve_retrieval_snapshot(db, col.id)
                    assert result.status == "paused"
                    assert bindings[0].id not in after.binding_revisions
                    assert bindings[1].id in after.binding_revisions
                    assert before.cache_fingerprint() != after.cache_fingerprint()
                    with pytest.raises(AppException) as stale:
                        await hybrid_retriever.resolve_retrieval_snapshot(db, col.id, pinned_snapshot=before)
                    assert stale.value.code == "STALE_RETRIEVAL_SNAPSHOT"
                    for model, identity in ((RepositoryDocument, doc.id),
                        (KnowledgeSourceRevision, bindings[0].active_source_revision_id),
                        (KnowledgeIndexRevision, bindings[0].active_index_revision_id)):
                        assert await db.scalar(select(model.id).where(model.id == identity)) == identity
                    await pause_source(db, bindings[0].id)
                    assert col.index_epoch == before.collection_epoch + 1
                    from app.modules.knowledge.services.source_ingestion_service import (
                        source_ingestion_service,
                    )

                    with patch("app.modules.knowledge.services.source_ingestion_service.evaluate_revision_quality",
                               return_value={"overall_status": "passed"}):
                        await source_ingestion_service.update_revision_content(
                            db, col.id, bindings[0].id, bindings[0].active_source_revision_id,
                            "Updated fixture content that must remain paused.",
                        )
                    await db.refresh(bindings[0])
                    assert bindings[0].status == "paused"
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_pause_respects_actor_scope():
    from app.modules.knowledge.services import source_pause as service

    db = AsyncMock()
    actor = SimpleNamespace(tenant_id="other", workspace_id="other")
    with (
        patch.object(service, "get_scoped_binding", AsyncMock(side_effect=EntityNotFoundError("missing"))) as scoped,
        pytest.raises(EntityNotFoundError),
    ):
        await service.pause_source(db, "source", actor=actor)
    scoped.assert_awaited_once_with(db, "source", actor=actor)
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_reviewing_markdown_does_not_resume_paused_source():
    from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service

    db = AsyncMock()
    revision = SimpleNamespace(id="md", status="review_required", parse_provenance={},
                               citation_metadata={}, canonical_markdown="Nội dung", page_manifest=[], canonical_hash=None)
    binding = SimpleNamespace(id="source", status="paused", active_source_revision_id="old")
    result = MagicMock()
    result.scalar_one_or_none.return_value = revision
    db.execute.return_value = result
    with (
        patch.object(source_ingestion_service, "get_source", AsyncMock(return_value=binding)),
        patch("app.modules.knowledge.services.source_reparse.lock_source", AsyncMock()),
        patch("app.modules.knowledge.services.source_reparse.ensure_source_idle", AsyncMock()),
    ):
        await source_ingestion_service.review_source_revision(db, "col", "source", "md", "approved")
    assert revision.status == "ready"
    assert binding.status == "paused"
