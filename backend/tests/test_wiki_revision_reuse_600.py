"""Real PostgreSQL -> chunk materialization -> pinned index -> authenticated read."""

import hashlib
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunkSet,
    KnowledgeCollection,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.normalization.retrieval_units import resolve_unit_manifest
from app.modules.knowledge.services.chunk_set_service import chunk_set_service
from app.modules.knowledge.services.source_artifact import build_source_artifact
from app.modules.knowledge.services.wiki_views import read_revision_pages
from app.modules.knowledge.wiki_schemas import WikiAnalysis, WikiGeneration
from app.modules.rag.evidence_blocks import load_published_blocks
from app.modules.rag.evidence_schemas import QueryPlan
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.schemas import RetrievalSnapshot
from app.modules.rag.wiki_context import load_wiki_pages


async def fixture_generator(contract, instruction, payload):
    if contract is WikiAnalysis:
        return WikiAnalysis(pages=[{"kind": kind, "title": title,
            "unit_ids": [unit["id"] for unit in payload["units"]]}
            for kind, title in [("source", payload["source"]["title"]),
                                ("entity", "Trường thử nghiệm"), ("concept", "Học phí")]])
    sections = [{"heading": f"Học phí {year}", "text": f"Học phí năm {year}: {fee} đồng.",
        "references": [{"unit_id": unit["id"], "quote": unit["text"]}],
        "temporal": [{"role": "data", "years": [year], "references": [
            {"unit_id": unit["id"], "quote": unit["text"]}]}]}
        for unit in payload["units"] for year, fee in [(2024, 100), (2025, 120), (2026, 140)]
        if f"Học phí năm {year}:" in unit["text"]]
    return WikiGeneration(pages=[{"kind": page["kind"], "title": page["title"], "sections": sections}
                                 for page in payload["analysis"]["pages"]])


@pytest.mark.asyncio
async def test_unchanged_revision_reuses_wiki_without_inference():
    from sqlalchemy.engine import make_url

    from app.core.config import settings

    url = make_url(settings.DATABASE_URL)
    if not (url.database or "").startswith("qnu_test_"):
        pytest.skip("Requires an isolated qnu_test_ database")
    assert settings.ENVIRONMENT == "test" and url.host in {"localhost", "127.0.0.1"}
    # Each pytest async test owns its event loop. Do not borrow pooled sockets
    # created in a previous test's loop from the application session factory.
    engine = create_async_engine(url, poolclass=NullPool, hide_parameters=True)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    suffix = uuid.uuid4().hex[:12]
    cid, bid, rid, iid = (prefix + suffix for prefix in ("wiki-col-", "wiki-bnd-", "wiki-src-", "wiki-idx-"))
    gid = "wiki-vg-" + suffix
    markdown = "# Trường thử nghiệm\n\n" + "\n\n".join(
        f"Học phí năm {year}: {fee} đồng." for year, fee in [(2024, 100), (2025, 120), (2026, 140)])
    source = KnowledgeSourceRevision(id=rid, binding_id=bid, revision_no=1, status="ready",
        origin_document_id="wiki-doc-" + suffix,
        origin_file_hash="a" * 64, snapshot_storage_path="wiki-fixture.docx",
        snapshot_metadata={"title": "Nguồn ba năm"}, canonical_markdown=markdown,
        canonical_hash=hashlib.sha256(markdown.encode()).hexdigest(),
        parse_provenance={"structured_artifact": build_source_artifact(markdown, 1, {}), "knowledge_wiki_policy": {}})
    try:
        async with factory() as db:
            db.add(KnowledgeCollection(id=cid, name="Wiki fixture", module_code="general"))
            await db.flush()
            db.add(KnowledgeBinding(id=bid, collection_id=cid, status="active"))
            await db.flush()
            db.add(source)
            await db.commit()
            with patch("app.modules.knowledge.services.wiki_build.model_generator",
                       AsyncMock(return_value=fixture_generator)) as model:
                chunks = await chunk_set_service.get_or_create_chunk_set(db, rid)
                repeated = await chunk_set_service.get_or_create_chunk_set(db, rid)
                assert chunks.id == repeated.id and model.await_count == 1
                values = {col.key: getattr(source, col.key) for col in source.__table__.columns
                          if col.key not in {"id", "created_at", "updated_at", "revision_no"}}
                db.add(KnowledgeSourceRevision(id=rid+"-copy", revision_no=2, **values))
                await db.commit()
                cloned = await chunk_set_service.get_or_create_chunk_set(db, rid+"-copy")
                assert cloned.id != chunks.id
                assert model.await_count == 1, "Unchanged source must not call compiler again"
            saved_id = chunks.id
            assert chunks.chunk_config["_knowledge_wiki"]["calls"] == 2

        # A new session proves persistence instead of relying on mutated Python objects.
        async with factory() as db:
            source = await db.get(KnowledgeSourceRevision, rid)
            chunks = await db.get(KnowledgeChunkSet, saved_id)
            actor = SimpleNamespace(permissions=["ai.knowledge.view"])
            view = await read_revision_pages(db, cid, bid, rid, actor)
            assert view["status"] == "ready" and len(view["pages"]) == 3
            assert view["index_revision_id"] is None
            units = resolve_unit_manifest(markdown, source.parse_provenance["structured_artifact"])
            db.add(KnowledgeVectorGeneration(id=gid, collection_id=cid, embedding_model="fixture-only",
                provider_id="fixture-only", qdrant_collection_name=gid, config_hash=hashlib.sha256(gid.encode()).hexdigest(),
                embedding_dimension=3))
            await db.flush()
            index = KnowledgeIndexRevision(id=iid, binding_id=bid, source_revision_v2_id=rid,
                chunk_set_id=saved_id, vector_generation_id=gid, chunk_count=chunks.chunk_count, status="ready", revision_no=1,
                parity_report={"parity_passed": True, "knowledge_wiki": chunks.chunk_config["_knowledge_wiki"]})
            db.add(index)
            await db.commit()
            snap = RetrievalSnapshot(snapshot_id="candidate-wiki", collection_id=cid,
                binding_revisions={bid: iid}, knowledge_wiki_enabled=True)
            assert await load_published_blocks(db, snap) == []  # Staging is not published.
            blocks = await load_published_blocks(db, snap, candidate_mode=True)
            pages = await load_wiki_pages(db, snap, blocks, QueryPlan(query="Học phí", years=[2025]), True)
            assert len(pages) == 3
            assert all("120 đồng" in page["markdown"] and "100 đồng" not in page["markdown"]
                       and "140 đồng" not in page["markdown"] for page in pages)
            assert await load_wiki_pages(db, snap, blocks, QueryPlan(query="Học phí"), False) == []
            # Publication is simulated only in the isolated fixture DB; no vector call.
            index.status = "active"
            binding = await db.get(KnowledgeBinding, bid)
            binding.active_index_revision_id = iid
            await db.commit()
            published = await hybrid_retriever.resolve_retrieval_snapshot(db, cid)
            assert published.knowledge_wiki_enabled
            assert published.binding_revisions == {bid: iid}
            assert await load_wiki_pages(db, published, blocks, QueryPlan(query="Học phí", years=[2024]), False)
            # Draft source B and another collection's index cannot enter this snapshot.
            foreign = published.model_copy(update={"collection_id": cid + "-other"})
            assert await load_wiki_pages(db, foreign, blocks, QueryPlan(query="Học phí"), False) == []
            assert len(units.units) >= 4
    finally:
        try:
            async with factory() as db:
                binding = await db.get(KnowledgeBinding, bid)
                if binding:
                    binding.active_index_revision_id = None
                    await db.flush()
                await db.execute(delete(KnowledgeIndexRevision).where(KnowledgeIndexRevision.id == iid))
                await db.execute(delete(KnowledgeVectorGeneration).where(KnowledgeVectorGeneration.id == gid))
                await db.execute(delete(KnowledgeChunkSet).where(KnowledgeChunkSet.source_revision_id.in_([rid, rid+"-copy"])))
                await db.execute(delete(KnowledgeSourceRevision).where(KnowledgeSourceRevision.id.in_([rid, rid+"-copy"])))
                await db.execute(delete(KnowledgeBinding).where(KnowledgeBinding.id == bid))
                await db.execute(delete(KnowledgeCollection).where(KnowledgeCollection.id == cid))
                await db.commit()
        finally:
            await engine.dispose()
