"""Vertically merged header rows keep physical columns; year proof is the governing header."""

import pytest

from qnu.domains.knowledge.compilation.supplement import _targets
from qnu.domains.knowledge.metadata import validate_annotations
from qnu.domains.knowledge.publication.automatic_metadata import preview
from qnu.domains.rag.answer.cells import catalog
from qnu.domains.rag.answer.table_selection import select_catalog
from qnu.platform.errors import AppException
from tests.unit.test_table_year_scope_947 import (
    RUN,
    TABLE,
    evidence_source,
    fixture,
    published,
    table_chunk,
)


def merged(*, second_year="2027"):
    return fixture(
        headers=[
            [
                {"text": "Ngành đào tạo", "row_span": 2},
                {"text": "Kế hoạch tuyển sinh", "col_span": 2},
            ],
            ["Chỉ tiêu năm 2026", f"Chỉ tiêu năm {second_year}"],
        ],
        body=[["Công nghệ thông tin", "31", "47"]],
        columns=3,
    )


def year_annotation(column, year, citation, quote):
    return {
        "target": f"table:{RUN}:{TABLE}:column:{column}",
        "values": {"data_year": year},
        "evidence": [{"citation": citation, "quote": quote}],
    }


def selection(content, documents, year):
    found = preview(published(content, documents))["annotations"]
    _, chunk = table_chunk(content, documents, found)
    source = evidence_source(chunk)
    cells = catalog([source])
    narrowed = select_catalog(
        cells,
        [source],
        f"Chỉ tiêu năm {year} của ngành Công nghệ thông tin",
        [],
        data_years={year},
    )
    values = {
        (cell["column"], cell["value"]) for table in narrowed["tables"] for cell in table["cells"]
    }
    chosen = {cell["value"]: cell for table in narrowed["tables"] for cell in table["cells"]}
    return found, chunk, values, chosen


def test_vertically_merged_header_keeps_each_year_on_its_physical_column():
    content, documents = merged()
    found, chunk, values, chosen = selection(content, documents, 2027)
    by_target = {item["target"]: item for item in found}
    assert by_target[f"table:{RUN}:{TABLE}:column:1"]["values"] == {"data_year": 2026}
    assert by_target[f"table:{RUN}:{TABLE}:column:2"]["values"] == {"data_year": 2027}
    assert by_target[f"table:{RUN}:{TABLE}:column:2"]["evidence"] == [
        {"citation": f"{RUN}:{TABLE}-c1-1", "quote": "Chỉ tiêu năm 2027"}
    ]
    assert {item["target"] for item in chunk.structure["retrieval_metadata"]} == {
        f"table:{RUN}:{TABLE}:column:1",
        f"table:{RUN}:{TABLE}:column:2",
    }
    assert (2, "47") in values
    assert all(value != "31" for _, value in values)
    # The value keeps its own cell, subject and physical column header.
    assert f"{RUN}:{TABLE}-c2-2" in chosen["47"]["source_cells"]
    assert f"{RUN}:{TABLE}-c1-1" in chosen["47"]["source_cells"]
    assert f"{RUN}:{TABLE}-c0-0" in chosen["47"]["source_cells"]


def test_reverse_year_filters_the_other_physical_column():
    content, documents = merged()
    _, _, values, chosen = selection(content, documents, 2026)
    assert (1, "31") in values
    assert all(value != "47" for _, value in values)
    assert f"{RUN}:{TABLE}-c1-0" in chosen["31"]["source_cells"]


def test_conflicting_header_years_for_one_column_stay_unknown():
    content, documents = fixture(
        headers=[
            [
                {"text": "Ngành đào tạo", "row_span": 2},
                {"text": "Kế hoạch năm 2026"},
            ],
            ["Chỉ tiêu năm 2027"],
        ],
        body=[["Công nghệ thông tin", "47"]],
        columns=2,
    )
    found = preview(published(content, documents))["annotations"]
    assert not [item for item in found if item["target"].startswith("table:")]


def test_broken_table_structure_never_scopes_a_year():
    content, documents = merged()
    content["source_tables"][0]["table"]["rows"][1] = content["source_tables"][0]["table"]["rows"][
        1
    ][:1]
    found = preview(published(content, documents))["annotations"]
    assert not [item for item in found if item["target"].startswith("table:")]


def test_compiler_targets_use_physical_columns_for_merged_header_rows():
    content, documents = merged()
    targets = _targets(content)
    assert f"table:{RUN}:{TABLE}:row:1:column:2" in targets[f"{RUN}:{TABLE}-c1-1"]
    assert f"table:{RUN}:{TABLE}:row:1:column:1" not in targets[f"{RUN}:{TABLE}-c1-1"]
    ok = {
        "target": f"table:{RUN}:{TABLE}:row:1:column:2",
        "values": {"data_year": 2027},
        "evidence": [{"citation": f"{RUN}:{TABLE}-c1-1", "quote": "Chỉ tiêu năm 2027"}],
    }
    validate_annotations([ok], content, documents)


def test_column_year_requires_the_governing_header_as_evidence():
    content, documents = merged()
    validate_annotations(
        [year_annotation(2, 2027, f"{RUN}:{TABLE}-c1-1", "Chỉ tiêu năm 2027")],
        content,
        documents,
        strict_roles=True,
    )
    with pytest.raises(AppException) as exc:
        validate_annotations(
            [year_annotation(2, 2027, f"{RUN}:{TABLE}-c1-0", "Chỉ tiêu năm 2026")],
            content,
            documents,
            strict_roles=True,
        )
    assert exc.value.code == "retrieval_metadata_invalid"


def test_quantity_cell_value_cannot_prove_a_column_year():
    content, documents = fixture(
        headers=[["Ngành đào tạo", "Chỉ tiêu năm 2027"]],
        body=[["Công nghệ thông tin", "2027"]],
        columns=2,
    )
    forged = year_annotation(1, 2027, f"{RUN}:{TABLE}-c1-1", "2027")
    # Historical read path: the number exists in the cited cell.
    validate_annotations([forged], content, documents)
    with pytest.raises(AppException) as exc:
        validate_annotations([forged], content, documents, strict_roles=True)
    assert exc.value.code == "retrieval_metadata_invalid"


def test_short_quote_cannot_hide_an_issuance_year_header():
    content, documents = fixture(
        headers=[["Ngành đào tạo", "Năm ban hành 2027"]],
        body=[["Công nghệ thông tin", "95"]],
        columns=2,
    )
    forged = year_annotation(1, 2027, f"{RUN}:{TABLE}-c0-1", "2027")
    validate_annotations([forged], content, documents)
    with pytest.raises(AppException) as exc:
        validate_annotations([forged], content, documents, strict_roles=True)
    assert exc.value.code == "retrieval_metadata_invalid"


def test_horizontally_merged_header_proves_every_governed_column():
    content, documents = fixture(
        headers=[[{"text": "Ngành đào tạo"}, {"text": "Chỉ tiêu năm 2027", "col_span": 2}]],
        body=[["Công nghệ thông tin", "80", "15"]],
        columns=3,
    )
    for column in (1, 2):
        validate_annotations(
            [year_annotation(column, 2027, f"{RUN}:{TABLE}-c0-1", "Chỉ tiêu năm 2027")],
            content,
            documents,
            strict_roles=True,
        )


def test_old_registered_row_coordinates_remain_readable():
    content, documents = merged()
    old = {
        "target": f"table:{RUN}:{TABLE}:row:1:column:0",
        "values": {"data_year": 2026},
        "evidence": [{"citation": f"{RUN}:{TABLE}-c1-0", "quote": "Chỉ tiêu năm 2026"}],
    }
    # Read path keeps validating previously registered metadata with row-local
    # list coordinates, without rewriting stored versions or indexes.
    validate_annotations([old], content, documents)
