"""Explicit column-header years scope cells, chunks, retrieval and citations."""

import json

import pytest

from qnu.domains.knowledge.index.chunking import build_chunks
from qnu.domains.knowledge.index.contextual import _prefix
from qnu.domains.knowledge.index.query_scope import resolve
from qnu.domains.knowledge.metadata import MetadataFilter, matches_metadata, validate_annotations
from qnu.domains.knowledge.publication.automatic_metadata import preview
from qnu.domains.knowledge.publication.evidence import VersionBundle
from qnu.domains.rag.answer.cells import catalog, materialize, prompt_catalog
from qnu.domains.rag.answer.schemas import EvidenceSource, ModelAnswer
from qnu.domains.rag.answer.table_selection import select_catalog
from qnu.platform.errors import AppException

RUN = "ocr"
TABLE = "ev-table"


def table(*, headers, body, columns, marked=True):
    rows = []
    for index, row in enumerate([*headers, *body]):
        cells = []
        for column, spec in enumerate(row):
            spec = spec if isinstance(spec, dict) else {"text": spec}
            cells.append(
                {
                    "text": spec["text"],
                    "row_span": spec.get("row_span", 1),
                    "col_span": spec.get("col_span", 1),
                    "header": marked and index < len(headers),
                    "evidence_id": f"{TABLE}-c{index}-{column}",
                }
            )
        rows.append(cells)
    return {"status": "parsed", "row_count": len(rows), "column_count": columns, "rows": rows}


def fixture(*, headers, body, columns, intro=None, marked=True):
    value = table(headers=headers, body=body, columns=columns, marked=marked)
    blocks = [{"evidence_id": TABLE, "text": "Bảng chỉ tiêu", "label": "Table", "table": value}]
    paragraphs = []
    if intro:
        blocks.insert(0, {"evidence_id": "ev-intro", "text": intro, "type": "paragraph"})
        paragraphs.append({"text": intro, "citations": [f"{RUN}:ev-intro"]})
    citations = {f"{RUN}:{TABLE}": {"page": 1}, f"{RUN}:ev-intro": {"page": 1}}
    citations.update(
        {f"{RUN}:{cell['evidence_id']}": {"page": 1} for row in value["rows"] for cell in row}
    )
    content = {
        "title": "Kế hoạch đào tạo",
        "citations": citations,
        "sections": [{"heading": "Chỉ tiêu", "paragraphs": paragraphs}],
        "source_tables": [{"citation": f"{RUN}:{TABLE}", "page_number": 1, "table": value}],
    }
    documents = [{"ocr_run_id": RUN, "pages": [{"page_number": 1, "blocks": blocks}]}]
    return content, documents


def published(content, documents):
    return VersionBundle("a" * 64, "b" * 64, "c" * 64, "d" * 64, {}, content, b"", documents)


def annotations(content, documents):
    return {item["target"]: item for item in preview(published(content, documents))["annotations"]}


def table_chunk(content, documents, listed):
    chunks = build_chunks(content, documents, 8000, listed)
    tables = [chunk for chunk in chunks if chunk.kind == "table"]
    assert len(tables) == 1
    return chunks, tables[0]


def evidence_source(chunk):
    return EvidenceSource(
        evidence_id="ich_table",
        chunk_id="ich_table",
        document_id="doc",
        version_id="v",
        publication_decision_id="published",
        kind="table",
        score=1,
        text=chunk.text,
        citations=chunk.citations,
        structure=chunk.structure,
    )


def test_conversion_year_requires_a_titled_source_and_local_rule():
    content, documents = fixture(
        headers=[["Điểm chứng chỉ", "Điểm quy đổi"]],
        body=[["6.0", "9.0"]],
        columns=2,
        intro="Điểm được quy đổi theo mức điểm như sau:",
    )
    blocks = documents[0]["pages"][0]["blocks"]
    title = {"evidence_id": "ev-title", "text": "THÔNG TIN TUYỂN SINH ĐẠI HỌC NĂM 2026"}
    blocks.insert(0, title)
    content["citations"][f"{RUN}:ev-title"] = {"page": 1}
    listed = list(annotations(content, documents).values())
    values = [a for a in listed if a["target"].startswith("table:")]
    assert len(values) == 2
    assert all(a["values"] == {"data_year": 2026} and len(a["evidence"]) == 2 for a in values)
    _, chunk = table_chunk(content, documents, listed)
    assert matches_metadata(chunk.structure, MetadataFilter(data_year=2026))
    assert not matches_metadata(chunk.structure, MetadataFilter(data_year=2025))
    source = evidence_source(chunk).model_copy(update={"evidence_id": "E1"})
    cells = select_catalog(
        catalog([source]),
        [source],
        "So sánh điểm quy đổi năm 2025 và 2026",
        [],
        data_years={2025, 2026},
    )
    assert prompt_catalog(cells)["tables"][0]["data_year"] == 2026
    lookup = cells["tables"][0]["cells"][0]["cell_id"]
    answer = ModelAnswer(status="answered", statements=[], lookups=[{"cell_id": lookup}])
    result = materialize(answer, [source], cells)
    assert "Năm 2026 / Điểm quy đổi: 9.0" in result.statements[0].text
    validate_annotations(values, content, documents, strict_roles=True)
    with pytest.raises(AppException):
        validate_annotations(
            [{**values[0], "evidence": values[0]["evidence"][:1]}], content, documents
        )
    blocks[1]["text"] = "Điểm năm trước được quy đổi theo mức điểm như sau:"
    assert not any(target.startswith("table:") for target in annotations(content, documents))


def test_single_year_header_scopes_the_column_not_the_whole_table():
    content, documents = fixture(
        headers=[["Ngành đào tạo", "Mã ngành", "Chỉ tiêu năm 2027"]],
        body=[["Công nghệ thông tin", "7480101", "95"], ["Kỹ thuật phần mềm", "7480104", "120"]],
        columns=3,
        intro="Kế hoạch tuyển sinh năm 2027.",
    )
    found = annotations(content, documents)
    column = found[f"table:{RUN}:{TABLE}:column:2"]
    assert column["values"] == {"data_year": 2027}
    assert column["evidence"] == [{"citation": f"{RUN}:{TABLE}-c0-2", "quote": "Chỉ tiêu năm 2027"}]
    assert set(found) == {f"table:{RUN}:{TABLE}:column:2", "paragraph:0:0"}
    listed = preview(published(content, documents))["annotations"]
    chunks, chunk = table_chunk(content, documents, listed)
    assert [item["target"] for item in chunk.structure["retrieval_metadata"]] == [
        f"table:{RUN}:{TABLE}:column:2"
    ]
    assert matches_metadata(chunk.structure, MetadataFilter(data_year=2027))
    assert not matches_metadata(chunk.structure, MetadataFilter(data_year=2026))
    assert f"{RUN}:{TABLE}-c0-2" in chunk.citations
    assert f"{RUN}:{TABLE}-c1-2" in chunk.citations and f"{RUN}:{TABLE}-c2-2" in chunk.citations
    assert all(
        item["target"].startswith("table:") for item in chunk.structure["retrieval_metadata"]
    )
    units = {
        unit["target"]: unit["values"] for unit in json.loads(_prefix(chunk, content, []))["units"]
    }
    assert units == {f"table:{RUN}:{TABLE}:column:2": {"data_year": 2027}}
    assert [item for item in chunks if item.kind == "paragraph"]


def test_intro_year_alone_never_scopes_table_cells():
    content, documents = fixture(
        headers=[["Ngành đào tạo", "Chỉ tiêu"]],
        body=[["Công nghệ thông tin", "95"]],
        columns=2,
        intro="Kế hoạch tuyển sinh năm 2027.",
    )
    found = annotations(content, documents)
    assert set(found) == {"paragraph:0:0"}
    listed = preview(published(content, documents))["annotations"]
    _, chunk = table_chunk(content, documents, listed)
    assert chunk.structure["retrieval_metadata"] == []
    assert not matches_metadata(chunk.structure, MetadataFilter(data_year=2027))


def test_two_year_columns_keep_each_year_and_answer_selection_drops_the_other():
    content, documents = fixture(
        headers=[
            ["Ngành đào tạo", "Mã ngành", "Chỉ tiêu năm 2026", "Chỉ tiêu năm 2027", "Ghi chú"]
        ],
        body=[
            ["Công nghệ thông tin", "7480101", "100", "95", "Ưu tiên"],
            ["Kỹ thuật phần mềm", "7480104", "90", "120", "Tuyển bổ sung"],
        ],
        columns=5,
    )
    found = annotations(content, documents)
    assert found[f"table:{RUN}:{TABLE}:column:2"]["values"] == {"data_year": 2026}
    assert found[f"table:{RUN}:{TABLE}:column:3"]["values"] == {"data_year": 2027}
    assert f"table:{RUN}:{TABLE}:column:4" not in found
    listed = preview(published(content, documents))["annotations"]
    _, chunk = table_chunk(content, documents, listed)
    assert {item["target"] for item in chunk.structure["retrieval_metadata"]} == {
        f"table:{RUN}:{TABLE}:column:2",
        f"table:{RUN}:{TABLE}:column:3",
    }
    query = "Số liệu năm 2027 của ngành Công nghệ thông tin"
    _, filters, _ = resolve(query, MetadataFilter(), [chunk.structure])
    assert [item.model_dump(mode="json", exclude_none=True) for item in filters] == [
        {"data_year": 2027}
    ]
    assert matches_metadata(chunk.structure, filters[0])
    _, absent, _ = resolve(
        "Chỉ tiêu ngành Công nghệ thông tin năm 2030 là bao nhiêu?",
        MetadataFilter(),
        [chunk.structure],
    )
    assert [item.model_dump(mode="json", exclude_none=True) for item in absent] == [
        {"data_year": 2030}
    ]
    assert not matches_metadata(chunk.structure, absent[0])
    source = evidence_source(chunk)
    cells = catalog([source])
    narrowed = select_catalog(cells, [source], query, [], data_years={2027})
    values = {
        (cell["subject"], cell["column"], cell["value"])
        for table in narrowed["tables"]
        for cell in table["cells"]
    }
    assert ("Công nghệ thông tin", 3, "95") in values
    assert ("Kỹ thuật phần mềm", 3, "120") in values
    assert ("Công nghệ thông tin", 2, "100") not in values
    assert ("Kỹ thuật phần mềm", 2, "90") not in values
    assert ("Công nghệ thông tin", 4, "Ưu tiên") in values
    chosen = next(
        cell for table in narrowed["tables"] for cell in table["cells"] if cell["value"] == "95"
    )
    assert f"{RUN}:{TABLE}-c0-3" in chosen["source_cells"]
    assert f"{RUN}:{TABLE}-c1-3" in chosen["source_cells"]
    other = select_catalog(cells, [source], query, [], data_years={2026})
    other_values = {cell["value"] for table in other["tables"] for cell in table["cells"]}
    assert {"100", "90"} <= other_values and "95" not in other_values


def test_merged_multitier_header_year_covers_every_spanned_data_column():
    content, documents = fixture(
        headers=[
            [
                {"text": "Ngành đào tạo", "row_span": 2},
                {"text": "Chỉ tiêu năm 2027", "col_span": 2},
            ],
            ["Đại học", "Liên thông"],
        ],
        body=[["Công nghệ thông tin", "80", "15"], ["Kỹ thuật phần mềm", "100", "20"]],
        columns=3,
    )
    found = annotations(content, documents)
    for column in (1, 2):
        annotation = found[f"table:{RUN}:{TABLE}:column:{column}"]
        assert annotation["values"] == {"data_year": 2027}
        assert annotation["evidence"] == [
            {"citation": f"{RUN}:{TABLE}-c0-1", "quote": "Chỉ tiêu năm 2027"}
        ]
    listed = preview(published(content, documents))["annotations"]
    _, chunk = table_chunk(content, documents, listed)
    targets = {item["target"] for item in chunk.structure["retrieval_metadata"]}
    assert targets == {
        f"table:{RUN}:{TABLE}:column:1",
        f"table:{RUN}:{TABLE}:column:2",
    }
    assert matches_metadata(chunk.structure, MetadataFilter(data_year=2027))
    assert not matches_metadata(chunk.structure, MetadataFilter(data_year=2028))


def test_ambiguous_or_role_year_headers_stay_unknown():
    content, documents = fixture(
        headers=[
            [
                "Ngành đào tạo",
                "Ngày ban hành 01/02/2027",
                "Chỉ tiêu năm 2026 và 2027",
                "Ghi chú",
            ]
        ],
        body=[["Công nghệ thông tin", "159", "95", "Chỉ áp dụng đợt 1"]],
        columns=4,
    )
    assert not [
        a for a in annotations(content, documents).values() if a["target"].startswith("table:")
    ]


def test_unmarked_first_row_is_not_treated_as_a_header():
    content, documents = fixture(
        headers=[["Ngành đào tạo", "Chỉ tiêu năm 2027"]],
        body=[["Công nghệ thông tin", "95"]],
        columns=2,
        marked=False,
    )
    assert preview(published(content, documents))["annotations"] == []


@pytest.mark.parametrize("marked", [False, True])
def test_multitier_year_header_scopes_its_child_columns(marked):
    content, documents = fixture(
        headers=[
            [
                {"text": "Ngành đào tạo", "row_span": 2},
                {"text": "2024", "col_span": 2},
            ],
            ["Chỉ tiêu", "Trúng tuyển"],
        ],
        body=[["Công nghệ thông tin", "80", "15"], ["Kỹ thuật phần mềm", "100", "20"]],
        columns=3,
        marked=marked,
    )
    found = annotations(content, documents)
    for column in (1, 2):
        annotation = found[f"table:{RUN}:{TABLE}:column:{column}"]
        assert annotation["values"] == {"data_year": 2024}
        assert annotation["evidence"] == [{"citation": f"{RUN}:{TABLE}-c0-1", "quote": "2024"}]
    listed = preview(published(content, documents))["annotations"]
    _, chunk = table_chunk(content, documents, listed)
    assert {item["target"] for item in chunk.structure["retrieval_metadata"]} == {
        f"table:{RUN}:{TABLE}:column:1",
        f"table:{RUN}:{TABLE}:column:2",
    }
    assert matches_metadata(chunk.structure, MetadataFilter(data_year=2024))
    assert not matches_metadata(chunk.structure, MetadataFilter(data_year=2025))


def test_multitier_parent_year_conflicting_with_a_child_label_stays_unknown():
    content, documents = fixture(
        headers=[
            [
                {"text": "Ngành đào tạo", "row_span": 2},
                {"text": "2024", "col_span": 2},
            ],
            ["Chỉ tiêu năm 2023", "Trúng tuyển"],
        ],
        body=[["Công nghệ thông tin", "80", "15"], ["Kỹ thuật phần mềm", "100", "20"]],
        columns=3,
        marked=False,
    )
    found = annotations(content, documents)
    assert f"table:{RUN}:{TABLE}:column:1" not in found
    assert found[f"table:{RUN}:{TABLE}:column:2"]["values"] == {"data_year": 2024}


def test_headerless_table_and_signing_date_never_scope_a_column():
    content, documents = fixture(
        headers=[["Ngành đào tạo", "2024"]],
        body=[["Công nghệ thông tin", "80"], ["Kỹ thuật phần mềm", "90"]],
        columns=2,
        intro="Ngày ký: 15/01/2024",
        marked=False,
    )
    assert not [
        item
        for item in annotations(content, documents).values()
        if item["target"].startswith("table:")
    ]


def test_column_annotation_rejects_evidence_from_another_column():
    content, documents = fixture(
        headers=[["Ngành đào tạo", "Chỉ tiêu năm 2027"]],
        body=[["Công nghệ thông tin", "95"]],
        columns=2,
    )
    forged = {
        "target": f"table:{RUN}:{TABLE}:column:1",
        "values": {"data_year": 2027},
        "evidence": [{"citation": f"{RUN}:{TABLE}-c1-0", "quote": "Công nghệ thông tin"}],
    }
    with pytest.raises(AppException) as exc:
        validate_annotations([forged], content, documents)
    assert exc.value.code == "retrieval_metadata_invalid"
