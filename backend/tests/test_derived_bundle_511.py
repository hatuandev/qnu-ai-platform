"""Isolated DB contracts plus rollback and post-I/O publication regression."""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeFact,
    KnowledgeIndexActivation,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.services.chunk_set_service import chunk_set_service
from app.modules.knowledge.services.generation_candidate import validate_candidate_artifacts
from app.modules.knowledge.services.generation_publish_service import publish_generation
from app.modules.knowledge.services.source_artifact import build_source_artifact


@pytest.mark.asyncio
async def test_real_db_sealed_chunks_facts_revision_and_tamper_guards():
    """No model/vector calls; all fixture writes roll back the outer transaction."""
    key = f"test511_{uuid4().hex[:12]}"
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as connection:
            outer = await connection.begin()
            try:
                async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint") as db:
                    col = KnowledgeCollection(name="Isolated structure fixture", module_code=key)
                    db.add(col)
                    await db.flush()
                    binding = KnowledgeBinding(collection_id=col.id, status="active")
                    gen = KnowledgeVectorGeneration(collection_id=col.id, embedding_model="fixture", provider_id="fixture",
                                                    embedding_dimension=4, qdrant_collection_name=key, config_hash=key, status="ready")
                    db.add_all([binding, gen])
                    await db.flush()
                    markdown = "# Source 2026\n\n| Entity | Value |\n| --- | --- |\n| Alpha | 21 |"
                    artifact = build_source_artifact(markdown, 0, {})
                    source = KnowledgeSourceRevision(binding_id=binding.id, revision_no=1, status="ready",
                        origin_document_id=key, origin_file_hash=key, snapshot_storage_path=key,
                        canonical_markdown=markdown, canonical_hash=artifact["content_hash"],
                        parse_provenance={"structured_artifact": artifact})
                    db.add(source)
                    await db.flush()
                    binding.active_source_revision_id = source.id
                    chunk_set = await chunk_set_service.get_or_create_chunk_set(db, source.id)
                    manifest = chunk_set.chunk_config["_manifest"]
                    report = {"source_content_hash": source.canonical_hash, "fact_set_hash": artifact["fact_set_hash"],
                              "derived_bundle_hash": chunk_set.chunk_config["_bundle_hash"],
                              "derived_bundle_version": "derived-bundle-v1", "parity_passed": True,
                              "expected_count": len(manifest), "verified_count": len(manifest)}
                    index = KnowledgeIndexRevision(binding_id=binding.id, source_revision_v2_id=source.id,
                        vector_generation_id=gen.id, chunk_set_id=chunk_set.id, revision_no=1,
                        status="ready", chunk_count=len(manifest), fact_count=len(artifact["facts"]), parity_report=report)
                    db.add(index)
                    await db.flush()
                    chunks = []
                    for item in manifest:
                        chunk = KnowledgeChunk(collection_id=col.id, binding_id=binding.id, index_revision_id=index.id,
                            chunk_index=item["index"], content=item["content"], chunk_hash=item["chunk_hash"],
                            token_count=item["token_count"], section=item["section"], page_number=item["page_number"],
                            chunk_metadata={**item["metadata"], "source_revision_id": source.id, "chunk_set_id": chunk_set.id})
                        db.add(chunk)
                        chunks.append(chunk)
                    facts = []
                    for draft in artifact["facts"]:
                        fact = KnowledgeFact(**{k: v for k, v in draft.items() if k not in {"id", "raw_data"}},
                            raw_data={**draft["raw_data"], "source_revision_id": source.id, "fact_set_hash": artifact["fact_set_hash"]},
                            collection_id=col.id, binding_id=binding.id, index_revision_id=index.id)
                        db.add(fact)
                        facts.append(fact)
                    await db.flush()
                    await validate_candidate_artifacts(db, [index])
                    # Same character content, wrong provenance must still fail.
                    original_meta = deepcopy(chunks[-1].chunk_metadata)
                    chunks[-1].chunk_metadata = {**original_meta, "source_revision_id": "another"}
                    await db.flush()
                    with pytest.raises(AppException, match="Chunks") as failure:
                        await validate_candidate_artifacts(db, [index])
                    assert failure.value.code == "DERIVED_BUNDLE_INVALID"
                    chunks[-1].chunk_metadata = original_meta
                    await db.flush()
                    # Removing the new report marker cannot bypass a sealed chunk set.
                    index.parity_report = {k: v for k, v in report.items() if not k.startswith("derived_bundle")}
                    await db.flush()
                    with pytest.raises(AppException) as failure:
                        await validate_candidate_artifacts(db, [index])
                    assert failure.value.code == "DERIVED_BUNDLE_INVALID"
                    index.parity_report = report
                    original_raw = deepcopy(facts[0].raw_data)
                    facts[0].raw_data = {**original_raw, "fact_set_hash": "wrong"}
                    await db.flush()
                    with pytest.raises(AppException) as failure:
                        await validate_candidate_artifacts(db, [index])
                    assert failure.value.code == "FACT_SET_PARITY_FAILED"
                    facts[0].raw_data = original_raw
                    await db.flush()
                    await validate_candidate_artifacts(db, [index])
                    assert binding.active_index_revision_id is None
                    # Exercise the actual existing source rollback service against
                    # sealed DB artifacts; only the remote vector adapter is fake.
                    from app.modules.knowledge.services.index_build_service import (
                        index_build_service,
                    )

                    gen.status = "active"
                    col.collection_metadata = {"active_vector_generation_id": gen.id}
                    current = KnowledgeIndexRevision(binding_id=binding.id, revision_no=2, status="active",
                        vector_generation_id=gen.id, source_revision_v2_id=source.id, chunk_count=1)
                    db.add(current)
                    await db.flush()
                    binding.active_index_revision_id = current.id
                    binding.active_epoch = 2
                    index.status = "archived"
                    db.add(KnowledgeIndexActivation(binding_id=binding.id, to_index_revision_id=index.id, epoch=1))
                    db.add(KnowledgeIndexActivation(binding_id=binding.id, to_index_revision_id=current.id, epoch=2))
                    await db.commit()
                    expected_epoch = binding.active_epoch
                    with patch("app.modules.knowledge.services.revision_publish_service.vector_indexer.activate_index_revision",
                               AsyncMock()) as activate, patch(
                        "app.modules.knowledge.services.revision_publish_service.vector_indexer.deactivate_index_revision", AsyncMock(),
                    ) as deactivate:
                        response = await index_build_service.rollback_index_revision(db, binding.id, index.id, expected_epoch,
                            actor=SimpleNamespace(actor_id="fixture-reviewer"))
                    assert response.to_index_revision_id == index.id and response.action == "rollback"
                    assert response.activated_by == "fixture-reviewer" and response.epoch == expected_epoch + 1
                    assert binding.active_index_revision_id == index.id
                    assert activate.call_args.kwargs["qdrant_collection_name"] == key
                    deactivate.assert_not_called()
            finally:
                await outer.rollback()
    finally:
        await engine.dispose()


def result(items):
    response = MagicMock()
    response.scalars.return_value.all.return_value = items
    return response


@pytest.mark.asyncio
async def test_rollback_uses_last_published_revision_not_newer_unpublished_build():
    col = KnowledgeCollection(id="col", index_epoch=4, collection_metadata={"active_vector_generation_id": "current"})
    gen = KnowledgeVectorGeneration(id="old", collection_id=col.id, status="retired", embedding_model="fixture", embedding_dimension=4)
    previous = KnowledgeVectorGeneration(id="current", collection_id=col.id, status="active")
    binding = KnowledgeBinding(id="binding", collection_id=col.id, status="active", active_epoch=3,
                               active_source_revision_id="source_now", active_index_revision_id="index_now")
    published = KnowledgeIndexRevision(id="published", binding_id=binding.id, source_revision_v2_id="old_source",
        vector_generation_id=gen.id, revision_no=1, status="archived", chunk_count=3)
    staged = KnowledgeIndexRevision(id="staged", binding_id=binding.id, source_revision_v2_id="new_source",
        vector_generation_id=gen.id, revision_no=2, status="ready", chunk_count=4)
    activation = KnowledgeIndexActivation(binding_id=binding.id, to_index_revision_id=published.id, epoch=1)
    db = AsyncMock()
    db.add = MagicMock()
    db.get.side_effect = lambda model, key: gen if key == "old" else previous
    db.execute.side_effect = [result([binding]), result([staged, published]), result([activation]), result([binding])]
    with patch("app.modules.knowledge.services.generation_publish_service.get_scoped_collection", AsyncMock(return_value=col)), \
         patch("app.modules.knowledge.services.generation_candidate.validate_candidate_artifacts", AsyncMock()) as validate, \
         patch("app.modules.knowledge.services.generation_publish_service.vector_indexer.activate_index_revision", AsyncMock()) as activate:
        await publish_generation(db, col.id, gen.id, SimpleNamespace(actor_id="reviewer"), rollback=True)
    assert binding.active_index_revision_id == published.id
    assert binding.active_source_revision_id == "source_now"  # Editing pointer is not serving pointer.
    assert validate.await_count == 2
    assert activate.call_args.args[1] == published.id
    audit = db.add.call_args.args[0]
    assert audit.action == "rollback" and audit.activated_by == "reviewer"
