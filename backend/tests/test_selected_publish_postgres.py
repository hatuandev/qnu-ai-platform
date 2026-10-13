"""Opt-in PostgreSQL round-trip; fixture writes stay inside a rolled-back transaction."""

import os
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeIndexActivation,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.schemas import PublishVectorItem
from app.modules.knowledge.services.selected_vector_publish import publish_selected_vectors
from app.modules.rag.retriever import hybrid_retriever


@pytest.mark.skipif(os.getenv("QNU_TEST_SELECTED_PUBLISH_DB") != "1", reason="Opt-in PostgreSQL fixture")
@pytest.mark.asyncio
async def test_publish_incrementally_preserves_snapshot_and_round_trips_pointers():
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    tag = uuid.uuid4().hex[:10]
    actor = SimpleNamespace(tenant_id="tenant_qnu", workspace_id="workspace_qnu", actor_id="test_officer")
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint") as db:
                    collection = KnowledgeCollection(
                        id=f"test_partial_{tag}", name="TEST partial publication", module_code="general", index_epoch=1,
                    )
                    db.add(collection)
                    await db.flush()
                    gen = KnowledgeVectorGeneration(
                        id=f"test_gen_{tag}", collection_id=collection.id, embedding_model="test_dynamic_model",
                        provider_id="test_provider", embedding_dimension=8, config_hash=tag,
                        qdrant_collection_name=f"test_vectors_{tag}", status="ready",
                    )
                    bindings = [KnowledgeBinding(
                        id=f"test_b{number}_{tag}", collection_id=collection.id, status="active",
                    ) for number in range(3)]
                    db.add_all([gen, *bindings])
                    await db.flush()
                    sources = [KnowledgeSourceRevision(
                        id=f"test_s{number}_{tag}", binding_id=binding.id, revision_no=1,
                        origin_document_id=f"test_doc_{tag}", origin_file_hash=tag,
                        snapshot_storage_path=f"test/{tag}", canonical_hash=tag, canonical_markdown="TEST content",
                        status="ready", parse_provenance={"structured_artifact": {
                            "content_hash": tag, "issues": [], "review": {"status": "approved"},
                        }},
                    ) for number, binding in enumerate(bindings)]
                    db.add_all(sources)
                    await db.flush()
                    indexes = [KnowledgeIndexRevision(
                        id=f"test_i{number}_{tag}", binding_id=bindings[number].id,
                        source_revision_v2_id=sources[number].id, vector_generation_id=gen.id,
                        revision_no=1, status="ready", chunk_count=1, parity_report={"parity_passed": True},
                    ) for number in range(2)]
                    db.add_all(indexes)
                    for binding, source in zip(bindings, sources, strict=True):
                        binding.active_source_revision_id = source.id
                    await db.flush()
                    items = [PublishVectorItem(
                        binding_id=index.binding_id, source_revision_id=index.source_revision_v2_id,
                        index_revision_id=index.id,
                    ) for index in indexes]
                    with patch(
                        "app.modules.knowledge.services.selected_vector_publish.vector_indexer.activate_index_revision",
                        AsyncMock(return_value=1),
                    ):
                        await publish_selected_vectors(db, collection.id, gen.id, items[:1], actor)
                        first = await hybrid_retriever.resolve_retrieval_snapshot(db, collection.id)
                        assert first.binding_revisions == {bindings[0].id: indexes[0].id}
                        await publish_selected_vectors(db, collection.id, gen.id, items[1:], actor)
                        collection_id, generation_id = collection.id, gen.id
                        binding_ids = [binding.id for binding in bindings]
                        index_ids = [index.id for index in indexes]
                        db.expire_all()
                        stored = list((await db.scalars(select(KnowledgeBinding).where(
                            KnowledgeBinding.collection_id == collection_id,
                        ).order_by(KnowledgeBinding.id))).all())
                        assert [binding.active_index_revision_id for binding in stored] == [*index_ids, None]
                        snapshot = await hybrid_retriever.resolve_retrieval_snapshot(db, collection_id)
                        assert snapshot.binding_revisions == dict(zip(binding_ids[:2], index_ids, strict=True))
                        assert first.binding_revisions == {binding_ids[0]: index_ids[0]}
                        epoch = snapshot.collection_epoch
                        repeat = await publish_selected_vectors(db, collection_id, generation_id, items[1:], actor)
                        assert repeat.new_epoch == epoch
                    assert await db.scalar(select(func.count(KnowledgeIndexActivation.id)).where(
                        KnowledgeIndexActivation.binding_id.in_([binding.id for binding in stored]),
                    )) == 2
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
