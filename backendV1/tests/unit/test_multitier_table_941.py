"""Multi-tier merged headers become selectable at answer time, with no re-index.

A native block whose top-left identity label spans several rows and columns, with
merged numeric group headers above purely numeric data columns, is proven by
geometry and type contrast alone. The detector emits the header tiers; the catalog
borrows them for every data chunk; support attaches the header fragment. The
extractive guard in materialize is unchanged.
"""

import json
from types import SimpleNamespace

import pytest

from qnu.domains.knowledge.index.table_dependencies import (
    MULTITIER_BASIS,
    dependencies,
    multitier_header,
)
from qnu.domains.knowledge.metadata import MetadataFilter
from qnu.domains.rag.answer.cells import catalog, materialize
from qnu.domains.rag.answer.drafting import parse_answer
from qnu.domains.rag.answer.schemas import EvidenceSource
from qnu.domains.rag.answer.table_support import supports


def cell(text, ref, *, rs=1, cs=1):
    return {"text": text, "row_span": rs, "col_span": cs, "header": False, "evidence_id": ref}


def grid():
    """Two header tiers over a merged identity label; columns 3-5 are purely numeric.

    Column 0 is a row-spanned group, column 1 a numeric program code sharing the
    identity header, column 2 the program name. This is the shape that defeated
    every single-tier proof and left the values unselectable.
    """
    return [
        [cell("Chương trình", "t-0-0", rs=2, cs=3), cell("2026", "t-0-1", cs=3)],
        [cell("Chỉ tiêu", "t-1-0"), cell("Ghi nhận", "t-1-1"), cell("Tỷ lệ", "t-1-2")],
        [
            cell("Group A", "t-2-0", rs=3),
            cell("0012", "t-2-1"),
            cell("Alpha", "t-2-2"),
            cell("100", "t-2-3"),
            cell("200", "t-2-4"),
            cell("300", "t-2-5"),
        ],
        [
            cell("00027", "t-3-0"),
            cell("Beta", "t-3-1"),
            cell("110", "t-3-2"),
            cell("210", "t-3-3"),
            cell("310", "t-3-4"),
        ],
        [
            cell("0120", "t-4-0"),
            cell("Gamma", "t-4-1"),
            cell("120", "t-4-2"),
            cell("220", "t-4-3"),
            cell("320", "t-4-4"),
        ],
    ]


def table(rows=None, *, columns=6):
    return {"rows": grid() if rows is None else rows, "column_count": columns}


def chunk(rows, indices, *, key, total=5, columns=6, citation="run:t"):
    refs = {
        citation.split(":", 1)[0] + ":" + c["evidence_id"]: {"page": 1} for row in rows for c in row
    }
    return EvidenceSource(
        evidence_id=key,
        chunk_id=key,
        document_id="doc",
        version_id="v",
        publication_decision_id="published",
        kind="table",
        score=1,
        text="raw table",
        citations={citation: {"page": 1}, **refs},
        structure={
            "source_table_citation": citation,
            "original_row_count": total,
            "original_column_count": columns,
            "rows": rows,
            "row_indices": indices,
        },
    )


def document(rows=None, *, method="native", review=False, columns=6):
    bbox = {"units": "normalized_0_1", "x0": 0.1, "x1": 0.9, "y0": 0.1, "y1": 0.9}
    return {
        "ocr_run_id": "run",
        "pages": [
            {
                "page_number": 1,
                "extraction_method": method,
                "blocks": [
                    {
                        "evidence_id": "t",
                        "requires_review": review,
                        "bbox": bbox,
                        "table": {
                            "status": "parsed",
                            "column_count": columns,
                            "rows": grid() if rows is None else rows,
                        },
                    }
                ],
            }
        ],
    }


def link_for(data_key="E2", header_key="E1", *, basis=MULTITIER_BASIS, header_rows=(0, 1)):
    return {
        "chunk_id": data_key,
        "header": "run:t",
        "previous": None,
        "support_ids": [header_key],
        "basis": basis,
        "header_rows": list(header_rows),
    }


def test_multitier_header_proof_returns_header_tiers():
    assert multitier_header(table()) == [0, 1]


def test_hybrid_page_accepts_only_its_native_table_block():
    doc = document(method="hybrid")
    block = doc["pages"][0]["blocks"][0]
    block["origin"] = "native"
    link = dependencies(doc)["run:t"]
    assert link["header_rows"] == [0, 1]
    assert link["previous"] is None
    block["origin"] = "ocr"
    assert "run:t" not in dependencies(doc)


def test_horizontal_groups_keep_the_metric_tier_after_the_year():
    rows = [
        [cell("Ngành", "c00"), cell("Năm 2024", "c01", cs=2), cell("Năm 2025", "c03", cs=2)],
        [
            cell(text, f"c1{i}")
            for i, text in enumerate(["", "Chỉ tiêu", "Điểm", "Chỉ tiêu", "Điểm"])
        ],
        [cell(text, f"c2{i}") for i, text in enumerate(["Alpha", "80", "24.5", "75", "25.1"])],
        [cell(text, f"c3{i}") for i, text in enumerate(["Beta", "90", "20.0", "70", "21.2"])],
    ]
    for top in rows[0]:
        top["header"] = True
    assert multitier_header(table(rows, columns=5)) == [0, 1]
    native = document(rows, columns=5)
    native["pages"][0]["blocks"][0]["bbox"] = None
    assert dependencies(native)["run:t"]["header_rows"] == [0, 1]
    source = chunk(rows, [0, 1, 2, 3], key="E1", total=4, columns=5)
    result = catalog([source], [link_for("E1", "E1")])
    assert result["tables"][0]["fields"]["3"] == ["Năm 2025", "Chỉ tiêu"]
    assert result["tables"][0]["fields"]["4"] == ["Năm 2025", "Điểm"]
    rows[1][0]["text"] = "Tên một dòng dữ liệu"
    assert multitier_header(table(rows, columns=5)) is None


@pytest.mark.parametrize(
    "change",
    [
        "single_tier",
        "identity_too_wide",
        "too_few_rows",
        "no_numeric_column",
        "empty_header_cell",
        "unmerged_numeric_header",
        "incomplete_grid",
        "numeric_identity_label",
    ],
)
def test_multitier_proof_rejects_unproven_headers(change):
    rows = grid()
    if change == "single_tier":
        rows[0][0]["row_span"] = 1
    elif change == "identity_too_wide":
        rows[0][0]["col_span"] = 6
    elif change == "too_few_rows":
        rows = rows[:3]
    elif change == "no_numeric_column":
        for row in rows[2:]:
            for c in row:
                if any(ch.isdigit() for ch in c["text"]):
                    c["text"] = "n" + c["text"]
    elif change == "empty_header_cell":
        rows[1][0]["text"] = ""
    elif change == "unmerged_numeric_header":
        rows[0] = [
            rows[0][0],
            cell("2026", "t-0-1"),
            cell("2027", "t-0-2"),
            cell("2028", "t-0-3"),
        ]
    elif change == "incomplete_grid":
        rows[2].pop()
    else:
        rows[0][0]["text"] = "123"
    assert multitier_header(table(rows)) is None


def test_dependencies_emits_multitier_basis_with_header_rows():
    link = dependencies(document())["run:t"]
    assert link["basis"] == MULTITIER_BASIS
    assert link["header"] == "run:t"
    assert link["header_rows"] == [0, 1]
    assert link["previous"] is None
    assert link["chain"] == ["run:t"]


@pytest.mark.parametrize("gate", ["ocr", "review"])
def test_multitier_still_requires_native_clean_block(gate):
    doc = document(method="ocr" if gate == "ocr" else "native", review=gate == "review")
    assert "run:t" not in dependencies(doc)


def test_data_chunk_without_link_is_header_unresolved():
    data = chunk(grid()[2:5], [2, 3, 4], key="E2")
    result = catalog([data])
    assert result["tables"] == []
    assert result["issues"] == [{"evidence_id": "E2", "issues": ["header_unresolved"]}]


def test_catalog_borrows_multitier_headers_and_keeps_program_name():
    header = chunk(grid()[0:2], [0, 1], key="E1")
    data = chunk(grid()[2:5], [2, 3, 4], key="E2")
    cells = catalog([data, header], [link_for()])
    by_id = {t["evidence_id"]: t for t in cells["tables"]}
    # The header-only fragment carries no selectable value of its own.
    assert by_id["E1"]["cells"] == []
    assert by_id["E2"]["fields"]["3"] == ["2026", "Chỉ tiêu"]
    values = {c["cell_id"]: c for c in by_id["E2"]["cells"] if c["column"] >= 3}
    assert values["E2:r2:k3"]["subject"] == "Group A / Alpha"
    assert values["E2:r2:k3"]["value"] == "100"
    # The numeric program code is skipped so the following name survives.
    assert values["E2:r3:k3"]["subject"] == "Group A / Beta"
    assert values["E2:r4:k3"]["subject"] == "Group A / Gamma"
    assert set(values["E2:r2:k3"]["evidence_ids"]) == {"E1", "E2"}


def test_multitier_lookup_materializes_source_value():
    header = chunk(grid()[0:2], [0, 1], key="E1")
    data = chunk(grid()[2:5], [2, 3, 4], key="E2")
    sources = [data, header]
    cells = catalog(sources, [link_for()])
    draft = parse_answer(
        json.dumps({"status": "answered", "statements": [], "lookups": [{"cell_id": "E2:r2:k3"}]}),
        sources,
    )
    answer = materialize(draft, sources, cells)
    assert answer.statements[0].text == "Group A / Alpha — 2026 / Chỉ tiêu: 100"
    assert set(answer.statements[0].evidence_ids) == {"E1", "E2"}


def test_support_attaches_header_fragment_and_propagates_header_rows():
    header = SimpleNamespace(
        id="hdr",
        chunk_id="hdr",
        input_id="in",
        structure={
            "source_table_citation": "run:t",
            "row_indices": [0, 1],
            "original_row_count": 5,
        },
    )
    data = SimpleNamespace(
        id="data",
        chunk_id="data",
        input_id="in",
        structure={
            "source_table_citation": "run:t",
            "row_indices": [2, 3, 4],
            "original_row_count": 5,
        },
    )
    relationships = {
        ("in", "run:t"): {
            "basis": MULTITIER_BASIS,
            "header": "run:t",
            "chain": ["run:t"],
            "previous": None,
            "header_rows": [0, 1],
        }
    }
    selected, links = supports(
        [SimpleNamespace(chunk_id="data")], [header, data], relationships, MetadataFilter()
    )
    assert set(selected) == {"hdr"}
    assert links[0]["support_ids"] == ["hdr"]
    assert links[0]["header_rows"] == [0, 1]
    assert links[0]["basis"] == MULTITIER_BASIS
