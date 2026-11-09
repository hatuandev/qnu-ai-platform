"""Source-bound context reduction and complete units, without live inference."""

import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from qnu.domains.knowledge.index.schemas import SearchResponse
from qnu.domains.rag.answer import context
from qnu.domains.rag.answer.cells import materialize
from qnu.domains.rag.answer.coverage import assess
from qnu.domains.rag.answer.drafting import parse_answer
from qnu.domains.rag.answer.schemas import AnswerRequest, ModelAnswer, Statement
from qnu.domains.rag.answer.service import _pack_messages
from qnu.domains.rag.answer.structure_context import continuation_groups, select_groups
from qnu.platform.errors import AppException
from tests.unit.test_answer_coverage_861 import corpus, sources
from tests.unit.test_rag_clause_context_856 import chunk
from tests.unit.test_table_grounding_770 import source


def pack(tables, question, **options):
    return _pack_messages(
        AnswerRequest(question=question, context_max_bytes=100000),
        tables,
        {},
        **options,
    )


def values(messages):
    return {
        value
        for table in json.loads(messages[-1].content).get("tables", [])
        for row in table["rows"]
        for value in row["cells"].values()
    }


def test_named_row_keeps_every_field_and_original_proof_without_other_rows():
    table = source(
        [
            ["Device", "Cost", "Unit", "Condition"],
            ["Marine sensor", "12", "million", "Calibration included"],
            ["Optical sensor", "18", "million", "Calibration excluded"],
        ]
    )
    original = copy.deepcopy(table)
    messages, cells, *_ = pack([table], "How much does Marine sensor cost?")
    assert values(messages) == {"12", "million", "Calibration included"}
    assert {c["cell_id"] for t in cells["tables"] for c in t["cells"]} == {
        "E1:r1:k1",
        "E1:r1:k2",
        "E1:r1:k3",
    }
    assert all(c["source_cells"] for t in cells["tables"] for c in t["cells"])
    assert table == original


@pytest.mark.parametrize("question", ["What are all device costs?", "How much is the sensor?"])
def test_unknown_or_ambiguous_subject_keeps_the_catalog(question):
    table = source([["Device", "Cost"], ["Marine sensor", "12"], ["Optical sensor", "18"]])
    assert values(pack([table], question)[0]) == {"12", "18"}


def test_enumeration_does_not_treat_an_example_subject_as_a_filter():
    table = source([["Device", "Cost"], ["Marine sensor", "12"], ["Optical sensor", "18"]])
    messages, *_ = pack([table], "List all device costs including Marine sensor")
    assert values(messages) == {"12", "18"}


def test_unselected_cell_cannot_be_guessed_back_into_the_answer():
    table = source([["Device", "Cost"], ["Marine sensor", "12"], ["Optical sensor", "18"]])
    _, cells, *_ = pack([table], "How much does Marine sensor cost?")
    draft = parse_answer(
        json.dumps({"status": "answered", "statements": [], "lookups": [{"cell_id": "E1:r2:k1"}]}),
        [table],
    )
    with pytest.raises(AppException) as caught:
        materialize(draft, [table], cells)
    assert caught.value.code == "answer_cell_invalid"


def test_resolved_question_and_longest_subject_match_do_not_select_prefix_names():
    table = source([["Device", "Cost"], ["Sensor", "12"], ["Sensor array", "18"]])
    messages, *_ = pack(
        [table], "How much does it cost?", resolved_question="How much does Sensor array cost?"
    )
    assert values(messages) == {"18"}


def test_two_named_subjects_and_publication_boundaries_are_preserved():
    table = source([["Device", "Cost"], ["Marine sensor", "12"], ["Optical sensor", "18"]])
    other = source([["Device", "Cost"], ["Thermal sensor", "25"]], key="E2")
    other.version_id = "other"
    messages, *_ = pack([table, other], "Compare Marine sensor and Optical sensor costs")
    assert values(messages) == {"12", "18", "25"}


def test_one_named_subject_does_not_hide_the_comparison_population():
    table = source([["Device", "Cost"], ["Marine sensor", "12"], ["Optical sensor", "18"]])
    messages, *_ = pack([table], "Does Marine sensor have the highest cost?")
    assert values(messages) == {"12", "18"}


def test_an_unused_continuation_does_not_create_a_missing_answer_requirement():
    evidence = sources(corpus()[0][:3])
    group = {
        "kind": "continuation",
        "label": "Another independent sentence",
        "units": [{"chunk_ids": [s.chunk_id]} for s in evidence[1:]],
    }
    draft = ModelAnswer(
        status="answered", statements=[Statement(text="A cited fact.", evidence_ids=["E1"])]
    )
    assert not assess(draft, evidence, {"structure": {"groups": [group]}}).structures
    draft.statements[0].evidence_ids = ["E2"]
    assert (
        assess(draft, evidence, {"structure": {"groups": [group]}}).structures[0].status
        == "partial"
    )


def test_fragment_family_filters_only_with_a_shared_source_table():
    first = source([["Device", "Cost"], ["Marine sensor", "12"]], key="E1")
    second = source([["Device", "Cost"], ["Optical sensor", "18"]], key="E2")
    messages, *_ = pack([first, second], "How much does Marine sensor cost?")
    assert values(messages) == {"12"}
    second.structure["source_table_citation"] = "ocr:unrelated"
    messages, *_ = pack([first, second], "How much does Marine sensor cost?")
    assert values(messages) == {"12", "18"}


def test_required_structure_is_not_removed_as_optional_when_packing():
    evidence = sources(corpus()[0][:2])
    evidence[0].text += " Source-bound context." * 20
    _, _, _, size, _ = _pack_messages(
        AnswerRequest(question="Article 4", context_max_bytes=100000), evidence[:1], {}
    )
    with pytest.raises(AppException) as caught:
        _pack_messages(
            AnswerRequest(question="Article 4", context_max_bytes=size),
            evidence,
            {"added": [{"chunk_id": evidence[1].chunk_id, "kind": "structure"}]},
        )
    assert caught.value.code == "answer_context_budget_exceeded"


@pytest.mark.asyncio
async def test_whole_article_exceeds_top_k_count_and_uses_resolved_question(monkeypatch):
    texts = ["Article 6. Conditions"] + [f"{i}. A distinct condition." for i in range(1, 25)]
    rows = [chunk(i, text, 1) for i, text in enumerate(texts)]
    for row in rows:
        row.point_id, row.text_sha256 = row.id, row.id
    hits = sources(rows[:1])
    result = SearchResponse(
        index_run_id="index", generation=1, status="results", hits=hits, eligible_documents=1
    )
    run = SimpleNamespace(
        id="index", status="completed", is_active=True, workspace_id="ws", collection_id="col"
    )
    db = SimpleNamespace(
        get=AsyncMock(return_value=run),
        scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: rows)),
    )
    group = {
        "kind": "article",
        "reference": "6",
        "label": texts[0],
        "primary_chunk_id": "0",
        "required_ids": [row.id for row in rows],
        "units": [{"ref": "run:" + row.id, "chunk_ids": [row.id]} for row in rows[1:]],
    }
    select = Mock()
    monkeypatch.setattr("qnu.domains.knowledge.publication.access.authorize", AsyncMock())
    monkeypatch.setattr(
        context, "_eligible", AsyncMock(return_value=([SimpleNamespace(id="published")], []))
    )
    monkeypatch.setattr(context, "manifest", AsyncMock(return_value={}))
    monkeypatch.setattr(context, "pinned_bundles", AsyncMock(return_value={}))
    monkeypatch.setattr(context, "select_groups", lambda *args: (select(*args), [group])[1])
    monkeypatch.setattr(context, "_hits", AsyncMock(return_value=sources(rows[1:])))
    expanded, trace = await context.expand_context(
        db,
        None,
        None,
        "ws",
        "col",
        result,
        AnswerRequest(question="And those?", context_max_bytes=100000),
        resolved_question="What are the conditions in Article 6?",
    )
    assert select.call_args.args[-1] == "What are the conditions in Article 6?"
    assert len(expanded.hits) == 25
    assert not trace.get("skipped_budget")


@pytest.mark.asyncio
async def test_sentence_continuations_do_not_disable_existing_clause_dependencies(monkeypatch):
    rows = [
        chunk(i, text, 1)
        for i, text in enumerate(["A fragment", "continued.", "a) First.", "b) Second."])
    ]
    for row in rows:
        row.point_id, row.text_sha256 = row.id, row.id
    result = SearchResponse(
        index_run_id="index",
        generation=1,
        status="results",
        hits=sources(rows[:1]),
        eligible_documents=1,
    )
    run = SimpleNamespace(
        id="index", status="completed", is_active=True, workspace_id="ws", collection_id="col"
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
    monkeypatch.setattr(
        context,
        "continuation_groups",
        lambda *args: [
            {"kind": "continuation", "primary_chunk_id": "0", "required_ids": ["0", "1"]}
        ],
    )
    monkeypatch.setattr(context, "clause_groups", lambda *args: [rows])

    async def hits(db, run, allowed, candidates, sealed):
        return sources([rows[int(hit.payload["chunk_id"])] for hit in candidates])

    monkeypatch.setattr(context, "_hits", hits)
    expanded, trace = await context.expand_context(
        db,
        None,
        None,
        "ws",
        "col",
        result,
        AnswerRequest(question="Explain", context_max_bytes=100000),
    )
    assert {hit.chunk_id for hit in expanded.hits} == {row.id for row in rows}
    assert [item["kind"] for item in trace["added"]] == ["structure", "clause", "clause"]


def test_named_article_records_continuation_fragments_as_required_units():
    rows, bundles = corpus()
    texts = [
        "Article 4. Eligibility conditions",
        "1. A minimum of",
        "17 points applies.",
        "Except in the following cases:",
        "a) Certified candidates.",
        "Article 5. Other",
    ]
    rows = [chunk(i, text, 1) for i, text in enumerate(texts)]
    bundles["version"].documents[0]["pages"] = [
        {
            "page_number": 1,
            "blocks": [{"evidence_id": str(i), "text": text} for i, text in enumerate(texts)],
        }
    ]
    group = select_groups(rows, sources(rows[:1]), bundles, "Article 4 conditions")[0]
    assert {u["ref"] for u in group["units"]} >= {"run:1", "run:2", "run:3", "run:4"}


@pytest.mark.parametrize("boundary", ["sentence", "heading", "table", "figure"])
def test_continuation_does_not_cross_a_real_source_boundary(boundary):
    rows, bundles = corpus()
    texts = ["1. A minimum result of", "17 points is required", "for certified candidates."]
    rows = [chunk(i, text, 1) for i, text in enumerate(texts)]
    blocks = [{"evidence_id": str(i), "text": text} for i, text in enumerate(texts)]
    if boundary == "sentence":
        blocks[0]["text"] += "."
    elif boundary == "heading":
        blocks[1]["label"] = "section_header"
    else:
        blocks[1]["type"] = boundary
    bundles["version"].documents[0]["pages"] = [{"page_number": 1, "blocks": blocks}]
    assert not continuation_groups(rows, sources(rows[:1]), bundles)


def test_continuation_keeps_uppercase_names_and_an_unindexed_piece_across_pages():
    rows, bundles = corpus()
    texts = ["1. Complete a course in", "Applied Physics", "with at least 17 points."]
    rows = [chunk(i, text, 1) for i, text in enumerate(texts)]
    bundles["version"].documents[0]["pages"] = [
        {"page_number": 1, "blocks": [{"evidence_id": "0", "text": texts[0]}]},
        {"page_number": 2, "blocks": [{"evidence_id": str(i), "text": texts[i]} for i in (1, 2)]},
    ]
    group = continuation_groups(rows[:2], sources(rows[:1]), bundles)[0]
    assert group["required_ids"] == ["0", "1"]
    assert group["unindexed_refs"] == ["run:2"]
    assert [u["ref"] for u in group["units"]] == ["run:0", "run:1", "run:2"]
