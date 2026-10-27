"""The canonical document and its validation: evidence must be complete and pinned.

These tests build the canonical payload from parsed layouts, so they cover the mapping
between a derived block/cell and its page, bbox and stable evidence id.
"""

from __future__ import annotations

import json

from qnu.domains.ocr.artifacts.canonical import (
    PageDocument,
    build_canonical,
    build_manifest,
    evidence_id,
    render_markdown,
)
from qnu.domains.ocr.artifacts.render import PageImage, RenderedDocument
from qnu.domains.ocr.artifacts.validate import run_status, validate_document
from qnu.domains.ocr.layout import parse_page

IDENTITY = {
    "workspace_id": "ws_1",
    "collection_id": "col_1",
    "source_id": "src_1",
    "revision_id": "rev_1",
    "revision_no": 2,
    "source_sha256": "a" * 64,
    "run_id": "ocr_1",
    "generation": 1,
}
PROCESSING = {
    "processor_version": "qnu-ocr/v1",
    "prompt_version": "nemotron-parse/v1",
    "table_layout_version": "nemotron-tabular/v1",
    "config_fingerprint": "b" * 64,
    "renderer": {"converter": "pymupdf", "dpi": 144},
    "provider": {"provider_id": "prv_1", "model_name": "nemotron-parse"},
    "started_at": "2026-10-26T00:00:00+00:00",
    "finished_at": "2026-10-26T00:00:10+00:00",
    "warnings": [],
}
LIMITS = {"max_pages": 300, "dpi": 144, "max_output_tokens": 8192, "max_page_bytes": 8388608}


def _rendered(pages: int, *, blank: tuple[int, ...] = ()) -> RenderedDocument:
    return RenderedDocument(
        extension=".pdf",
        renderer={"converter": "pymupdf", "dpi": 144},
        pages=tuple(
            PageImage(
                page_number=number,
                png=b"\x89PNG",
                width=1190,
                height=1684,
                sha256=f"{number:064d}",
                blank=number in blank,
                ink_ratio=0.0 if number in blank else 0.0021,
            )
            for number in range(1, pages + 1)
        ),
    )


def _document(number: int, raw: str | None, status: str = "completed") -> PageDocument:
    return PageDocument(
        page_number=number,
        status=status,
        image_sha256=f"{number:064d}",
        image_width=1190,
        image_height=1684,
        ink_ratio=0.0021,
        layout=parse_page(raw) if raw is not None else None,
        usage_tokens=140 if status == "completed" else None,
    )


def _canonical(pages: list[PageDocument], *, rendered: RenderedDocument | None = None) -> dict:
    return build_canonical(
        identity=IDENTITY,
        processing=PROCESSING,
        rendered=rendered or _rendered(len(pages)),
        pages=pages,
        limits=LIMITS,
    )


TABLE_RAW = (
    "<x_0.10><y_0.10>PHỤ LỤC 01<x_0.90><y_0.15><class_Title>"
    "<x_0.10><y_0.20>\\begin{tabular}{ccc} \\hline \\thead{Chỉ tiêu} & \\thead{2023} "
    "& \\thead{2024} \\\\ Tuyển sinh & 0 & - \\\\ Trúng tuyển & & 150 \\\\ "
    "\\end{tabular}<x_0.90><y_0.60><class_Table>"
    "<x_0.10><y_0.90>Ghi chú: số liệu năm 2023.<x_0.90><y_0.95><class_Footnote>"
)


def test_canonical_pins_identity_processing_and_limits() -> None:
    canonical = _canonical([_document(1, TABLE_RAW)])
    assert canonical["schema_version"] == "qnu.ocr.document/v1"
    assert canonical["identity"]["revision_id"] == "rev_1"
    assert canonical["identity"]["source_sha256"] == "a" * 64
    assert canonical["identity"]["generation"] == 1
    assert canonical["processing"]["provider"]["model_name"] == "nemotron-parse"
    assert canonical["limits"] == LIMITS


def test_bbox_units_and_block_order_are_explicit() -> None:
    canonical = _canonical([_document(1, TABLE_RAW)])
    blocks = canonical["pages"][0]["blocks"]
    assert [block["order"] for block in blocks] == [1, 2, 3]
    assert blocks[0]["bbox"]["units"] == "normalized_0_1"
    assert blocks[0]["type"] == "title"
    assert blocks[2]["type"] == "footnote"


def test_evidence_ids_are_stable_and_cover_every_cell() -> None:
    canonical = _canonical([_document(1, TABLE_RAW)])
    table = canonical["pages"][0]["blocks"][1]["table"]
    assert table["status"] == "parsed"
    assert table["column_count"] == 3
    assert table["rows"][1][1]["text"] == "0"
    assert table["rows"][1][2]["text"] == "-"
    assert table["rows"][2][1]["text"] == ""
    cell_id = table["rows"][1][1]["evidence_id"]
    assert cell_id == evidence_id(1, 2, (1, 1))
    assert cell_id in canonical["evidence"]
    assert canonical["evidence"][cell_id]["kind"] == "table_cell"
    for block in canonical["pages"][0]["blocks"]:
        assert block["evidence_id"] in canonical["evidence"]


def test_evidence_ids_are_deterministic_across_rebuilds() -> None:
    first = _canonical([_document(1, TABLE_RAW)])
    second = _canonical([_document(1, TABLE_RAW)])
    assert list(first["evidence"]) == list(second["evidence"])


def test_missing_page_is_detected() -> None:
    canonical = _canonical([_document(1, TABLE_RAW)])
    report = validate_document(canonical, expected_pages=2)
    assert report.ok is False
    assert "page_count_mismatch" in {issue.code for issue in report.errors}


def test_failed_page_is_an_error_and_blank_page_is_not() -> None:
    failed = _canonical([_document(1, None, status="failed")])
    assert "page_ocr_failed" in {issue.code for issue in validate_document(failed, expected_pages=1).errors}

    blank = _canonical(
        [PageDocument(page_number=1, status="blank", image_sha256="1" * 64, image_width=1190,
                      image_height=1684, ink_ratio=0.0)],
        rendered=_rendered(1, blank=(1,)),
    )
    report = validate_document(blank, expected_pages=1)
    assert report.ok is True


def test_page_with_ink_but_no_text_is_an_error() -> None:
    canonical = _canonical([_document(1, "")])
    codes = {issue.code for issue in validate_document(canonical, expected_pages=1).errors}
    assert "page_without_content" in codes


def test_uncertain_page_wins_over_a_clean_report() -> None:
    pages = [{"status": "completed"}, {"status": "uncertain"}]
    assert run_status(pages, validate_document(_canonical([_document(1, TABLE_RAW)]), expected_pages=1)) == "uncertain"


def test_manifest_checksums_match_the_payloads() -> None:
    canonical = _canonical([_document(1, TABLE_RAW)])
    report = validate_document(canonical, expected_pages=1)
    manifest = build_manifest(
        canonical=canonical,
        artifacts=[
            {"kind": "page_image", "page_no": 1, "sha256": "c" * 64, "size_bytes": 10,
             "content_type": "image/png", "blob_key": "v1/p.png"},
        ],
        validation=report.as_dict(),
        canonical_sha256="d" * 64,
        markdown_sha256="e" * 64,
    )
    assert manifest["schema_version"] == "qnu.ocr.manifest/v1"
    assert manifest["checks"]["canonical_sha256"] == "d" * 64
    assert manifest["checks"]["markdown_sha256"] == "e" * 64
    assert manifest["checks"]["pages_completed"] == 1
    assert manifest["checks"]["pages_failed"] == 0
    assert manifest["checks"]["page_image_sha256"] == {"1": f"{1:064d}"}
    assert manifest["artifacts"][0]["sha256"] == "c" * 64
    assert manifest["validation"]["ok"] is True


def test_markdown_keeps_literal_values_and_points_back_to_pages() -> None:
    markdown = render_markdown(_canonical([_document(1, TABLE_RAW)]))
    assert "<!-- page 1 -->" in markdown
    assert "PHỤ LỤC 01" in markdown
    assert ">0<" in markdown
    assert ">-<" in markdown
    assert "Ghi chú: số liệu năm 2023." in markdown


def test_canonical_survives_a_json_round_trip_unchanged() -> None:
    canonical = _canonical([_document(1, TABLE_RAW)])
    payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True)
    assert json.loads(payload) == canonical
    # Unknown usage is null, never zero: zero would claim a measurement we did not make.
    assert canonical["pages"][0]["usage_tokens"] == 140
    assert canonical["unknowns"] == canonical.get("unknowns")
