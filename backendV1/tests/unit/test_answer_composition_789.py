"""Generic split-condition and mixed-source regressions, without admissions labels."""

import copy
import json

import pytest

from qnu.domains.rag.answer.cells import catalog, materialize
from qnu.domains.rag.answer.drafting import messages_for, parse_answer
from qnu.domains.rag.answer.source_text import passages
from qnu.platform.errors import AppException
from tests.unit.test_table_grounding_770 import source


def paragraph(key, refs, docs):
    s = source([["Item", "Rate"], ["Valve", "8"]], key=key)
    s.kind, s.structure, s.text = "paragraph", None, "Derived summary."
    s.citations = {ref: {"page": 1} for ref in refs}
    s.source_passages = passages(s, docs)
    return s


def documents():
    return [
        {
            "ocr_run_id": "run",
            "pages": [
                {
                    "blocks": [
                        {"evidence_id": "a", "text": "Eligible teams must satisfy category A and "},
                        {
                            "evidence_id": "b",
                            "text": "a score of at least 27 or a certificate score of 9.",
                        },
                        {"evidence_id": "c", "text": "A separate case has another rule."},
                    ]
                }
            ],
        }
    ]


def test_narrative_order_uses_pinned_block_order_not_retrieval_rank():
    docs = documents()
    end = paragraph("E1", ["run:b"], docs)
    start = paragraph("E2", ["run:a"], docs)
    original = copy.deepcopy([end, start])
    view = json.loads(messages_for("What conditions apply?", [end, start])[-1].content)
    assert view["reading"] == [["E2", "E1"]]
    assert sum(item["text"].count("category A") for item in view["evidence"]) == 1
    assert [end, start] == original


@pytest.mark.parametrize("boundary", ["gap", "table", "version", "document", "publication"])
def test_narrative_never_bridges_uncited_blocks_or_published_identities(boundary):
    docs = documents()
    if boundary == "table":
        docs[0]["pages"][0]["blocks"][1]["table"] = {"rows": []}
    a = paragraph("E1", ["run:a"], docs)
    c = paragraph("E2", ["run:c" if boundary in {"gap", "table"} else "run:b"], docs)
    field = {
        "version": "version_id",
        "document": "document_id",
        "publication": "publication_decision_id",
    }.get(boundary)
    if field:
        setattr(c, field, "different")
    view = json.loads(messages_for("Rules?", [a, c])[-1].content)
    # A one-item run proves no adjacency; only multi-item verified runs are sent.
    assert not view.get("reading")


def test_partial_overlap_preserves_complete_sentence_in_each_owner():
    docs = documents()
    a = paragraph("E1", ["run:a", "run:b"], docs)
    b = paragraph("E2", ["run:b"], docs)
    view = json.loads(messages_for("Rules?", [b, a])[-1].content)
    assert view["reading"] == [["E1", "E2"]]
    assert view["evidence"][1]["text"] == "\n".join(p["text"] for p in a.source_passages)
    assert "category A" in view["evidence"][1]["text"]
    assert "certificate score" in view["evidence"][1]["text"]


def test_mixed_answer_retains_only_paragraph_narrative_and_original_table_values():
    table = source([["Level", "Value"], ["Basic", "12"]])
    note = paragraph("E2", ["run:a"], documents())
    value = {
        "status": "answered",
        "lookups": [{"cell_id": "E1:r1:k1"}],
        "statements": [
            {"text": "Only certified teams may use this level.", "evidence_ids": ["E2"]},
            {"text": "Basic costs 999, add an extra fee.", "evidence_ids": ["E1"]},
        ],
    }
    answer = materialize(
        parse_answer(json.dumps(value), [table, note]), [table, note], catalog([table])
    )
    assert len(answer.statements) == 2
    assert answer.statements[0].evidence_ids == ["E2"]
    assert answer.statements[1].text == "Basic — Value: 12"
    assert "999" not in str(answer) and "extra fee" not in str(answer)


def test_mixed_response_still_rejects_foreign_cell_and_citation():
    table = source([["Level", "Value"], ["Basic", "12"]])
    value = {"status": "answered", "lookups": [{"cell_id": "E9:r1:k1"}], "statements": []}
    with pytest.raises(AppException):
        materialize(parse_answer(json.dumps(value), [table]), [table], catalog([table]))
    value["lookups"] = [{"cell_id": "E1:r1:k1"}]
    value["statements"] = [{"text": "Unknown.", "evidence_ids": ["E999"]}]
    with pytest.raises(AppException):
        parse_answer(json.dumps(value), [table])


def test_generation_schema_excludes_table_citations_from_narrative():
    from qnu.domains.rag.answer.drafting import output_schema

    table = source([["Item", "Rate"], ["Valve", "8"]])
    note = paragraph("E2", ["run:a"], documents())
    schema = output_schema([table, note])
    assert schema["$defs"]["Statement"]["properties"]["evidence_ids"]["items"]["enum"] == ["E2"]
    assert output_schema([table])["properties"]["statements"]["maxItems"] == 0


@pytest.mark.parametrize("broken", [None, "gap", "terminal", "uppercase", "version"])
def test_leading_continuation_completes_only_verified_narrative_citations(broken):
    docs = documents()
    if broken == "terminal":
        docs[0]["pages"][0]["blocks"][0]["text"] += "."
    if broken == "uppercase":
        docs[0]["pages"][0]["blocks"][1]["text"] = "A new independent sentence."
    end = paragraph("E1", ["run:b"], docs)
    start = paragraph("E2", ["run:a"], docs)
    if broken == "gap":
        end.source_passages[0]["position"] = "3"
    if broken == "version":
        start.version_id = "different"
    draft = parse_answer(
        json.dumps(
            {
                "status": "answered",
                "lookups": [],
                "statements": [{"text": "A condition with a score.", "evidence_ids": ["E1"]}],
            }
        ),
        [end, start],
    )
    result = materialize(draft, [end, start], catalog([end, start]))
    assert result.statements[0].evidence_ids == (["E1", "E2"] if broken is None else ["E1"])


@pytest.mark.asyncio
async def test_added_reading_context_is_included_in_budget_before_dispatch(monkeypatch):
    from unittest.mock import AsyncMock

    from qnu.domains.knowledge.index.schemas import SearchHit, SearchResponse
    from qnu.domains.rag.answer import service
    from qnu.domains.rag.answer.schemas import AnswerRequest

    docs = documents()
    docs[0]["pages"][0]["blocks"][0]["text"] += " " + "extra condition " * 30
    sources = [paragraph("E1", ["run:a"], docs), paragraph("E2", ["run:b"], docs)]
    result = SearchResponse(
        index_run_id="idx",
        generation=1,
        status="results",
        eligible_documents=1,
        hits=[SearchHit.model_validate(s.model_dump(exclude={"evidence_id"})) for s in sources],
    )
    envelope = json.loads(messages_for("Conditions?", sources)[-1].content)
    old_size = len(
        json.dumps(
            {
                key: envelope[key]
                for key in ("evidence", "tables", "unselectable", "reading", "plan")
                if key in envelope
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
    )
    monkeypatch.setattr(service, "search", AsyncMock(return_value=result))
    monkeypatch.setattr(service, "expand_context", AsyncMock(return_value=(result, {})))
    monkeypatch.setattr(service, "sources_for", lambda _: sources)
    monkeypatch.setattr(service, "attach_source_text", AsyncMock())
    prepare = AsyncMock()
    monkeypatch.setattr(service, "prepare_chat_request", prepare)
    with pytest.raises(AppException) as exc:
        await service.answer(
            None,
            None,
            None,
            None,
            None,
            None,
            "ws",
            "col",
            AnswerRequest(question="Conditions?", context_max_bytes=old_size - 1),
        )
    assert exc.value.code == "answer_context_budget_exceeded"
    assert service.search.await_args.kwargs["verify"] is False
    prepare.assert_not_called()


def test_same_alias_requires_identical_complete_ordered_passages():
    docs = documents()
    first = paragraph("E1", ["run:a", "run:b"], docs)
    duplicate = paragraph("E2", ["run:a", "run:b"], docs)
    view = json.loads(messages_for("Rules?", [first, duplicate])[-1].content)
    assert view["evidence"][1] == {"id": "E2", "kind": "paragraph", "same": "E1"}
    different = duplicate.model_copy(update={"publication_decision_id": "other"})
    view = json.loads(messages_for("Rules?", [first, different])[-1].content)
    assert all("text" in item for item in view["evidence"])
