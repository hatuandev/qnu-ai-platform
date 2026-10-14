"""Opt-in real PostgreSQL + configured embedding + private Qdrant staging index."""

import os
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeSourceRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.schemas import SourceContextEditRequest
from app.modules.knowledge.services.source_artifact import build_source_artifact
from app.modules.knowledge.services.source_context import (
    apply_context_edits,
    review_context_artifact,
)
from app.modules.knowledge.services.vector_generation_service import vector_generation_service
from app.modules.rag.evidence_blocks import load_published_blocks, rank_blocks
from app.modules.rag.retriever import filter_unit_years, hybrid_retriever
from app.modules.rag.schemas import RetrievalSnapshot
from app.modules.rag.vector_indexer import vector_indexer

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(os.getenv("QNU_TEST_UNIT_INDEX") != "1",
    reason="Opt-in real scoped PostgreSQL/Qdrant/embedding fixture")]


async def test_staging_units_match_dense_lexical_bm25_and_exact_source_without_publishing():
    tag = "test_units_" + uuid.uuid4().hex
    engine = create_async_engine(settings.DATABASE_URL)
    created_qdrant = False
    try:
        async with engine.connect() as connection:
            outer = await connection.begin()
            try:
                async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint") as db:
                    # Read the operator's actual vector generation, no model/key hardcoding.
                    configured = (await db.execute(select(KnowledgeVectorGeneration).where(
                        KnowledgeVectorGeneration.status == "active").order_by(KnowledgeVectorGeneration.created_at.desc()))).scalars().first()
                    assert configured is not None, "No configured active embedding generation"
                    collection = KnowledgeCollection(name="Private source-unit index verification", module_code=tag,
                        tenant_id=tag, workspace_id=tag)
                    db.add(collection)
                    await db.flush()
                    binding = KnowledgeBinding(collection_id=collection.id, tenant_id=tag, workspace_id=tag, status="active")
                    generation = KnowledgeVectorGeneration(collection_id=collection.id, tenant_id=tag, workspace_id=tag,
                        provider_id=configured.provider_id, embedding_model=configured.embedding_model,
                        embedding_dimension=configured.embedding_dimension, config_hash=tag,
                        qdrant_collection_name=tag, status="ready")
                    db.add_all([binding, generation])
                    await db.flush()
                    markdown = "# Báo cáo tổng hợp 2026\n\n" + "\n\n".join(
                        f"Đơn vị A có {value} hồ sơ trong năm {year}." for year, value in [(2022, 17), (2023, 18), (2024, 19)])
                    artifact = build_source_artifact(markdown, 0, {})
                    edits = [{"unit_id": unit["id"], "data_years": unit["temporal"]["mentioned_years"],
                              "role": "data", "evidence_quote": unit["text"]}
                             for unit in artifact["retrieval_units"]["units"] if unit["kind"] == "paragraph"]
                    artifact = review_context_artifact(apply_context_edits(artifact,
                        SourceContextEditRequest(expected_fact_set_hash=artifact["fact_set_hash"],
                            reason="Private fixture verified from exact source", units=edits), tag), "approved", tag, None)
                    artifact["review"] = {"status": "approved", "actor_id": tag}
                    source = KnowledgeSourceRevision(binding_id=binding.id, revision_no=1, origin_document_id=tag,
                        origin_file_hash=tag, snapshot_storage_path=tag, canonical_markdown=markdown,
                        canonical_hash=artifact["content_hash"], status="ready", page_manifest=[],
                        snapshot_metadata={"title": "Báo cáo tổng hợp 2026"}, parse_provenance={"structured_artifact": artifact})
                    db.add(source)
                    await db.flush()
                    binding.active_source_revision_id = source.id
                    await db.commit()
                    # Ensure a uniquely named collection before build, so cleanup
                    # never targets the operator's vector collection.
                    assert not await vector_indexer.client.collection_exists(tag)
                    await vector_indexer.ensure_collection(collection.id, vector_size=generation.embedding_dimension,
                        qdrant_collection_name=tag)
                    created_qdrant = True
                    index = await vector_generation_service.build_generation_for_source(db, collection.id, binding.id, generation.id)
                    assert index.status == "ready" and index.parity_report["parity_passed"]
                    assert index.parity_report["unit_manifest_hash"] == artifact["unit_manifest_hash"]
                    await db.refresh(binding)
                    assert binding.active_index_revision_id is None  # never published
                    snapshot = RetrievalSnapshot(snapshot_id=tag, collection_id=collection.id, tenant_id=tag,
                        workspace_id=tag, binding_revisions={binding.id: index.id}, vector_generations={binding.id: generation.id})
                    blocks = await load_published_blocks(db, snapshot, candidate_mode=True)
                    chunks = list((await db.execute(select(KnowledgeChunk).where(KnowledgeChunk.index_revision_id == index.id))).scalars())
                    points, _ = await vector_indexer.client.scroll(collection_name=tag, limit=100, with_payload=True)
                    assert len(blocks) == len(chunks) == len(points) == 4
                    payloads = {point.payload["chunk_id"]: point.payload for point in points}
                    for chunk in chunks:
                        assert payloads[chunk.id]["source_unit"] == chunk.chunk_metadata["source_unit"]
                        assert not payloads[chunk.id]["is_retrievable"]
                        unit = chunk.chunk_metadata["source_unit"]
                        assert markdown[unit["start"]:unit["end"]] == unit["text"]
                    runtime = await vector_indexer._resolve_embedding_runtime(
                        preferred_provider_id=generation.provider_id, preferred_model_name=generation.embedding_model)
                    query = "Đơn vị A có bao nhiêu hồ sơ năm 2023?"
                    vector = (await vector_indexer.embed_texts([query], runtime, target_dim=generation.embedding_dimension))[0]
                    dense = await vector_indexer.search_dense(collection.id, query, query_vector=vector,
                        tenant_id=tag, workspace_id=tag, snapshot=snapshot, qdrant_collection_name=tag,
                        candidate_mode=True, score_threshold=0.0, top_k=10)
                    sparse = await hybrid_retriever.search_sparse_fts(db, collection.id, query, top_k=10,
                        tenant_id=tag, workspace_id=tag, snapshot=snapshot, read_mode_override="revisioned")
                    for hits in [filter_unit_years(dense, [2023]), filter_unit_years(sparse, [2023])]:
                        assert any(hit["metadata"]["source_unit"]["temporal"]["data_years"] == [2023] for hit in hits)
                        assert not any(hit["metadata"]["source_unit"]["temporal"]["data_years"] in [[2022], [2024]] for hit in hits)
                    assert rank_blocks(blocks, [query], 5, [2023])[0].temporal_scope.data_years == [2023]
                    assert not any(b.temporal_scope.data_years for b in rank_blocks(blocks, [query], 5, [2026]))
                    assert not await vector_indexer.search_dense(collection.id, query, query_vector=vector,
                        tenant_id=tag, workspace_id=tag, snapshot=snapshot, qdrant_collection_name=tag, score_threshold=0.0)
                    assert not await load_published_blocks(db, snapshot.model_copy(update={"tenant_id": "other"}), candidate_mode=True)
            finally:
                await outer.rollback()
    finally:
        if created_qdrant:
            assert tag.startswith("test_units_") and len(tag) == 43
            await vector_indexer.client.delete_collection(tag)
        await engine.dispose()


@pytest.mark.skipif(os.getenv("QNU_TEST_UNIT_LLM") != "1", reason="Opt-in actual configured semantic model")
async def test_actual_model_distinguishes_historical_data_from_citation_and_event_years():
    import httpx

    from app.modules.knowledge.normalization.retrieval_units import build_unit_manifest
    from app.modules.knowledge.services.unit_annotation import propose_unit_annotations

    async with httpx.AsyncClient(trust_env=False, timeout=10) as client:
        response = await client.get("http://localhost:8001/platform/v1alpha1/assistants/admissions")
        response.raise_for_status()
        assistant = response.json()
    policy = assistant["config"]["model_policy"]
    manifest = build_unit_manifest("# Báo cáo 2026\n\nTrong năm 2023, đơn vị A xử lý 17 hồ sơ.\n\n"
        "Văn bản này viện dẫn Nghị định số 116/2020/NĐ-CP.\n\nCuộc họp diễn ra ngày 12/03/2024.")
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as db:
            await propose_unit_annotations(db, manifest, assistant["tenant_id"],
                policy["primary_model"], policy["preferred_provider_id"])
        assert manifest.units[1].temporal.role == "data" and manifest.units[1].temporal.data_years == [2023]
        assert not (manifest.units[2].temporal.role == "data" and manifest.units[2].temporal.data_years == [2020])
        assert manifest.units[3].temporal.role == "event"
        assert all(unit.temporal.status != "verified" for unit in manifest.units)
    finally:
        await engine.dispose()
