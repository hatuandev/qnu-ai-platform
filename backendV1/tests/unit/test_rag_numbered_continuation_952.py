"""Q12: an anchored numbered exception list is read whole, bounded by its source."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from qnu.domains.knowledge.index.schemas import SearchResponse
from qnu.domains.rag.answer import context, structure_context
from qnu.domains.rag.answer.schemas import AnswerRequest
from tests.unit.test_answer_coverage_861 import corpus, sources
from tests.unit.test_rag_clause_context_856 import chunk

TEXTS = [
    "II.2. Ngoại lệ nhóm B – minh chứng thực tập ngoài trường",
    "1. Được phép sử dụng biên bản xác minh trực tuyến do Phòng",
    "Hợp tác doanh nghiệp lập và có xác nhận của đơn vị.",
    "2. Được phép sử dụng chứng chỉ hành nghề còn hiệu lực.",
    "3. Trường hợp hồ sơ thiếu minh chứng, cán bộ ghi",
    "thái trở về “Cần bổ sung hồ sơ” và hẹn bổ sung.",
    "Bảng 10. Ma trận ngoại lệ minh chứng thực tập.",
]


def numbered_corpus(texts=TEXTS):
    rows = [chunk(index, text, 4) for index, text in enumerate(texts)]
    _, bundles = corpus()
    bundles["version"].documents[0]["pages"] = [
        {
            "page_number": 18,
            "blocks": [{"evidence_id": str(i), "text": text} for i, text in enumerate(texts)],
        }
    ]
    return rows, bundles


def test_numbered_exception_list_completes_from_an_anchored_item():
    rows, bundles = numbered_corpus()
    groups = structure_context.numbered_groups(rows, sources(rows[1:2]), bundles)
    assert len(groups) == 1
    group = groups[0]
    assert group["kind"] == "continuation"
    assert group["basis"] == "numbered_list"
    assert group["optional"] is True
    assert group["primary_chunk_id"] == "1"
    assert group["required_ids"] == ["1", "2", "3", "4", "5"]
    assert [unit["chunk_ids"] for unit in group["units"]] == [["1", "2"], ["3"], ["4", "5"]]


def test_numbered_run_stops_at_a_caption_and_at_a_gap_in_numbering():
    rows, bundles = numbered_corpus()
    group = structure_context.numbered_groups(rows, sources(rows[4:5]), bundles)[0]
    assert group["required_ids"] == ["1", "2", "3", "4", "5"]
    assert "6" not in group["required_ids"]

    texts = ["1. First rule.", "2. Second rule.", "4. Skipped rule.", "5. Last rule."]
    rows, bundles = numbered_corpus(texts)
    group = structure_context.numbered_groups(rows, sources(rows[0:1]), bundles)[0]
    assert group["required_ids"] == ["0", "1"]


def test_a_lone_numbered_sentence_does_not_expand():
    rows, bundles = numbered_corpus(["1. Only rule.", "Bảng 1. Caption."])
    assert structure_context.numbered_groups(rows, sources(rows[0:1]), bundles) == []


def prepare(monkeypatch, rows, bundles):
    for row in rows:
        row.point_id, row.text_sha256 = row.id, row.id
    result = SearchResponse(
        index_run_id="run",
        generation=1,
        status="results",
        hits=sources(rows[1:2]),
        eligible_documents=1,
    )
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
    monkeypatch.setattr(context, "pinned_bundles", AsyncMock(return_value=bundles))
    by_id = {row.id: row for row in rows}

    async def hits(db, run, allowed, candidates, sealed):
        return sources([by_id[hit.payload["chunk_id"]] for hit in candidates])

    monkeypatch.setattr(context, "_hits", hits)
    return db, result


@pytest.mark.asyncio
async def test_condition_question_reads_the_whole_numbered_list(monkeypatch):
    rows, bundles = numbered_corpus()
    db, result = prepare(monkeypatch, rows, bundles)
    expanded, trace = await context.expand_context(
        db,
        None,
        None,
        "ws",
        "col",
        result,
        AnswerRequest(
            question="Trường hợp hồ sơ thiếu minh chứng được xử lý thế nào?",
            context_max_bytes=32000,
            context_window=0,
        ),
    )
    assert [hit.chunk_id for hit in expanded.hits] == ["1", "2", "3", "4", "5"]
    assert [item["chunk_id"] for item in trace["added"]] == ["2", "3", "4", "5"]
    assert trace["structure"]["groups"][-1]["basis"] == "numbered_list"


@pytest.mark.asyncio
async def test_general_question_does_not_read_the_numbered_list(monkeypatch):
    rows, bundles = numbered_corpus()
    db, result = prepare(monkeypatch, rows, bundles)
    expanded, trace = await context.expand_context(
        db,
        None,
        None,
        "ws",
        "col",
        result,
        AnswerRequest(question="Explain the rule.", context_max_bytes=32000, context_window=0),
    )
    assert {hit.chunk_id for hit in expanded.hits} == {"1", "2"}
    assert {item["chunk_id"] for item in trace["added"]} == {"2"}
