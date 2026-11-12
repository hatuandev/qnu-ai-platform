"""G1 regressions: whole-table sibling reassembly and per-facet evidence caps."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from qnu.domains.knowledge.index.schemas import SearchRequest, SearchResponse
from qnu.domains.rag.answer import context, retrieval
from qnu.domains.rag.answer.schemas import AnswerRequest, EvidenceSource
from tests.unit.test_answer_coverage_861 import sources
from tests.unit.test_rag_clause_context_856 import chunk

TABLE_PARENT = "table:ocr:ev_shared"


def _mixed_rows():
    rows = [
        chunk(0, "Narrative anchor for the question.", 1),
        chunk(1, "Header rows 0-2 of the shared table.", 1),
        chunk(2, "Middle rows 3-8 of the shared table.", 1),
        chunk(3, "Answer rows 9-14 with the target value 127.", 1),
    ]
    for index, row in enumerate(rows):
        row.point_id, row.text_sha256 = row.id, row.id
        if index:
            row.kind = "table"
            row.structure["context"].update(parent=TABLE_PARENT, position=index - 1)
    return rows


def _expansion_db(monkeypatch, rows):
    run = SimpleNamespace(
        id="run", status="completed", is_active=True, workspace_id="ws", collection_id="col"
    )
    db = SimpleNamespace(
        get=AsyncMock(return_value=run),
        scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: rows)),
    )
    monkeypatch.setattr("qnu.domains.knowledge.publication.access.authorize", AsyncMock())
    monkeypatch.setattr(
        context, "_eligible", AsyncMock(return_value=([SimpleNamespace(id="published")], []))
    )
    monkeypatch.setattr(context, "manifest", AsyncMock(return_value={}))
    monkeypatch.setattr(context, "pinned_bundles", AsyncMock(return_value={}))
    monkeypatch.setattr(context, "select_groups", lambda *args: [])
    monkeypatch.setattr(context, "continuation_groups", lambda *args: [])
    by_id = {row.id: row for row in rows}

    async def hits(db, run, allowed, candidates, sealed):
        return sources([by_id[hit.payload["chunk_id"]] for hit in candidates])

    monkeypatch.setattr(context, "_hits", hits)
    return db


@pytest.mark.asyncio
async def test_table_primary_reassembles_every_fragment_of_the_same_table(monkeypatch):
    rows = _mixed_rows()
    db = _expansion_db(monkeypatch, rows)
    result = SearchResponse(
        index_run_id="run",
        generation=1,
        status="results",
        hits=sources(rows[:2]),
        eligible_documents=1,
    )
    expanded, trace = await context.expand_context(
        db,
        None,
        None,
        "ws",
        "col",
        result,
        AnswerRequest(question="Giá trị mục tiêu là bao nhiêu?", context_window=0),
    )
    assert trace["effective_window"] == 1
    assert [hit.chunk_id for hit in expanded.hits] == ["0", "1", "2", "3"]
    assert {"chunk_id": "3", "primary_chunk_id": "1", "parent": TABLE_PARENT} in trace["added"]


@pytest.mark.asyncio
async def test_paragraph_primary_keeps_the_bounded_window(monkeypatch):
    rows = [chunk(i, f"Paragraph {i} of one section.", 1) for i in range(5)]
    for index, row in enumerate(rows):
        row.point_id, row.text_sha256 = row.id, row.id
        row.structure["context"].update(parent="section:1", position=index)
    db = _expansion_db(monkeypatch, rows)
    result = SearchResponse(
        index_run_id="run",
        generation=1,
        status="results",
        hits=sources(rows[2:3]),
        eligible_documents=1,
    )
    expanded, trace = await context.expand_context(
        db,
        None,
        None,
        "ws",
        "col",
        result,
        AnswerRequest(question="Giá trị mục tiêu là bao nhiêu?", context_window=0),
    )
    assert [hit.chunk_id for hit in expanded.hits] == ["2", "1", "3"]
    assert trace["skipped_budget"] == 0


@pytest.mark.asyncio
async def test_whole_table_expansion_still_respects_the_byte_budget(monkeypatch):
    rows = _mixed_rows()
    db = _expansion_db(monkeypatch, rows)
    primaries = sources(rows[:2])
    result = SearchResponse(
        index_run_id="run", generation=1, status="results", hits=primaries, eligible_documents=1
    )
    middle = sources([rows[2]])[0]
    budget = 2 + sum(context.evidence_size(hit) for hit in primaries)
    budget += context.evidence_size(middle) + 8
    expanded, trace = await context.expand_context(
        db,
        None,
        None,
        "ws",
        "col",
        result,
        AnswerRequest(
            question="Giá trị mục tiêu là bao nhiêu?", context_window=0, context_max_bytes=budget
        ),
    )
    assert [hit.chunk_id for hit in expanded.hits] == ["0", "1", "2"]
    assert trace["skipped_budget"] == 1
    assert trace["bytes_used"] <= budget


def _facet_hits(prefix, count):
    return [
        EvidenceSource(
            evidence_id=f"{prefix}{i}",
            chunk_id=f"{prefix}{i}",
            document_id="doc",
            version_id="v",
            publication_decision_id="pub",
            score=1,
            kind="paragraph",
            text=f"Evidence {prefix}{i}",
            citations={},
            structure=None,
        )
        for i in range(count)
    ]


def _facet_response(hits):
    return SearchResponse(
        index_run_id="idx", generation=1, status="results", hits=hits, eligible_documents=1
    )


FACET_QUESTION = (
    "Công thức tính điểm tổng hợp Q là gì và các biến A, B, C đại diện cho những đại lượng nào?"
)


@pytest.mark.asyncio
async def test_each_question_clause_keeps_its_own_retrieved_top_k(monkeypatch):
    first, second = _facet_hits("F1_", 5), _facet_hits("F2_", 5)
    mock = AsyncMock(side_effect=[_facet_response(first), _facet_response(second)])
    monkeypatch.setattr(retrieval, "search_single", mock)
    req = SearchRequest(query=FACET_QUESTION, top_k=5)
    result = await retrieval.search(None, None, None, None, None, "ws", "col", req)
    ids = [hit.chunk_id for hit in result.hits]
    assert ids == [
        "F1_0",
        "F2_0",
        "F1_1",
        "F2_1",
        "F1_2",
        "F2_2",
        "F1_3",
        "F2_3",
        "F1_4",
        "F2_4",
    ]
    assert result.trace["selected_ids"] == ids
    assert mock.await_count == 2


@pytest.mark.asyncio
async def test_shared_evidence_between_clauses_is_deduplicated(monkeypatch):
    first = _facet_hits("F1_", 3)
    second = [first[0], *_facet_hits("F2_", 2)]
    mock = AsyncMock(side_effect=[_facet_response(first), _facet_response(second)])
    monkeypatch.setattr(retrieval, "search_single", mock)
    req = SearchRequest(query=FACET_QUESTION, top_k=3)
    result = await retrieval.search(None, None, None, None, None, "ws", "col", req)
    ids = [hit.chunk_id for hit in result.hits]
    assert ids == ["F1_0", "F1_1", "F2_0", "F1_2", "F2_1"]
