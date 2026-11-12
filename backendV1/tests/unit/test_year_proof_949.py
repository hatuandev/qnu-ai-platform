"""Cell/row year proofs and multi-year child headers stay source-bound."""

import pytest

from qnu.domains.knowledge.compilation.table_year import data_year
from qnu.domains.knowledge.metadata import validate_annotations
from qnu.platform.errors import AppException
from tests.unit.test_table_year_scope_947 import RUN, TABLE, annotations, fixture
from tests.unit.test_vertical_merge_year_948 import merged


def cell_annotation(row, column, year, citation, quote):
    return {
        "target": f"table:{RUN}:{TABLE}:row:{row}:column:{column}",
        "values": {"data_year": year},
        "evidence": [{"citation": citation, "quote": quote}],
    }


def column_annotation(column, year, evidence):
    return {
        "target": f"table:{RUN}:{TABLE}:column:{column}",
        "values": {"data_year": year},
        "evidence": evidence,
    }


def row_annotation(row, year, citation, quote):
    return {
        "target": f"table:{RUN}:{TABLE}:row:{row}",
        "values": {"data_year": year},
        "evidence": [{"citation": citation, "quote": quote}],
    }


def test_cell_year_proven_by_its_governing_header_is_accepted():
    content, documents = merged()
    cell = cell_annotation(2, 2, 2027, f"{RUN}:{TABLE}-c1-1", "Chỉ tiêu năm 2027")
    validate_annotations([cell], content, documents, strict_roles=True)
    forged = cell_annotation(2, 2, 2027, f"{RUN}:{TABLE}-c1-0", "Chỉ tiêu năm 2026")
    with pytest.raises(AppException) as exc:
        validate_annotations([forged], content, documents, strict_roles=True)
    assert exc.value.code == "retrieval_metadata_invalid"


def test_cell_year_cannot_be_proven_by_a_quantity_cell():
    content, documents = fixture(
        headers=[["Ngành đào tạo", "Chỉ tiêu năm 2027"]],
        body=[["Công nghệ thông tin", "2027"]],
        columns=2,
    )
    forged = cell_annotation(1, 1, 2027, f"{RUN}:{TABLE}-c1-1", "2027")
    # Historical read path: the number exists in the cited cell.
    validate_annotations([forged], content, documents)
    with pytest.raises(AppException) as exc:
        validate_annotations([forged], content, documents, strict_roles=True)
    assert exc.value.code == "retrieval_metadata_invalid"


def test_column_year_quote_must_be_on_the_governing_header_cell():
    content, documents = fixture(
        headers=[["Ngành đào tạo", "Chỉ tiêu năm 2027"]],
        body=[["Công nghệ thông tin", "2027"]],
        columns=2,
    )
    forged = column_annotation(
        1,
        2027,
        [
            {"citation": f"{RUN}:{TABLE}-c0-1", "quote": "Chỉ tiêu"},
            {"citation": f"{RUN}:{TABLE}-c1-1", "quote": "2027"},
        ],
    )
    validate_annotations([forged], content, documents)
    with pytest.raises(AppException) as exc:
        validate_annotations([forged], content, documents, strict_roles=True)
    assert exc.value.code == "retrieval_metadata_invalid"


def test_row_year_cannot_be_proven_by_a_quantity_cell():
    content, documents = fixture(
        headers=[["Ngành đào tạo", "Chỉ tiêu"]],
        body=[["Công nghệ thông tin", "2027"]],
        columns=2,
    )
    forged = row_annotation(1, 2027, f"{RUN}:{TABLE}-c1-1", "2027")
    validate_annotations([forged], content, documents)
    with pytest.raises(AppException) as exc:
        validate_annotations([forged], content, documents, strict_roles=True)
    assert exc.value.code == "retrieval_metadata_invalid"


def test_row_year_proven_by_a_labelled_cell_in_its_row_is_accepted():
    content, documents = fixture(
        headers=[["Ngành đào tạo", "Chỉ tiêu"]],
        body=[["Mùa tuyển sinh 2027", "95"]],
        columns=2,
    )
    ok = row_annotation(1, 2027, f"{RUN}:{TABLE}-c1-0", "Mùa tuyển sinh 2027")
    validate_annotations([ok], content, documents, strict_roles=True)


def test_parent_single_year_never_overrides_a_multi_year_child_header():
    content, documents = fixture(
        headers=[
            ["Ngành đào tạo", {"text": "Kế hoạch năm 2027", "col_span": 2}],
            ["Ghi chú", "Chỉ tiêu năm 2026 và 2027", "Chỉ tiêu"],
        ],
        body=[["Công nghệ thông tin", "95", "80"]],
        columns=3,
    )
    found = annotations(content, documents)
    assert f"table:{RUN}:{TABLE}:column:1" not in found
    assert found[f"table:{RUN}:{TABLE}:column:2"]["values"] == {"data_year": 2027}


def test_abbreviated_year_range_header_stays_unknown():
    assert data_year("Chỉ tiêu năm 2026-27") is None
    content, documents = fixture(
        headers=[["Ngành đào tạo", "Chỉ tiêu năm 2026-27"]],
        body=[["Công nghệ thông tin", "95"]],
        columns=2,
    )
    assert not [
        item for item in annotations(content, documents).values() if item["target"].startswith("table:")
    ]


def test_multi_year_parent_header_never_scopes_its_columns():
    content, documents = fixture(
        headers=[["Ngành đào tạo", {"text": "Kế hoạch năm 2026-2027", "col_span": 2}]],
        body=[["Công nghệ thông tin", "95", "80"]],
        columns=3,
    )
    assert not [
        item for item in annotations(content, documents).values() if item["target"].startswith("table:")
    ]
