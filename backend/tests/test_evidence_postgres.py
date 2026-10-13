"""Opt-in evidence contracts against real PostgreSQL; all fixture writes roll back."""

import hashlib
import os
import uuid

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
from app.modules.rag.evidence_blocks import load_published_blocks
from app.modules.rag.evidence_facts import reviewed_fact_blocks
from app.modules.rag.evidence_schemas import QueryPlan
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(
    os.getenv("QNU_TEST_EVIDENCE_DB") != "1", reason="Opt-in real PostgreSQL evidence fixture")]


async def test_pinned_hash_review_scope_and_corrected_row_use_real_database():
    engine = create_async_engine(settings.DATABASE_URL)
    tag = uuid.uuid4().hex[:10]
    try:
        async with engine.connect() as conn:
            outer = await conn.begin()
            try:
                async with AsyncSession(bind=conn, expire_on_commit=False) as db:
                    markdown = "<!-- Trang 1 -->\n# TUYỂN SINH 2026\n\n| Ngành | Sàn |\n| --- | --- |\n| TEST entity | 21 |"
                    digest = hashlib.sha256(markdown.encode()).hexdigest()
                    collection = KnowledgeCollection(id=f"ev_col_{tag}", name="TEST evidence", module_code="general")
                    binding = KnowledgeBinding(id=f"ev_b_{tag}", collection_id=collection.id, status="active")
                    db.add_all([collection, binding])
                    await db.flush()
                    generation = KnowledgeVectorGeneration(id=f"ev_g_{tag}", collection_id=collection.id,
                        embedding_model="test_encoder", provider_id="test_provider", embedding_dimension=8,
                        config_hash=tag, qdrant_collection_name=f"test_ev_{tag}", status="active")
                    db.add(generation)
                    await db.flush()
                    source = KnowledgeSourceRevision(id=f"ev_s_{tag}", binding_id=binding.id, revision_no=1,
                        origin_document_id=f"ev_doc_{tag}", origin_file_hash=tag, snapshot_storage_path=f"test/{tag}",
                        canonical_hash=digest, canonical_markdown=markdown, status="ready",
                        parse_provenance={"structured_artifact": {"content_hash": digest, "issues": [], "review": {"status": "approved"}}})
                    db.add(source)
                    await db.flush()
                    index = KnowledgeIndexRevision(id=f"ev_i_{tag}", binding_id=binding.id,
                        vector_generation_id=generation.id, source_revision_v2_id=source.id, revision_no=1,
                        status="active", chunk_count=1, parity_report={"parity_passed": True, "fact_set_hash": tag})
                    db.add(index)
                    await db.flush()
                    for column, (attribute, value) in enumerate([("Sàn", "20"), ("Điều kiện", "Tổng điểm văn hóa ≥ 13,34")]):
                        db.add(KnowledgeFact(id=f"ev_f{column}_{tag}", collection_id=collection.id, binding_id=binding.id,
                            index_revision_id=index.id, entity_name="TEST entity", entity_type="major",
                            entity_key=tag, entity_label="TEST entity", entity_text="TEST entity",
                            attribute_name=attribute, attribute_value=value,
                            raw_data={"table_id": "t1", "row_index": 1, "column_index": column, "page_number": 1}))
                    await db.flush()
                    snapshot = RetrievalSnapshot(snapshot_id=tag, collection_id=collection.id,
                        tenant_id=collection.tenant_id, workspace_id=collection.workspace_id,
                        binding_revisions={binding.id: index.id})
                    blocks = await load_published_blocks(db, snapshot)
                    assert blocks and all("| TEST entity | 21 |" not in b.text for b in blocks)
                    rows = await reviewed_fact_blocks(db, AskRequest(question="TEST entity", collection_id=collection.id),
                        snapshot, QueryPlan(query="TEST entity", years=[2026]), blocks)
                    assert len(rows) == 1 and "Sàn: 20" in rows[0].text and "13,34" in rows[0].text
                    assert rows[0].origin == "reviewed_fact" and rows[0].page_number == 1
                    assert not await load_published_blocks(db, snapshot.model_copy(update={"tenant_id": "other_tenant"}))
                    source.canonical_hash = "invalid"
                    await db.flush()
                    with pytest.raises(AppException) as error:
                        await load_published_blocks(db, snapshot)
                    assert error.value.code == "EVIDENCE_SOURCE_INVALID"
            finally:
                await outer.rollback()
    finally:
        await engine.dispose()
