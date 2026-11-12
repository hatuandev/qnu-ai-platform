"""Unselectable tables allow verbatim prose; selectable tables keep cell selection."""

import json

import pytest

from qnu.domains.rag.answer.cells import catalog, materialize
from qnu.domains.rag.answer.drafting import output_schema, parse_answer
from qnu.domains.rag.answer.schemas import EvidenceSource
from qnu.platform.errors import AppException
from tests.unit.test_table_grounding_770 import source


def unselectable(text, *, key="E1", table="ocr:t"):
    """Keep the visible text and the canonical cells describing the same table."""
    rows = [
        [part.strip() for part in line.split("]:", 1)[1].split("|")]
        for line in text.splitlines()
        if line.startswith("row[") and "]:" in line
    ]
    s = source(rows or [["Name", "Price"], ["Alpha", "18"]], key=key, table=table)
    for row in s.structure["rows"]:
        for cell in row:
            cell["header"] = False
    s.text = text
    return s


def paragraph(key, text):
    return EvidenceSource(
        evidence_id=key,
        chunk_id=key,
        document_id="doc",
        version_id="v",
        publication_decision_id="published",
        kind="paragraph",
        score=1,
        text=text,
        citations={"run:a": {"page": 1}},
        structure=None,
        source_passages=[{"citation": "run:a", "text": text, "position": "0"}],
    )


def answer_with(statements, lookups=()):
    return json.dumps(
        {
            "status": "answered",
            "statements": statements,
            "lookups": [{"cell_id": key} for key in lookups],
        }
    )


def test_unselectable_table_accepts_verbatim_numeric_prose():
    s = unselectable("row[0]: Name | Price\nrow[1]: Alpha | 18")
    draft = parse_answer(answer_with([{"text": "Alpha: 18", "evidence_ids": ["E1"]}]), [s])
    result = materialize(draft, [s], catalog([s]))
    assert result.statements[0].text == "Alpha: 18"
    assert result.statements[0].evidence_ids == ["E1"]


def test_unselectable_table_rejects_fabricated_number():
    s = unselectable("row[0]: Name | Price\nrow[1]: Alpha | 18")
    draft = parse_answer(answer_with([{"text": "Alpha: 999", "evidence_ids": ["E1"]}]), [s])
    with pytest.raises(AppException) as exc:
        materialize(draft, [s], catalog([s]))
    assert exc.value.code == "answer_table_value_not_extractive"
    assert exc.value.validation_issues == [
        {"path": ["statements", 0, "text"], "type": "number_not_in_cited_source"}
    ]


@pytest.mark.parametrize("prose", ["Alpha đạt 93.3", "Alpha đạt 93"])
def test_unselectable_table_rejects_normalized_or_partial_numbers(prose):
    s = unselectable("row[0]: Name | Rate\nrow[1]: Alpha | 93,3")
    draft = parse_answer(answer_with([{"text": prose, "evidence_ids": ["E1"]}]), [s])
    with pytest.raises(AppException) as exc:
        materialize(draft, [s], catalog([s]))
    assert exc.value.code == "answer_table_value_not_extractive"


def test_unselectable_table_keeps_decimal_comma_and_date_tokens_verbatim():
    s = unselectable("row[0]: Mã | Hạn\nrow[1]: NV-01 | 30/11/2026")
    draft = parse_answer(
        answer_with([{"text": "NV-01 hạn 30/11/2026", "evidence_ids": ["E1"]}]), [s]
    )
    result = materialize(draft, [s], catalog([s]))
    assert result.statements[0].text == "NV-01 hạn 30/11/2026"
    rate = unselectable("row[0]: Name | Rate\nrow[1]: Alpha | 93,3", key="E2", table="ocr:r")
    draft = parse_answer(answer_with([{"text": "Alpha đạt 93,3", "evidence_ids": ["E2"]}]), [rate])
    assert materialize(draft, [rate], catalog([rate])).statements[0].text == "Alpha đạt 93,3"


def test_unselectable_table_accepts_text_only_prose():
    s = unselectable("row[0]: Item | Note\nrow[1]: Beta | nhiệm vụ chính")
    draft = parse_answer(
        answer_with([{"text": "Beta là nhiệm vụ chính.", "evidence_ids": ["E1"]}]), [s]
    )
    assert materialize(draft, [s], catalog([s])).statements[0].text == "Beta là nhiệm vụ chính."


def test_selectable_table_numeric_prose_without_lookup_still_fails():
    s = source([["Name", "Price"], ["Alpha", "18"]])
    draft = parse_answer(answer_with([{"text": "Alpha costs 18.", "evidence_ids": ["E1"]}]), [s])
    with pytest.raises(AppException) as exc:
        materialize(draft, [s], catalog([s]))
    assert exc.value.code == "answer_cell_selection_required"


def test_lookup_into_unselectable_table_is_still_rejected():
    s = unselectable("row[0]: Name | Price\nrow[1]: Alpha | 18")
    draft = parse_answer(answer_with([], ["E1:r1:k1"]), [s])
    with pytest.raises(AppException) as exc:
        materialize(draft, [s], catalog([s]))
    assert exc.value.code == "answer_cell_invalid"


def test_mixed_answer_keeps_unselectable_prose_and_drops_selectable_prose():
    selectable = source([["Name", "Price"], ["Alpha", "18"]])
    prose_table = unselectable("row[0]: Item | Rate\nrow[1]: Beta | 22", key="E2", table="ocr:t2")
    sources = [selectable, prose_table]
    draft = parse_answer(
        answer_with(
            [
                {"text": "Alpha costs 18.", "evidence_ids": ["E1"]},
                {"text": "Beta: 22", "evidence_ids": ["E2"]},
            ],
            ["E1:r1:k1"],
        ),
        sources,
    )
    result = materialize(draft, sources, catalog(sources))
    assert [s.text for s in result.statements] == ["Beta: 22", "Alpha — Price: 18"]
    assert result.statements[0].evidence_ids == ["E2"]


def test_number_from_cocited_narrative_is_source_bound():
    table = unselectable("row[0]: Item | Rate\nrow[1]: Beta | 22")
    note = paragraph("E2", "The rate is 18.")
    sources = [table, note]
    draft = parse_answer(answer_with([{"text": "Rate: 18", "evidence_ids": ["E1", "E2"]}]), sources)
    result = materialize(draft, sources, catalog(sources))
    assert result.statements[0].text == "Rate: 18"
    fabricated = parse_answer(
        answer_with([{"text": "Rate: 77", "evidence_ids": ["E1", "E2"]}]), sources
    )
    with pytest.raises(AppException) as exc:
        materialize(fabricated, sources, catalog(sources))
    assert exc.value.code == "answer_table_value_not_extractive"


def test_schema_enum_includes_unselectable_tables_only_when_catalog_known():
    selectable = source([["Name", "Price"], ["Alpha", "18"]])
    prose_table = unselectable("row[0]: Item | Rate\nrow[1]: Beta | 22", key="E2", table="ocr:t2")
    note = paragraph("E3", "A condition.")
    sources = [selectable, prose_table, note]
    cells = catalog(sources)
    schema = output_schema(sources, cells=cells)
    assert schema["$defs"]["Statement"]["properties"]["evidence_ids"]["items"]["enum"] == [
        "E2",
        "E3",
    ]
    legacy = output_schema(sources)
    assert legacy["$defs"]["Statement"]["properties"]["evidence_ids"]["items"]["enum"] == ["E3"]
    tables_only = output_schema([selectable], cells=catalog([selectable]))
    assert tables_only["properties"]["statements"]["maxItems"] == 0
    unselectable_only = output_schema([prose_table], cells=catalog([prose_table]))
    assert unselectable_only["$defs"]["Statement"]["properties"]["evidence_ids"]["items"][
        "enum"
    ] == ["E2"]
