"""Real PostgreSQL, isolated rollback: published/draft facts and candidate scope."""

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeFact,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.services.facts_service import facts_service
from app.modules.knowledge.services.generation_candidate import (
    resolve_candidate_snapshot,
    validate_candidate_artifacts,
)
from app.modules.knowledge.services.source_artifact import build_source_artifact


@pytest.mark.asyncio
async def test_real_db_candidate_isolation_and_tampered_fact_rejected():
    tenant = f"test382_{uuid.uuid4().hex[:12]}"
    actor = SimpleNamespace(tenant_id=tenant, workspace_id=tenant)
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                async with AsyncSession(bind=connection, expire_on_commit=False) as db:
                    collection = KnowledgeCollection(name="Isolated fixture", module_code=tenant, tenant_id=tenant, workspace_id=tenant)
                    db.add(collection)
                    await db.flush()
                    binding = KnowledgeBinding(collection_id=collection.id, tenant_id=tenant, workspace_id=tenant, status="active")
                    generation = KnowledgeVectorGeneration(collection_id=collection.id, tenant_id=tenant, workspace_id=tenant,
                        embedding_model="fixture-model", provider_id="fixture-provider", embedding_dimension=4,
                        qdrant_collection_name=tenant, config_hash=tenant, status="ready")
                    db.add_all([binding, generation])
                    await db.flush()
                    markdown = "| Entity | Year 2025 |\n| --- | --- |\n| Example Entity | 21.5 |"
                    artifact = build_source_artifact(markdown, 1, {})
                    source = KnowledgeSourceRevision(binding_id=binding.id, revision_no=1, origin_document_id="fixture",
                        origin_file_hash="fixture", snapshot_storage_path="fixture", status="ready",
                        canonical_markdown=markdown, canonical_hash=artifact["content_hash"],
                        page_manifest=[{"page": 1}], parse_provenance={"structured_artifact": artifact})
                    db.add(source)
                    await db.flush()
                    binding.active_source_revision_id = source.id
                    index = KnowledgeIndexRevision(binding_id=binding.id, source_revision_v2_id=source.id,
                        vector_generation_id=generation.id, revision_no=1, status="ready", fact_count=1,
                        parity_report={"source_content_hash": source.canonical_hash, "fact_set_hash": artifact["fact_set_hash"]})
                    db.add(index)
                    await db.flush()
                    draft = artifact["facts"][0]
                    fact = KnowledgeFact(**{key: value for key, value in draft.items() if key != "id"},
                        collection_id=collection.id, binding_id=binding.id, index_revision_id=index.id, document_id=None)
                    db.add(fact)
                    await db.flush()
                    assert (await facts_service.get_collection_facts(db, collection.id, actor=actor)).total == 0
                    snapshot = await resolve_candidate_snapshot(db, collection.id, generation.id, actor)
                    assert snapshot.binding_revisions == {binding.id: index.id}
                    assert binding.active_index_revision_id is None  # preview never publishes
                    binding.active_index_revision_id = index.id
                    await db.flush()
                    result = await facts_service.get_collection_facts(db, collection.id, actor=actor)
                    assert result.total == 1 and result.facts[0].document_id is None
                    binding.status = "paused"
                    await db.flush()
                    assert (await facts_service.get_collection_facts(db, collection.id, actor=actor)).total == 0
                    with pytest.raises(AppException):
                        await resolve_candidate_snapshot(db, collection.id, generation.id, SimpleNamespace(tenant_id="wrong", workspace_id=tenant))
                    fact.attribute_value = "999"
                    await db.flush()
                    with pytest.raises(AppException) as error:
                        await validate_candidate_artifacts(db, [index])
                    assert error.value.code == "FACT_SET_PARITY_FAILED"
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
