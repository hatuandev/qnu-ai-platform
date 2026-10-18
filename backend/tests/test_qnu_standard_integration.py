"""PostgreSQL rollback drill: standard edit -> review -> chunks -> RAG evidence.

Only isolated fixture rows and fake in-memory storage are used. No embedding,
provider request, Qdrant write or business publication is executed.
"""

import hashlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.normalization.qnu_markdown import (
    QnuBlock,
    QnuSourceInfo,
    QnuSourceLocation,
    QnuStructuredDocument,
    render_qnu_markdown,
)
from app.modules.knowledge.services.chunk_set_service import chunk_set_service
from app.modules.knowledge.services.qnu_docx_artifacts import save_qnu_document
from app.modules.knowledge.services.qnu_serving import serving_pages
from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service
from app.modules.rag.evidence_blocks import load_published_blocks, pack_context, rank_blocks
from app.modules.rag.evidence_schemas import QuoteReference
from app.modules.rag.evidence_validation import bind_quote
from app.modules.rag.schemas import RetrievalSnapshot


@pytest.mark.asyncio
async def test_standard_edit_review_index_and_pinned_evidence_real_db_rollback():
    tag = "qnu526_" + uuid4().hex
    stored = {}
    async def save(path, data):
        stored[path] = data
    storage = SimpleNamespace(save=AsyncMock(side_effect=save), get=AsyncMock(side_effect=lambda path: stored.get(path)),
                              exists=AsyncMock(side_effect=lambda path: path in stored))
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as connection:
            outer = await connection.begin()
            try:
                async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint") as db:
                    collection = KnowledgeCollection(name="Isolated standard fixture", module_code=tag)
                    db.add(collection)
                    await db.flush()
                    binding = KnowledgeBinding(collection_id=collection.id, status="active")
                    db.add(binding)
                    await db.flush()
                    path = f"snapshots/{collection.id}/{binding.id}/fixture.pdf"
                    document = QnuStructuredDocument(title="Fixture", source=QnuSourceInfo(filename="fixture.pdf", sha256="a" * 64, page_count=2), blocks=[
                        QnuBlock(id="s", type="section", body="## Phương thức", source_locations=[QnuSourceLocation(page=2)]),
                        QnuBlock(id="p", parent_id="s", type="text", body="Có năm phương thức, kèm điều kiện.",
                                 source_locations=[QnuSourceLocation(page=2, locator="block/1")], context_refs=["n"]),
                        QnuBlock(id="n", parent_id="s", type="note", body="Điều kiện riêng theo chương trình.", source_locations=[QnuSourceLocation(page=2)])])
                    with patch("app.modules.knowledge.services.qnu_docx_artifacts.storage_service", storage), patch("app.modules.knowledge.services.qnu_serving.storage_service", storage):
                        base = KnowledgeSourceRevision(binding_id=binding.id, revision_no=1, status="ready", origin_document_id=tag,
                            origin_file_hash="a" * 64, snapshot_storage_path=path, canonical_markdown="Old serving content",
                            canonical_hash=hashlib.sha256(b"Old serving content").hexdigest(), page_manifest=[{"page": 1}, {"page": 2}])
                        db.add(base)
                        await db.flush()
                        reference = await save_qnu_document(document, document_id=binding.id, revision_id=base.id, snapshot_path=path)
                        base.snapshot_metadata = {"qnu_markdown": reference}
                        binding.active_source_revision_id = base.id
                        await db.flush()
                        markdown = render_qnu_markdown(document, document_id=binding.id, revision_id=base.id)
                        revised = await source_ingestion_service.update_revision_content(db, collection.id, binding.id, base.id,
                            markdown, actor_id="fixture_editor", change_reason="Đối chiếu fixture nguồn",
                            expected_canonical_hash=base.canonical_hash, content_format="qnu-rag-markdown/1.0")
                        assert revised.id != base.id and revised.status == "review_required"
                        assert binding.active_source_revision_id == base.id and binding.active_index_revision_id is None
                        with pytest.raises(AppException):
                            await chunk_set_service.get_or_create_chunk_set(db, revised.id)
                        approved = await source_ingestion_service.review_source_revision(db, collection.id, binding.id, revised.id,
                            "approved", "Đã đối chiếu nội dung fixture", actor_id="fixture_reviewer")
                        assert approved.status == "ready" and binding.active_source_revision_id == revised.id
                        chunks = await chunk_set_service.get_or_create_chunk_set(db, revised.id)
                        assert chunks.chunk_count == 3
                        pages, unknown = serving_pages(revised)
                        assert not unknown and [page["page_number"] for page in pages] == [2]
                        generation = KnowledgeVectorGeneration(collection_id=collection.id, embedding_model="fixture", provider_id="fixture",
                            embedding_dimension=4, qdrant_collection_name=tag, config_hash=tag, status="ready")
                        db.add(generation)
                        await db.flush()
                        index = KnowledgeIndexRevision(binding_id=binding.id, source_revision_v2_id=revised.id, vector_generation_id=generation.id,
                            revision_no=1, status="ready", chunk_count=chunks.chunk_count, parity_report={"parity_passed": True,
                                "unit_manifest_hash": chunks.chunk_config["_unit_manifest_hash"]})
                        db.add(index)
                        await db.flush()
                        snapshot = RetrievalSnapshot(snapshot_id=tag, collection_id=collection.id, binding_revisions={binding.id: index.id})
                        blocks = await load_published_blocks(db, snapshot, candidate_mode=True)
                        body = next(block for block in blocks if block.unit_id == "qnu:p")
                        assert body.id in {block.id for block in rank_blocks(blocks, ["năm phương thức"], 3, [])}
                        selected = pack_context(blocks, [body], [], 5, 6000)
                        assert {block.unit_id for block in selected} >= {"qnu:p", "qnu:n"}
                        bound = bind_quote(QuoteReference(block_id=body.id, quote="năm phương thức"), {body.id: body})
                        assert revised.canonical_markdown[bound["start"]:bound["end"]] == bound["quote"]
                        assert bound["source_revision_id"] == revised.id and bound["page_number"] == 2
                        other = snapshot.model_copy(update={"collection_id": "another_collection"})
                        assert not await load_published_blocks(db, other, candidate_mode=True)
                        assert snapshot.cache_fingerprint() != other.cache_fingerprint()
            finally:
                await outer.rollback()
    finally:
        await engine.dispose()
