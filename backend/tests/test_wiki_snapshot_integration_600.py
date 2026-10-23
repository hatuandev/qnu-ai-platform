"""Real owned PostgreSQL and ASGI handlers: no provider, vector, or publication writes."""

import asyncio
import uuid
from contextlib import asynccontextmanager
from copy import deepcopy
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import delete, event, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AppException, register_exception_handlers
from app.modules.auth.dependencies import get_current_actor
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeChunkSet,
    KnowledgeCollection,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
    KnowledgeVectorGeneration,
)
from app.modules.knowledge.services.chunk_set_service import chunk_set_service
from app.modules.knowledge.services.wiki_links import validate_page_links
from app.modules.knowledge.services.wiki_snapshot import load_snapshot_pages
from app.modules.knowledge.wiki_router import router
from app.modules.knowledge.wiki_schemas import WikiReadAction
from app.modules.rag.evidence_blocks import load_published_blocks
from app.modules.rag.evidence_schemas import QueryPlan
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.schemas import AskRequest
from app.modules.rag.wiki_context import read_wiki_context
from tests.test_wiki_links_600 import compile_source, source


@asynccontextmanager
async def fixture():
    url = make_url(settings.DATABASE_URL)
    if not (url.database or "").startswith(("qnu_test_context600_", "qnu_test_context601_", "qnu_test_context602_", "qnu_test_context603_", "qnu_test_context604_", "qnu_test_context606_")):
        pytest.skip("Requires this task's owned test database")
    assert settings.ENVIRONMENT == "test" and url.host in {"localhost", "127.0.0.1"}
    engine = create_async_engine(url, poolclass=NullPool, hide_parameters=True)
    async with engine.connect() as conn:
        owner = await conn.scalar(text("SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()"))
        context = (url.database or '').split('_')[2].removeprefix('context')
        assert owner and owner.startswith(f'context{context}:')
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    prefix = uuid.uuid4().hex[:12]
    cid = "w600-col-" + prefix
    items = []
    try:
        async with factory() as db:
            db.add(KnowledgeCollection(id=cid, name="Fixture nhiều nguồn", module_code="general"))
            await db.flush()
            generation_id = "w600-vg-" + prefix
            db.add(KnowledgeVectorGeneration(id=generation_id, collection_id=cid, embedding_model="fixture-only",
                provider_id="fixture-only", qdrant_collection_name=generation_id, config_hash="a" * 64,
                embedding_dimension=3))
            await db.flush()
            for number, year in enumerate((2024, 2025, 2026), 1):
                item = source(number, year, value=str(number * 100))
                item.id = f"w600-src-{prefix}-{number}"
                item.binding_id = f"w600-bnd-{prefix}-{number}"
                bundle, _ = await compile_source(item, year=year, collection_id=cid)
                db.add(KnowledgeBinding(id=item.binding_id, collection_id=cid, status="active"))
                await db.flush()
                revision = KnowledgeSourceRevision(**vars(item), snapshot_storage_path="fixture-only.docx")
                db.add(revision)
                await db.flush()
                index = KnowledgeIndexRevision(id=f"w600-idx-{prefix}-{number}", binding_id=item.binding_id,
                    vector_generation_id=generation_id,
                    source_revision_v2_id=item.id, revision_no=1, status="active", chunk_count=1,
                    parity_report={"parity_passed": True, "knowledge_wiki": bundle})
                db.add(index)
                await db.flush()
                binding = await db.get(KnowledgeBinding, item.binding_id)
                binding.active_index_revision_id, binding.active_source_revision_id = index.id, item.id
                items.append((revision, index, binding))
            await db.commit()
        yield factory, cid, items, engine
    finally:
        async with factory() as db:
            bindings = [row[2].id for row in items]
            for bid in bindings:
                binding = await db.get(KnowledgeBinding, bid)
                if binding:
                    binding.active_index_revision_id = binding.active_source_revision_id = None
            await db.flush()
            await db.execute(delete(KnowledgeIndexRevision).where(KnowledgeIndexRevision.binding_id.in_(bindings)))
            await db.execute(delete(KnowledgeVectorGeneration).where(KnowledgeVectorGeneration.collection_id == cid))
            await db.execute(delete(KnowledgeChunkSet).where(KnowledgeChunkSet.source_revision_id.in_(
                select(KnowledgeSourceRevision.id).where(KnowledgeSourceRevision.binding_id.in_(bindings)))))
            await db.execute(delete(KnowledgeSourceRevision).where(KnowledgeSourceRevision.binding_id.in_(bindings)))
            await db.execute(delete(KnowledgeBinding).where(KnowledgeBinding.collection_id == cid))
            await db.execute(delete(KnowledgeCollection).where(KnowledgeCollection.id == cid))
            await db.commit()
        await engine.dispose()


@pytest.mark.asyncio
async def test_handler_auth_backlinks_source_scope_and_get_never_writes_or_calls_model():
    async with fixture() as (factory, cid, items, engine):
        app = FastAPI()
        register_exception_handlers(app)
        app.include_router(router)
        actor = AuthActor(username="fixture", permissions=["ai.knowledge.view"])

        async def database():
            async with factory() as db:
                yield db

        app.dependency_overrides[get_db] = database
        app.dependency_overrides[get_current_actor] = lambda: actor
        statements = []
        event.listen(engine.sync_engine, "before_cursor_execute", lambda _conn, _cursor, statement, *_: statements.append(statement))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://fixture") as client:
            route = f"/collections/{cid}/knowledge-map"
            with patch("app.modules.modelops.service.modelops_service.generate", AsyncMock(side_effect=AssertionError("GET called model"))) as model:
                response = await client.get(route)
                assert response.status_code == 200
                data = response.json()
                assert len(data["pages"]) == 6 and all(e["status"] == "structural" for e in data["graph"]["links"])
                assert len([e for e in data["graph"]["links"] if e["relation"] == "co_mention"]) == 3
                for edge in data["graph"]["links"]:
                    assert edge["id"] in data["graph"]["outgoing"][edge["source"]]
                    assert edge["id"] in data["graph"]["backlinks"][edge["target"]]
                denied = await client.get(route + "/review")
                assert denied.status_code == 403
                actor.permissions.append("ai.knowledge.review")
                advanced = await client.get(route + "/review")
                assert advanced.status_code == 200
                assert any(i["code"] == "SHARED_LABEL_NOT_IDENTITY" for i in advanced.json()["issues"])
                revision, _, binding = items[0]
                reviewed = await client.get(f"/collections/{cid}/sources/{binding.id}/revisions/{revision.id}/knowledge-pages/review")
                assert reviewed.status_code == 200
                actor.permissions.clear()
                assert (await client.get(route)).status_code == 403
                model.assert_not_awaited()
        assert not any(s.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER")) for s in statements)


@pytest.mark.asyncio
async def test_update_remove_rollback_and_foreign_or_draft_never_mix_snapshots():
    async with fixture() as (factory, cid, items, _engine), factory() as db:
        old = await hybrid_retriever.resolve_retrieval_snapshot(db, cid)
        pages = await load_snapshot_pages(db, old)
        from app.modules.knowledge.services.wiki_links import build_page_links

        graph = build_page_links(pages, old.cache_fingerprint())
        revision, index, binding = items[0]
        saved = deepcopy(index.parity_report)
        binding = await db.get(KnowledgeBinding, binding.id)
        binding.status = "paused"
        await db.commit()
        current = await hybrid_retriever.resolve_retrieval_snapshot(db, cid)
        current_pages = await load_snapshot_pages(db, current)
        assert all(p["binding_id"] != binding.id for p in current_pages)
        with pytest.raises(AppException, match="Phạm vi phục vụ"):
            await load_snapshot_pages(db, old)
        with pytest.raises(AppException): validate_page_links(graph, current_pages, current.cache_fingerprint())
        binding.status = "active"
        index_row = await db.get(KnowledgeIndexRevision, index.id)
        index_row.status = "ready"
        binding.active_index_revision_id = None
        await db.commit()
        with pytest.raises(AppException):
            await load_snapshot_pages(db, old)
        candidate = old.model_copy(update={"binding_revisions": {binding.id: index.id}})
        assert len(await load_snapshot_pages(db, candidate, candidate_mode=True)) == 2
        foreign = old.model_copy(update={"collection_id": cid + "-foreign"})
        with pytest.raises(AppException):
            await load_snapshot_pages(db, foreign, candidate_mode=True)
        index_row.status = "active"
        binding.active_index_revision_id = index.id
        await db.commit()
        rollback = await hybrid_retriever.resolve_retrieval_snapshot(db, cid)
        assert build_page_links(await load_snapshot_pages(db, rollback), rollback.cache_fingerprint()) == graph
        assert (await db.get(KnowledgeIndexRevision, index.id)).parity_report == saved
        assert (await db.get(KnowledgeSourceRevision, revision.id)).canonical_hash == revision.canonical_hash
        changed, changed_index = await create_changed_revision(db, cid, revision, index)
        binding.active_source_revision_id = changed.id
        await db.commit()
        staging_pages = await load_snapshot_pages(db, rollback)
        assert all(p["source_revision_id"] != changed.id for p in staging_pages)
        index_row.status, changed_index.status = "archived", "active"
        binding.active_index_revision_id = changed_index.id
        collection = await db.get(KnowledgeCollection, cid)
        collection.index_epoch += 1
        await db.commit()
        updated = await hybrid_retriever.resolve_retrieval_snapshot(db, cid)
        updated_pages = await load_snapshot_pages(db, updated)
        assert {p["source_revision_id"] for p in updated_pages if p["binding_id"] == binding.id} == {changed.id}
        assert all("2027" in p["markdown"] for p in updated_pages if p["binding_id"] == binding.id)
        with pytest.raises(AppException):
            validate_page_links(graph, updated_pages, updated.cache_fingerprint())
        binding.active_source_revision_id, binding.active_index_revision_id = revision.id, index.id
        index_row.status, changed_index.status = "active", "archived"
        collection.index_epoch += 1
        await db.commit()
        restored = await hybrid_retriever.resolve_retrieval_snapshot(db, cid)
        restored_pages = await load_snapshot_pages(db, restored)
        assert {p["id"] for p in restored_pages} == {p["id"] for p in pages}
        assert (await db.get(KnowledgeIndexRevision, index.id)).parity_report == saved

@pytest.mark.asyncio
async def test_cached_navigation_rechecks_revocation_even_with_stale_blocks():
    async with fixture() as (factory, cid, items, _engine), factory() as db:
        _revision, index, binding = items[0]
        current = await hybrid_retriever.resolve_retrieval_snapshot(db, cid)
        snapshot = current.model_copy(update={"binding_revisions": {binding.id: index.id}})
        blocks = await load_published_blocks(db, snapshot)
        pages = await load_snapshot_pages(db, snapshot)
        selected = next(p for p in pages if p["kind"] == "entity")
        req = AskRequest(collection_id=cid, question="Viện thử nghiệm")
        action = AsyncMock(return_value=WikiReadAction(action="read_pages", page_ids=[selected["id"]]))
        with patch("app.modules.rag.wiki_context.structured_call", action):
            result = await read_wiki_context(db, req, snapshot, QueryPlan(query=req.question), blocks, candidate_mode=False)
            assert result and req._wiki_context["selected_pages"]
            binding = await db.get(KnowledgeBinding, binding.id)
            binding.active_index_revision_id = None
            await db.commit()
            with pytest.raises(AppException) as stale:
                await read_wiki_context(db, req, snapshot, QueryPlan(query=req.question), blocks, candidate_mode=False)
            assert stale.value.code == "KNOWLEDGE_WIKI_SCOPE_CHANGED"
            assert not req._wiki_context
            action.assert_awaited_once()

@pytest.mark.asyncio
async def test_concurrent_retry_and_late_old_revision_job_preserve_new_pointer():
    async with fixture() as (factory, cid, items, _engine):
        revision, index, binding = items[0]
        async with factory() as db:
            changed, changed_index = await create_changed_revision(db, cid, revision, index)
            current_binding = await db.get(KnowledgeBinding, binding.id)
            old_index = await db.get(KnowledgeIndexRevision, index.id)
            old_index.status, changed_index.status = "archived", "active"
            current_binding.active_source_revision_id = changed.id
            current_binding.active_index_revision_id = changed_index.id
            await db.commit()
            expected_pointer = changed_index.id
        # Independent sessions serialize against the source row; inference is a fixture only.
        async def build():
            async with factory() as db:
                return (await chunk_set_service.get_or_create_chunk_set(db, revision.id)).id

        # Select only this source's offered IDs. No inference or provider credentials.
        async def select(contract, _instruction, payload):
            from app.modules.knowledge.wiki_schemas import WikiSelection

            await asyncio.sleep(0.05)
            return WikiSelection(pages=[{"kind": "source", "title": payload["source"]["title"],
                "unit_ids": [u["id"] for u in payload["units"]]}])

        with patch("app.modules.knowledge.services.wiki_build.model_generator", AsyncMock(return_value=select)) as generator:
            ids = await asyncio.gather(build(), build())
            assert ids[0] == ids[1] and generator.await_count == 1
        async with factory() as db:
            assert (await db.get(KnowledgeBinding, binding.id)).active_index_revision_id == expected_pointer
            before = deepcopy((await db.get(KnowledgeIndexRevision, index.id)).parity_report)
            assert before["knowledge_wiki"]["source_revision_id"] == revision.id


async def create_changed_revision(db, cid, previous, previous_index):
    item = source(4, 2027, value="200")
    item.id, item.binding_id, item.revision_no = previous.id + "-v2", previous.binding_id, previous.revision_no + 1
    item.origin_document_id = previous.origin_document_id
    bundle, _ = await compile_source(item, year=2027, collection_id=cid)
    revision = KnowledgeSourceRevision(**vars(item), snapshot_storage_path="fixture-changed.docx")
    db.add(revision)
    await db.flush()
    index = KnowledgeIndexRevision(id=previous_index.id + "-v2", binding_id=item.binding_id,
        source_revision_v2_id=item.id, vector_generation_id=previous_index.vector_generation_id,
        revision_no=2, status="ready", chunk_count=1,
        parity_report={"parity_passed": True, "knowledge_wiki": bundle})
    db.add(index)
    await db.flush()
    return revision, index


@pytest.mark.asyncio
async def test_publication_change_during_map_read_returns_stale_instead_of_partial_graph():
    from app.modules.knowledge.services.wiki_snapshot import read_collection_map

    async with fixture() as (factory, cid, _items, _engine), factory() as db:
        actor = AuthActor(username="fixture", permissions=["ai.knowledge.view"])
        original = load_snapshot_pages

        async def changed_after_read(*args, **kwargs):
            pages = await original(*args, **kwargs)
            async with factory() as writer:
                collection = await writer.get(KnowledgeCollection, cid)
                collection.index_epoch += 1
                await writer.commit()
            return pages

        with patch("app.modules.knowledge.services.wiki_snapshot.load_snapshot_pages", changed_after_read), pytest.raises(AppException) as failure:
            await read_collection_map(db, cid, actor)
        assert failure.value.code == "STALE_RETRIEVAL_SNAPSHOT"


@pytest.mark.asyncio
async def test_canonical_text_and_span_must_match_before_a_page_can_be_ranked():
    from app.modules.rag.wiki_context import load_wiki_pages

    async with fixture() as (factory, cid, items, _engine), factory() as db:
        _revision, index, binding = items[0]
        snapshot = await hybrid_retriever.resolve_retrieval_snapshot(db, cid)
        snapshot = snapshot.model_copy(update={"binding_revisions": {binding.id: index.id}})
        blocks = await load_published_blocks(db, snapshot)
        assert await load_wiki_pages(db, snapshot, blocks, QueryPlan(query="Viện thử nghiệm"), False)
        forged = [block.model_copy(update={"text": block.text + " Extra grant of permission"}) for block in blocks]
        assert await load_wiki_pages(db, snapshot, forged, QueryPlan(query="Viện thử nghiệm"), False) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("years,numbers", [([2024, 2025, 2026], [1, 2, 3]), ([2025], [2])])
async def test_cross_source_reader_uses_original_spans_and_filters_year_before_expansion(years, numbers):
    from app.modules.rag.evidence_schemas import QuoteReference
    from app.modules.rag.evidence_validation import bind_quote

    async with fixture() as (factory, cid, items, _engine), factory() as db:
        snapshot = await hybrid_retriever.resolve_retrieval_snapshot(db, cid)
        blocks = await load_published_blocks(db, snapshot)
        pages = await load_snapshot_pages(db, snapshot)
        seed_binding = items[numbers[0] - 1][2].id
        seed = next(p for p in pages if p["binding_id"] == seed_binding and p["kind"] == "entity")
        req = AskRequest(collection_id=cid, question="Viện thử nghiệm")
        action = AsyncMock(return_value=WikiReadAction(action="read_pages", page_ids=[seed["id"]]))
        with patch("app.modules.rag.wiki_context.structured_call", action):
            selected = await read_wiki_context(db, req, snapshot, QueryPlan(query=req.question, years=years),
                                               blocks, candidate_mode=False)
        expected = {items[n - 1][2].id for n in numbers}
        assert {b.binding_id for b in selected} == expected
        assert req._retrieval_diagnostics["knowledge_wiki"]["linked_pages"] == len(numbers) - 1
        action.assert_awaited_once()
        originals = {revision.id: revision for revision, _, _ in items}
        for block in selected:
            ref = bind_quote(QuoteReference(block_id=block.id, quote=block.text), {b.id: b for b in selected})
            original = originals[ref["source_revision_id"]]
            assert original.canonical_markdown[ref["start"]:ref["end"]] == ref["quote"]
        rows = [b.text for b in selected if b.fact_context.get("source_kind") == "table" and "0007" in b.text]
        assert all(any(str(n * 100) in row for row in rows) for n in numbers)
