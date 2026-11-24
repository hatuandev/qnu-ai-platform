import asyncio
from unittest.mock import AsyncMock

import pytest

from qnu.domains.knowledge.index.schemas import SearchRequest, SearchResponse
from qnu.domains.rag.answer import retrieval
from qnu.platform.errors import Conflict
from tests.unit.test_table_grounding_770 import source


@pytest.mark.parametrize(
    "query,count",
    [
        ("Compare years: What was the quota in 2028 and what is the rate in 2029?", 2),
        ("Theo bản ghi 2030, tổ A có bao nhiêu mẫu? Năm 2031 tổ B có bao nhiêu mẫu?", 2),
        ("Điều kiện A và B là gì?", 1),
        ("Compare 2028 and 2029", 1),
        ("Mức 2.5 và 3.5 quy đổi như thế nào?", 1),
        ("Nhóm Delta có bao nhiêu mẫu và tỷ lệ của nhóm này là bao nhiêu?", 2),
        ("What is the quota for robotics and what score does this program require?", 2),
    ],
)
def test_only_explicit_independent_questions_are_split(query, count):
    assert len(retrieval.question_facets(query)) == count


def test_referential_facet_keeps_the_whole_original_antecedent_without_guessing():
    query = "Nhóm Delta có bao nhiêu mẫu và tỷ lệ của nhóm này là bao nhiêu?"
    assert query in retrieval.question_facets(query)[1]


@pytest.mark.asyncio
async def test_facets_preserve_scope_filter_and_cap_context(monkeypatch):
    first, second = (
        source([["Name", "Value"], ["A", "10"]]),
        source([["Name", "Value"], ["B", "20"]], key="E2"),
    )
    mock = AsyncMock(
        side_effect=[
            SearchResponse(
                index_run_id="idx",
                generation=1,
                status="results",
                hits=[first],
                eligible_documents=1,
            ),
            SearchResponse(
                index_run_id="idx",
                generation=1,
                status="results",
                hits=[second],
                eligible_documents=1,
            ),
        ]
    )
    monkeypatch.setattr(retrieval, "search_single", mock)
    req = SearchRequest(
        query="How many samples did team A collect? How many samples did team B collect?",
        top_k=2,
        document_ids=["doc"],
        metadata_filter={"data_year": 2031},
    )
    result = await retrieval.search(None, None, None, None, None, "ws", ["col"], req)
    assert [h.chunk_id for h in result.hits] == ["E1", "E2"]
    for call in mock.call_args_list:
        scoped = call.args[-1]
        assert scoped.document_ids == ["doc"] and scoped.metadata_filter == req.metadata_filter
    assert mock.await_count == 2  # distinct facets, no retry


@pytest.mark.asyncio
async def test_answer_retrieval_forwards_skipped_final_validation(monkeypatch):
    mock = AsyncMock(
        return_value=SearchResponse(
            index_run_id="idx", generation=1, status="no_match", eligible_documents=1, hits=[]
        )
    )
    monkeypatch.setattr(retrieval, "search_single", mock)
    req = SearchRequest(query="What is the quota?", top_k=2)
    await retrieval.search(None, None, None, None, None, "ws", ["col"], req, verify=False)
    assert mock.await_args.kwargs["verify"] is False


@pytest.mark.asyncio
async def test_generation_change_between_facets_blocks(monkeypatch):
    monkeypatch.setattr(
        retrieval,
        "search_single",
        AsyncMock(
            side_effect=[
                SearchResponse(
                    index_run_id="a", generation=1, status="no_match", eligible_documents=1, hits=[]
                ),
                SearchResponse(
                    index_run_id="b", generation=2, status="no_match", eligible_documents=1, hits=[]
                ),
            ]
        ),
    )
    req = SearchRequest(
        query="What is the population of city A? What is the population of city B?", top_k=2
    )
    with pytest.raises(Conflict):
        await retrieval.search(None, None, None, None, None, "ws", ["col"], req)


@pytest.mark.asyncio
async def test_facets_execute_concurrently_and_preserve_order(monkeypatch):
    first, second = (
        source([["Name", "Value"], ["A", "10"]], key="E1"),
        source([["Name", "Value"], ["B", "20"]], key="E2"),
    )
    active = 0
    max_active = 0

    async def fake_search_single(_db, _blob, _model, _vectors, _actor, _ws, _col, scoped, **_kw):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.05)
        active -= 1
        hit = first if "team A" in scoped.query else second
        return SearchResponse(
            index_run_id="idx",
            generation=1,
            status="results",
            hits=[hit],
            eligible_documents=1,
        )

    monkeypatch.setattr(retrieval, "search_single", fake_search_single)
    req = SearchRequest(
        query="How many samples did team A collect? How many samples did team B collect?",
        top_k=2,
    )
    result = await retrieval.search(None, None, None, None, None, "ws", ["col"], req)
    assert max_active == 2
    assert [h.chunk_id for h in result.hits] == ["E1", "E2"]

