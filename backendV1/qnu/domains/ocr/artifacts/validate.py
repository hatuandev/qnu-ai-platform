"""Technical completeness checks for a finished generation.

These checks answer one question only: is the evidence complete and self-consistent?
A run that passes them is *technically processed*; nothing here approves content or
publishes knowledge. A blank page that the renderer measured as blank is valid; a page
the provider failed to return is not, and the two are never merged into one status.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from qnu.domains.ocr.layout import Cell, _table_grid


@dataclass(frozen=True, slots=True)
class Issue:
    code: str
    detail: str
    page: int | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "detail": self.detail}
        if self.page is not None:
            payload["page"] = self.page
        return payload


@dataclass(frozen=True, slots=True)
class Report:
    errors: tuple[Issue, ...] = ()
    warnings: tuple[Issue, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": [issue.as_dict() for issue in self.errors],
            "warnings": [issue.as_dict() for issue in self.warnings],
        }


def _valid_bbox(bbox: dict[str, Any]) -> bool:
    try:
        x0, y0, x1, y1 = (float(bbox[key]) for key in ("x0", "y0", "x1", "y1"))
    except (KeyError, TypeError, ValueError):
        return False
    if not all(math.isfinite(value) for value in (x0, y0, x1, y1)):
        return False
    return 0.0 <= x0 < x1 <= 1.0 and 0.0 <= y0 < y1 <= 1.0


def _table_reconstructable(table: dict[str, Any]) -> bool:
    rows: list[list[Cell]] = []
    for row in table.get("rows") or []:
        cells = [
            Cell(
                text=cell.get("text") or "",
                row_span=int(cell.get("row_span") or 1),
                col_span=int(cell.get("col_span") or 1),
                header=bool(cell.get("header")),
            )
            for cell in row
        ]
        rows.append(cells)
    return _table_grid(rows, int(table.get("column_count") or 0))


def validate_document(canonical: dict[str, Any], *, expected_pages: int) -> Report:
    errors: list[Issue] = []
    warnings: list[Issue] = []
    pages = canonical.get("pages") or []

    if len(pages) != expected_pages:
        errors.append(
            Issue(
                "page_count_mismatch",
                f"Canonical có {len(pages)} trang nhưng bản render có {expected_pages} trang.",
            )
        )

    expected_numbers = list(range(1, len(pages) + 1))
    actual_numbers = [int(page.get("page_number") or 0) for page in pages]
    if actual_numbers != expected_numbers:
        errors.append(Issue("page_order_invalid", "Thứ tự trang không liên tục từ 1."))

    seen_evidence: set[str] = set()
    evidence_index = canonical.get("evidence") or {}

    for page in pages:
        number = int(page.get("page_number") or 0)
        status = page.get("status")
        blocks = page.get("blocks") or []

        if status == "failed":
            errors.append(
                Issue("page_ocr_failed", page.get("error") or "Trang không nhận dạng được.", number)
            )
        elif status == "uncertain":
            errors.append(
                Issue(
                    "page_ocr_uncertain",
                    page.get("error") or "Chưa xác định được kết quả gọi provider.",
                    number,
                )
            )
        elif status == "completed" and not any(block.get("text") for block in blocks):
            errors.append(
                Issue(
                    "page_without_content",
                    "Trang ở trạng thái có nội dung nhưng không có khối nào.",
                    number,
                )
            )
        elif status == "blank" and any(block.get("text") for block in blocks):
            warnings.append(
                Issue("blank_page_has_text", "Trang đo là trắng nhưng provider trả về chữ.", number)
            )

        for block in blocks:
            block_id = block.get("evidence_id")
            if not block_id:
                errors.append(Issue("evidence_missing", "Khối thiếu evidence_id.", number))
            elif block_id in seen_evidence:
                errors.append(Issue("evidence_duplicate", f"evidence_id trùng: {block_id}", number))
            else:
                seen_evidence.add(block_id)
            if block_id and block_id not in evidence_index:
                errors.append(
                    Issue("evidence_unmapped", f"Không có mapping cho {block_id}", number)
                )
            locator = block.get("source_locator") or {}
            pagination = (
                canonical.get("processing", {}).get("renderer", {}).get("pagination")
            )
            direct_native = (
                (
                    pagination == "document"
                    and locator.get("format") == "docx"
                    and bool(locator.get("docling_ref"))
                )
                or (pagination == "sheets" and locator.get("format") == "xlsx")
                or (
                    pagination in {"document", "slides"}
                    and locator.get("format") in {"pptx", "md", "txt"}
                )
            )
            if not _valid_bbox(block.get("bbox") or {}) and not (
                direct_native and not block.get("bbox")
            ):
                errors.append(
                    Issue("block_bbox_invalid", f"bbox không hợp lệ ở {block_id}", number)
                )

            table = block.get("table")
            if table is None:
                continue
            if table.get("status") == "parsed":
                if not table.get("rows") or not _table_reconstructable(table):
                    errors.append(
                        Issue(
                            "table_grid_inconsistent",
                            f"Bảng không tái dựng được ở {block_id}",
                            number,
                        )
                    )
                for row in table.get("rows") or []:
                    for cell in row:
                        cell_id = cell.get("evidence_id")
                        if not cell_id:
                            errors.append(Issue("evidence_missing", "Ô thiếu evidence_id.", number))
                            continue
                        if cell_id in seen_evidence:
                            errors.append(
                                Issue("evidence_duplicate", f"evidence_id trùng: {cell_id}", number)
                            )
                        else:
                            seen_evidence.add(cell_id)
                        if cell_id not in evidence_index:
                            errors.append(
                                Issue(
                                    "evidence_unmapped", f"Không có mapping cho {cell_id}", number
                                )
                            )
            else:
                warnings.append(
                    Issue(
                        "table_unreconstructable",
                        f"Bảng giữ nguyên raw, lý do: {table.get('reason')}",
                        number,
                    )
                )

    return Report(errors=tuple(errors), warnings=tuple(warnings))


def run_status(pages: list[dict[str, Any]], report: Report) -> str:
    """A run never reports success while a page is uncertain or the evidence is incomplete."""
    if any(page.get("status") == "uncertain" for page in pages):
        return "uncertain"
    if report.errors:
        return "failed"
    return "completed"
