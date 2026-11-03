import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from qnu.domains.knowledge.index.models import IndexChunk
from qnu.domains.knowledge.index.schemas import SearchHit, SearchResponse
from qnu.domains.rag.answer import context
from qnu.domains.rag.answer.clause_context import clause_groups
from qnu.domains.rag.answer.schemas import AnswerRequest
from qnu.domains.rag.answer.service import _pack_messages
from tests.unit.test_answer_composition_789 import documents, paragraph


def chunk(index, text, section, **ref):
    heading = f"Part {section}"
    return IndexChunk(
        id=str(index),
        input_id="published",
        ordinal=index,
        kind="paragraph",
        text=f"Rules\n{heading}\n{text}",
        structure={"context": {"part": 0, "title": "Rules", "heading": heading}},
        citations={
            f"run:{index}": {
                "kind": "block",
                "run_id": "run",
                "revision_id": "revision",
                "canonical_sha256": "hash",
                "path": f"pages[5].blocks[{index}]",
                **ref,
            }
        },
    )


def test_clause_crosses_compiled_sections_and_stops_at_next_clause():
    rows = [
        chunk(0, "2. The following conditions apply:", 1),
        chunk(1, "a) First condition;", 1),
        chunk(2, "b) Second condition;", 2),
        chunk(3, "c) Third condition.", 2),
        chunk(4, "3. The next clause.", 2),
    ]
    assert list(clause_groups(rows, {"1"})) == [rows[:4]]


@pytest.mark.parametrize("boundary", ["revision", "input", "block_gap", "wrong_point"])
def test_clause_does_not_guess_at_an_unverified_boundary(boundary):
    last = chunk(2, "b) Second condition.", 2)
    if boundary == "revision":
        last.citations["run:2"]["revision_id"] = "other"
    if boundary == "input":
        last.input_id = "other"
    if boundary == "block_gap":
        last.citations["run:2"]["path"] = "pages[5].blocks[3]"
    if boundary == "wrong_point":
        last.text = last.text.replace("b)", "c)")
    rows = [chunk(0, "2. Conditions:", 1), chunk(1, "a) First condition;", 1), last]
    assert list(clause_groups(rows, {"1"})) == []


def test_exact_envelope_keeps_clause_and_removes_only_optional_tail():
    docs = documents()
    primary, clause, extra = (
        paragraph(f"E{i}", [f"run:{ref}"], docs) for i, ref in enumerate("abc", 1)
    )
    primary.chunk_id, clause.chunk_id, extra.chunk_id = "primary", "clause", "optional"
    req = AnswerRequest(question="Which conditions apply?", context_max_bytes=32000)
    trace = {"added": [{"chunk_id": "clause", "kind": "clause"}, {"chunk_id": "optional"}]}
    _, _, _, size, _ = _pack_messages(req, [primary, clause], trace)
    sources = [primary, clause, extra]
    messages, _, _, used, skipped = _pack_messages(
        req.model_copy(update={"context_max_bytes": size}), sources, trace
    )
    assert used == size
    assert skipped == ["optional"]
    assert [item["evidence_id"] for item in json.loads(messages[-1].content)["evidence"]] == [
        "E1",
        "E2",
    ]


@pytest.mark.asyncio
async def test_expansion_adds_all_cited_points_with_window_disabled(monkeypatch):
    rows = [
        chunk(0, "2. Conditions:", 1),
        chunk(1, "a) First;", 1),
        chunk(2, "b) Second;", 2),
        chunk(3, "c) Third.", 2),
    ]
    for row in rows:
        row.point_id, row.text_sha256 = row.id, row.id

    def hit(row):
        return SearchHit(
            chunk_id=row.id,
            document_id="doc",
            version_id="version",
            publication_decision_id="published",
            score=1,
            kind=row.kind,
            text=row.text,
            structure=row.structure,
            citations=row.citations,
        )

    result = SearchResponse(
        index_run_id="run",
        generation=2,
        status="results",
        eligible_documents=1,
        hits=[hit(rows[1])],
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
        context, "_eligible", AsyncMock(return_value=([SimpleNamespace(id="published")], None))
    )
    monkeypatch.setattr(context, "manifest", AsyncMock(return_value={}))
    validate_hits = AsyncMock(return_value=[hit(rows[i]) for i in (0, 2, 3)])
    monkeypatch.setattr(context, "_hits", validate_hits)
    expanded, trace = await context.expand_context(
        db, None, None, "ws", "col", result, AnswerRequest(question="Conditions?")
    )
    assert [h.chunk_id for h in expanded.hits] == ["1", "0", "2", "3"]
    assert {item["kind"] for item in trace["added"]} == {"clause"}
    assert [item.point_id for item in validate_hits.await_args.args[3]] == ["0", "2", "3"]
