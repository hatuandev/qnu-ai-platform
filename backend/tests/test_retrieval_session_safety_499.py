"""Retrieval uses the caller's AsyncSession sequentially; vector I/O stays parallel."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.schemas import RetrievalSnapshot


def snapshot():
    return RetrievalSnapshot(snapshot_id="snapshot", collection_id="collection",
                             binding_revisions={"binding": "revision"})


def hit(key):
    return {"chunk_id": key, "document_id": "doc", "content": key,
            "binding_id": "binding", "index_revision_id": "revision"}


@pytest.mark.asyncio
async def test_all_lexical_queries_share_session_without_overlapping_and_keep_snapshot():
    active = 0
    overlap = []
    completed = []
    vector_started = asyncio.Event()
    lexical_started = asyncio.Event()
    snap, db = snapshot(), object()
    async def lexical(**kwargs):
        nonlocal active
        assert kwargs["db"] is db and kwargs["snapshot"] is snap
        query = str(kwargs["query"])
        if active:
            overlap.append(query)
            raise RuntimeError("another operation is in progress")
        active += 1
        lexical_started.set()
        try:
            await vector_started.wait()
            await asyncio.sleep(0.001)
            completed.append(query)
            return [hit(query)]
        finally:
            active -= 1
    async def dense(**kwargs):
        assert kwargs["snapshot"] is snap
        vector_started.set()
        await lexical_started.wait()  # Would deadlock if all retrieval were sequential.
        return [hit("dense")]
    trace = {}
    with (patch.object(hybrid_retriever, "search_sparse_fts", side_effect=lexical),
          patch("app.modules.rag.retriever.vector_indexer.search_dense", side_effect=dense)):
        result = await asyncio.wait_for(hybrid_retriever.retrieve(db, "collection", "original",
            sparse_variants=["variant one", "variant two"], glossary_queries=["term one", "term two"],
            snapshot=snap, reranker_policy={"enabled": False}, rerank_top_k=10, diagnostics=trace), timeout=2)
    assert overlap == []
    assert completed == ["original", "variant one", "variant two", "term one", "term two"]
    assert {item.chunk_id for item in result} == {"dense", *completed}
    assert trace["variant_hits"] == 4 and trace["degradations"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True])
async def test_failed_or_cancelled_lexical_search_cleans_up_vector_task(cancel):
    vector_started, vector_cancelled, lexical_started = asyncio.Event(), asyncio.Event(), asyncio.Event()
    async def dense(**kwargs):
        vector_started.set()
        try:
            await asyncio.Event().wait()
        finally:
            vector_cancelled.set()
    async def lexical(**kwargs):
        await vector_started.wait()
        lexical_started.set()
        if cancel:
            await asyncio.Event().wait()
        raise AppException("Database failure", code="TEST_DB_FAILURE", status_code=503)
    with (patch.object(hybrid_retriever, "search_sparse_fts", side_effect=lexical),
          patch("app.modules.rag.retriever.vector_indexer.search_dense", side_effect=dense)):
        task = asyncio.create_task(hybrid_retriever.retrieve(object(), "collection", "query",
            snapshot=snapshot(), reranker_policy={"enabled": False}))
        await asyncio.wait_for(lexical_started.wait(), timeout=2)
        if cancel:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            with pytest.raises(AppException) as error:
                await task
            assert error.value.code == "TEST_DB_FAILURE"
        assert vector_cancelled.is_set()


@pytest.mark.asyncio
async def test_variant_failure_remains_traced_and_later_queries_keep_their_order():
    calls = []
    async def lexical(**kwargs):
        query = str(kwargs["query"])
        calls.append(query)
        if query == "failed variant":
            raise RuntimeError("fixture failure")
        return [hit(query)]
    trace = {}
    with (patch.object(hybrid_retriever, "search_sparse_fts", side_effect=lexical),
          patch("app.modules.rag.retriever.vector_indexer.search_dense", AsyncMock(return_value=[]))):
        result = await hybrid_retriever.retrieve(object(), "collection", "original",
            snapshot=snapshot(), sparse_variants=["failed variant", "valid variant"],
            reranker_policy={"enabled": False}, diagnostics=trace)
    assert calls == ["original", "failed variant", "valid variant"]
    assert {item.chunk_id for item in result} == {"original", "valid variant"}
    assert trace["degradations"] == [{"stage": "lexical_variant", "error_type": "RuntimeError"}]
