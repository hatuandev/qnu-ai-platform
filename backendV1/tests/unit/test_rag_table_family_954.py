"""Enumeration/count questions read every indexed chunk of the retrieved parent table."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from qnu.domains.knowledge.index.schemas import SearchResponse
from qnu.domains.knowledge.metadata import MetadataFilter
from qnu.domains.rag.answer import context
from qnu.domains.rag.answer.coverage import assess, plan_for
from qnu.domains.rag.answer.schemas import AnswerRequest, ModelAnswer, Statement
from qnu.domains.rag.answer.selection import question_needs
from qnu.domains.rag.answer.structure_context import (
    MAX_TABLE_FAMILY_CHUNKS,
    table_family_groups,
)
from tests.unit.test_answer_coverage_861 import sources
from tests.unit.test_rag_clause_context_856 import chunk

CITATION = "run:table1"


def table_chunk(
    index, indices, *, citation=CITATION, input_id="published", year=None, title="Quy chế"
):
    row = chunk(index, f"table fragment {index}", 1)
    row.kind = "table"
    row.input_id = input_id
    row.structure = {
        "source_table_citation": citation,
        "original_row_count": 30,
        "original_column_count": 2,
        "row_indices": list(indices),
        "rows": [
            [{"text": "Ngành"}, {"text": "Chỉ tiêu"}],
            [{"text": f"Ngành {index}"}, {"text": str(10 + index)}],
        ],
        "context": {"title": title},
    }
    if year is not None:
        row.structure["retrieval_metadata"] = [{"values": {"data_year": year}}]
    return row


def family(size=3):
    return [table_chunk(i, range(i * 10, i * 10 + 10)) for i in range(size)]


def test_enumeration_lists_every_chunk_of_the_retrieved_parent_table():
    rows = family()
    groups = table_family_groups(rows, sources([rows[1]]), [MetadataFilter()])
    assert [group["kind"] for group in groups] == ["table_family"]
    group = groups[0]
    assert group["primary_chunk_id"] == "1"
    assert group["required_ids"] == ["0", "1", "2"]
    assert group["units"] == [{"ref": CITATION, "chunk_ids": [str(i)]} for i in range(3)]
    assert group["label"] == "Ngành | Chỉ tiêu"
    assert group["truncated"] is False


def test_other_tables_inputs_and_scopes_are_never_mixed_into_the_family():
    rows = family()
    other_table = table_chunk(3, [0, 1], citation="run:table2")
    other_input = table_chunk(4, [0, 1], input_id="other")
    rows += [other_table, other_input]
    group = table_family_groups(rows, sources([rows[0]]), [MetadataFilter()])[0]
    assert group["required_ids"] == ["0", "1", "2"]
    rows[0].structure["retrieval_metadata"] = [{"values": {"data_year": 2031}}]
    rows[1].structure["retrieval_metadata"] = [{"values": {"data_year": 2031}}]
    rows[2].structure["retrieval_metadata"] = [{"values": {"data_year": 2032}}]
    group = table_family_groups(rows, sources([rows[0]]), [MetadataFilter(data_year=2031)])[0]
    assert group["required_ids"] == ["0", "1"]


def test_family_without_a_second_in_scope_chunk_is_not_expanded():
    rows = family(1)
    rows[0].structure["retrieval_metadata"] = [{"values": {"data_year": 2031}}]
    rows += [table_chunk(5, [10, 11], year=2032)]
    assert table_family_groups(rows, sources(rows[:1]), [MetadataFilter(data_year=2031)]) == []
    assert table_family_groups(rows[:1], sources(rows[:1]), [MetadataFilter()]) == []


def test_a_family_above_the_bound_is_left_alone_instead_of_partially_claimed():
    rows = family(MAX_TABLE_FAMILY_CHUNKS + 1)
    assert table_family_groups(rows, sources([rows[0]]), [MetadataFilter()]) == []


def test_count_cue_distinguishes_a_row_count_from_a_metric_value():
    assert question_needs("Trường có bao nhiêu ngành đào tạo?")["count"] is True
    assert question_needs("Học phí ngành A là bao nhiêu?")["count"] is False
    assert question_needs("Có bao nhiêu chỉ tiêu?")["count"] is False
    assert question_needs("Liệt kê các ngành đào tạo")["count"] is False


def _db(rows):
    run = SimpleNamespace(
        id="run", status="completed", is_active=True, workspace_id="ws", collection_id="col"
    )
    return SimpleNamespace(
        get=AsyncMock(return_value=run),
        scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: rows)),
    )


def _patched(monkeypatch, rows):
    monkeypatch.setattr("qnu.domains.knowledge.publication.access.authorize", AsyncMock())
    monkeypatch.setattr(
        context, "_eligible", AsyncMock(return_value=([SimpleNamespace(id="published")], []))
    )
    monkeypatch.setattr(context, "manifest", AsyncMock(return_value={}))
    monkeypatch.setattr(context, "pinned_bundles", AsyncMock(return_value={}))
    by_id = {row.id: row for row in rows}

    async def hits(db, run, allowed, candidates, sealed):
        return sources([by_id[hit.payload["chunk_id"]] for hit in candidates])

    async def attach(db, blob, actor, workspace_id, collection_id, result, req):
        return result, {}

    monkeypatch.setattr(context, "_hits", hits)
    monkeypatch.setattr(context, "attach_table_support", attach)
    monkeypatch.setattr(context, "select_groups", lambda *args: [])


def _response(rows):
    return SearchResponse(
        index_run_id="run", generation=1, status="results", hits=sources(rows), eligible_documents=1
    )


@pytest.mark.asyncio
async def test_count_question_reads_the_parent_family_even_with_only_table_hits(monkeypatch):
    rows = family()
    for row in rows:
        row.point_id, row.text_sha256 = row.id, row.id
    _patched(monkeypatch, rows)
    expanded, trace = await context.expand_context(
        _db(rows),
        None,
        None,
        "ws",
        "col",
        _response(rows[1:2]),
        AnswerRequest(question="Trường có bao nhiêu ngành đào tạo?", context_max_bytes=100000),
    )
    assert trace["question_kind"] == "single_value"
    assert [group["kind"] for group in trace["structure"]["groups"]] == ["table_family"]
    assert {hit.chunk_id for hit in expanded.hits} == {"0", "1", "2"}
    assert [item["kind"] for item in trace["added"]] == ["table_family", "table_family"]


@pytest.mark.asyncio
async def test_metric_value_question_keeps_the_retrieved_table_fragment_only(monkeypatch):
    rows = family()
    for row in rows:
        row.point_id, row.text_sha256 = row.id, row.id
    _patched(monkeypatch, rows)
    expanded, trace = await context.expand_context(
        _db(rows),
        None,
        None,
        "ws",
        "col",
        _response(rows[1:2]),
        AnswerRequest(question="Học phí ngành A là bao nhiêu?", context_max_bytes=100000),
    )
    assert trace["status"] == "disabled"
    assert [hit.chunk_id for hit in expanded.hits] == ["1"]


@pytest.mark.asyncio
async def test_family_expansion_takes_what_fits_and_reports_the_rest(monkeypatch):
    rows = family()
    for row in rows:
        row.point_id, row.text_sha256 = row.id, row.id
    rows[0].text += " First chunk detail." * 30
    rows[2].text += " Third chunk detail." * 400
    _patched(monkeypatch, rows)
    primary = sources(rows[1:2])[0]
    budget = 2 + context.evidence_size(primary) + context.evidence_size(sources(rows[:1])[0]) + 1
    expanded, trace = await context.expand_context(
        _db(rows),
        None,
        None,
        "ws",
        "col",
        _response(rows[1:2]),
        AnswerRequest(question="Liệt kê các ngành đào tạo", context_max_bytes=budget),
    )
    assert [hit.chunk_id for hit in expanded.hits] == ["1", "0"]
    assert trace["expansion"]["skipped_budget"] >= 1
    assert [item["chunk_id"] for item in trace["added"]] == ["0"]


def test_coverage_counts_each_family_chunk_as_a_required_unit():
    rows = family()
    evidence = sources(rows[:2])
    group = {
        "kind": "table_family",
        "label": "Ngành | Chỉ tiêu",
        "units": [{"chunk_ids": [str(i)]} for i in range(3)],
    }
    draft = ModelAnswer(
        status="answered", statements=[Statement(text="Có các ngành.", evidence_ids=["E1"])]
    )
    report = assess(draft, evidence, {"structure": {"groups": [group]}})
    item = report.structures[0]
    assert (item.required_units, item.provided_units, item.cited_units) == (3, 2, 1)
    assert item.status == "partial"
    assert item.uncovered_evidence_ids == ["E2"]
    assert (
        plan_for(evidence, {"structure": {"groups": [group]}})["groups"][0]["unprovided_units"] == 1
    )
