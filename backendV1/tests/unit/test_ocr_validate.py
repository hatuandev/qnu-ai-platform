"""Validation catches broken evidence instead of letting a run look successful."""

from __future__ import annotations

import copy

from qnu.domains.ocr.artifacts.canonical import PageDocument, build_canonical
from qnu.domains.ocr.artifacts.render import PageImage, RenderedDocument
from qnu.domains.ocr.artifacts.validate import validate_document
from qnu.domains.ocr.layout import parse_page

RAW = (
    "<x_0.10><y_0.10>PHỤ LỤC 01<x_0.90><y_0.15><class_Title>"
    "<x_0.10><y_0.20>\\begin{tabular}{cc} \\hline \\thead{Chỉ tiêu} & \\thead{2023} \\\\ "
    "Tuyển sinh & 0 \\\\ \\end{tabular}<x_0.90><y_0.60><class_Table>"
)

UNSUPPORTED_RAW = (
    "<x_0.10><y_0.20>\\begin{tabular}{cc} a & b & c \\\\ d \\\\ \\end{tabular}"
    "<x_0.90><y_0.60><class_Table>"
)


def _canonical(raw: str = RAW) -> dict:
    rendered = RenderedDocument(
        extension=".pdf",
        renderer={"converter": "pdf-direct", "dpi": 144},
        pages=(
            PageImage(
                page_number=1,
                png=b"\x89PNG",
                width=1190,
                height=1684,
                sha256="0" * 63 + "1",
                blank=False,
                ink_ratio=0.002,
            ),
        ),
    )
    return build_canonical(
        identity={"run_id": "ocr_1", "generation": 1, "revision_id": "rev_1"},
        processing={"processor_version": "qnu-ocr/v1"},
        rendered=rendered,
        pages=[
            PageDocument(
                page_number=1,
                status="completed",
                image_sha256="0" * 63 + "1",
                image_width=1190,
                image_height=1684,
                ink_ratio=0.002,
                layout=parse_page(raw),
                usage_tokens=140,
            )
        ],
        limits={"dpi": 144},
    )


def _codes(report) -> set[str]:
    return {issue.code for issue in report.errors}


def test_a_clean_document_has_no_errors() -> None:
    assert validate_document(_canonical(), expected_pages=1).ok is True


def test_page_order_must_be_contiguous_from_one() -> None:
    canonical = _canonical()
    canonical["pages"][0]["page_number"] = 2
    assert "page_order_invalid" in _codes(validate_document(canonical, expected_pages=1))


def test_a_block_without_evidence_id_is_an_error() -> None:
    canonical = copy.deepcopy(_canonical())
    canonical["pages"][0]["blocks"][0]["evidence_id"] = None
    assert "evidence_missing" in _codes(validate_document(canonical, expected_pages=1))


def test_duplicate_evidence_id_is_an_error() -> None:
    canonical = copy.deepcopy(_canonical())
    blocks = canonical["pages"][0]["blocks"]
    blocks[1]["evidence_id"] = blocks[0]["evidence_id"]
    assert "evidence_duplicate" in _codes(validate_document(canonical, expected_pages=1))


def test_evidence_without_a_mapping_is_an_error() -> None:
    canonical = copy.deepcopy(_canonical())
    block_id = canonical["pages"][0]["blocks"][0]["evidence_id"]
    canonical["evidence"].pop(block_id)
    assert "evidence_unmapped" in _codes(validate_document(canonical, expected_pages=1))


def test_invalid_bbox_is_an_error() -> None:
    canonical = copy.deepcopy(_canonical())
    canonical["pages"][0]["blocks"][0]["bbox"]["x1"] = 1.4
    assert "block_bbox_invalid" in _codes(validate_document(canonical, expected_pages=1))


def test_inconsistent_table_grid_is_an_error() -> None:
    canonical = copy.deepcopy(_canonical())
    table = canonical["pages"][0]["blocks"][1]["table"]
    table["rows"][1].pop()
    assert "table_grid_inconsistent" in _codes(validate_document(canonical, expected_pages=1))


def test_unreconstructable_table_is_a_warning_with_raw_kept() -> None:
    canonical = _canonical(UNSUPPORTED_RAW)
    report = validate_document(canonical, expected_pages=1)
    assert report.ok is True
    assert "table_unreconstructable" in {issue.code for issue in report.warnings}
    table = canonical["pages"][0]["blocks"][0]["table"]
    assert table["status"] == "unsupported"
    assert table["reason"]
    assert canonical["pages"][0]["blocks"][0]["text"]


def test_blank_page_that_returned_text_is_a_warning() -> None:
    canonical = copy.deepcopy(_canonical())
    canonical["pages"][0]["status"] = "blank"
    report = validate_document(canonical, expected_pages=1)
    assert "blank_page_has_text" in {issue.code for issue in report.warnings}
