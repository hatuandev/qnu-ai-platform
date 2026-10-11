"""Regression contracts for independent Knowledge snapshots."""

from app.modules.knowledge.models import KnowledgeIndexRevision
from app.modules.knowledge.schemas import KnowledgeBindingResponse


def test_index_provenance_does_not_require_repository_revision():
    column = KnowledgeIndexRevision.__table__.c.source_revision_id
    assert column.nullable
    assert not column.foreign_keys


def test_binding_response_accepts_independent_source():
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    source = KnowledgeBindingResponse(
        id="b", collection_id="c", repository_document_id=None,
        source_revision_id=None, created_at=now, updated_at=now,
    )
    assert source.source_revision_id is None


async def test_partial_remote_activation_keeps_serving_pointers():
    from unittest.mock import AsyncMock, MagicMock, patch

    import pytest

    from app.modules.knowledge.models import (
        KnowledgeBinding,
        KnowledgeCollection,
        KnowledgeVectorGeneration,
    )
    from app.modules.knowledge.services.generation_publish_service import publish_generation

    db = AsyncMock()
    col = KnowledgeCollection(id="c", index_epoch=7, collection_metadata={"active_vector_generation_id": "old"})
    gen = KnowledgeVectorGeneration(id="new", collection_id="c", status="ready", qdrant_collection_name="new_vectors")
    bindings = [KnowledgeBinding(id=f"b{i}", collection_id="c", status="active", active_source_revision_id=f"s{i}", active_index_revision_id=f"old{i}", active_epoch=1) for i in range(2)]
    revisions = [KnowledgeIndexRevision(id=f"r{i}", binding_id=f"b{i}", vector_generation_id="new", source_revision_v2_id=f"s{i}", status="ready", chunk_count=1) for i in range(2)]
    db.get.return_value = gen
    results = [MagicMock(), MagicMock()]
    results[0].scalars.return_value.all.return_value = bindings
    results[1].scalars.return_value.all.return_value = revisions
    db.execute.side_effect = results
    with (
        patch("app.modules.knowledge.services.generation_publish_service.get_scoped_collection", AsyncMock(return_value=col)),
        patch("app.modules.knowledge.services.generation_publish_service.vector_indexer.activate_index_revision", AsyncMock(side_effect=[1, RuntimeError("Qdrant unavailable")])),
        patch("app.modules.knowledge.services.generation_publish_service.vector_indexer.deactivate_index_revision", AsyncMock()) as deactivate,
        pytest.raises(RuntimeError, match="Qdrant unavailable"),
    ):
        await publish_generation(db, "c", "new")
    assert col.index_epoch == 7
    assert col.collection_metadata["active_vector_generation_id"] == "old"
    assert [b.active_index_revision_id for b in bindings] == ["old0", "old1"]
    assert gen.status == "ready"
    deactivate.assert_not_called()


async def test_cancelled_batch_counters_are_recomputed_without_reviving_batch():
    from unittest.mock import AsyncMock, MagicMock

    from app.modules.knowledge.models import KnowledgeImportBatch
    from app.modules.knowledge.services.import_state_service import refresh_batch_counts

    db = AsyncMock()
    batch = KnowledgeImportBatch(id="batch", status="cancelled", processing_count=99)
    result, counts = MagicMock(), MagicMock()
    result.scalar_one.return_value = batch
    counts.all.return_value = [("succeeded", 2), ("skipped", 3)]
    db.execute.side_effect = [result, counts]
    await refresh_batch_counts(db, "batch")
    assert batch.status == "cancelled"
    assert batch.processing_count == 0
    assert batch.succeeded_count == 2
    assert batch.skipped_count == 3
