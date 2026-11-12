"""Canonical document, derived Markdown and manifest for one OCR generation.

The canonical JSON is the only structure a later Compiler reads. It pins identity
(workspace → collection → source → revision → run/generation), the real provider and
processor versions, page and block order, literal text, bounding boxes with their
unit, table cells with spans, and an evidence index that maps every derived piece
back to the page/block/cell and to the artifact that proves it.

Evidence identifiers are stable inside one generation: they are derived from page
number and response order, not from a random value.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any

from qnu.domains.ocr.artifacts.render import RenderedDocument
from qnu.domains.ocr.config import CANONICAL_SCHEMA, MANIFEST_SCHEMA, MARKDOWN_VERSION
from qnu.domains.ocr.layout import PageLayout, Table

BBOX_UNITS = "normalized_0_1"


@dataclass(frozen=True, slots=True)
class PageDocument:
    """One page of the run: what was rendered and what the provider returned."""

    page_number: int
    status: str
    image_sha256: str | None
    image_width: int | None
    image_height: int | None
    ink_ratio: float | None
    layout: PageLayout | None = None
    error_code: str | None = None
    usage_tokens: int | None = None
    method: str | None = None
    image_ocr_failures: tuple[dict[str, Any], ...] = ()


def evidence_id(page: int, block_order: int, cell: tuple[int, int] | None = None) -> str:
    base = f"ev_p{page:03d}_b{block_order:03d}"
    if cell is None:
        return base
    return f"{base}_c{cell[0]:02d}_{cell[1]:02d}"


def _table_payload(table: Table, page: int, block_order: int) -> dict[str, Any]:
    rows: list[list[dict[str, Any]]] = []
    for row_index, row in enumerate(table.rows):
        cells: list[dict[str, Any]] = []
        for column_index, cell in enumerate(row):
            cells.append(
                {
                    "evidence_id": evidence_id(page, block_order, (row_index, column_index)),
                    "text": cell.text,
                    "row_span": cell.row_span,
                    "col_span": cell.col_span,
                    "header": cell.header,
                }
            )
        rows.append(cells)
    payload = {
        "evidence_id": evidence_id(page, block_order),
        "status": table.status,
        "reason": table.reason,
        "column_count": table.column_count,
        "row_count": len(table.rows),
        "rows": rows,
    }
    if table.source_mapping is not None:
        payload["source_mapping"] = table.source_mapping
    return payload


def build_canonical(
    *,
    identity: dict[str, Any],
    processing: dict[str, Any],
    rendered: RenderedDocument,
    pages: list[PageDocument],
    limits: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the canonical document; no value is inferred beyond what was measured."""
    page_payloads: list[dict[str, Any]] = []
    evidence: dict[str, dict[str, Any]] = {}
    failed_images: list[dict[str, Any]] = []

    for document in pages:
        page_index = document.page_number - 1
        blocks: list[dict[str, Any]] = []
        warnings: list[str] = []
        failures = [dict(item) for item in document.image_ocr_failures]
        warnings.extend(f"image_ocr_failed:{item['image_asset_no']}" for item in failures)
        if document.layout is not None:
            warnings.extend(document.layout.warnings)
            for block in document.layout.blocks:
                block_id = evidence_id(document.page_number, block.order)
                payload: dict[str, Any] = {
                    "evidence_id": block_id,
                    "order": block.order,
                    "type": block.kind,
                    "label": block.label,
                    "text": block.text,
                    "bbox": {},
                    "requires_review": block.requires_review,
                }
                if block.bbox is not None:
                    payload["bbox"] = dict(
                        zip(("x0", "y0", "x1", "y1"), block.bbox, strict=True),
                        units="normalized_image_0_1"
                        if block.source_locator and block.source_image_asset_no
                        else BBOX_UNITS,
                    )
                if block.source_locator:
                    payload["source_locator"] = block.source_locator
                artifact = "native_page" if block.origin == "native" else "raw_response"
                if block.origin == "native":
                    payload["origin"] = "native"
                if block.image:
                    payload["image"] = block.image
                if block.source_image_asset_no is not None:
                    payload["source_image_asset_no"] = block.source_image_asset_no
                evidence[block_id] = {
                    "kind": "block",
                    "page": document.page_number,
                    "path": f"pages[{page_index}].blocks[{len(blocks)}]",
                    "artifact": artifact,
                }
                if block.source_locator:
                    evidence[block_id]["source_locator"] = block.source_locator
                if block.table is not None:
                    table = _table_payload(block.table, document.page_number, block.order)
                    payload["table"] = table
                    evidence[table["evidence_id"]] = {
                        "kind": "table",
                        "page": document.page_number,
                        "path": f"pages[{page_index}].blocks[{len(blocks)}].table",
                        "artifact": artifact,
                    }
                    if block.source_locator:
                        evidence[block_id]["source_locator"] = block.source_locator
                    omitted = {
                        (y, i)
                        for y, i, _ in (table.get("source_mapping") or {}).get("omitted_slots", ())
                    }
                    for row_index, row in enumerate(table["rows"]):
                        for column_index, cell in enumerate(row):
                            evidence[cell["evidence_id"]] = {
                                "kind": "table_cell",
                                "page": document.page_number,
                                "path": (
                                    f"pages[{page_index}].blocks[{len(blocks)}]"
                                    f".table.rows[{row_index}][{column_index}]"
                                ),
                                "artifact": artifact,
                            }
                            if block.source_locator:
                                evidence[cell["evidence_id"]]["source_locator"] = {
                                    **block.source_locator,
                                    "row": row_index,
                                    "cell": column_index,
                                    "omitted": (row_index, column_index) in omitted,
                                }
                blocks.append(payload)

        page_payload: dict[str, Any] = {
            "page_number": document.page_number,
            "status": document.status,
            "image": {
                "sha256": document.image_sha256,
                "width": document.image_width,
                "height": document.image_height,
                "ink_ratio": document.ink_ratio,
            },
            "blocks": blocks,
            "warnings": warnings,
            "error": document.error_code,
            "usage_tokens": document.usage_tokens,
        }
        if failures:
            page_payload["image_ocr_failures"] = failures
            failed_images.extend(failures)
        page_payloads.append(page_payload)
        if document.method:
            page_payloads[-1]["extraction_method"] = document.method

    canonical: dict[str, Any] = {
        "schema_version": CANONICAL_SCHEMA,
        "identity": identity,
        "processing": processing,
        "pages": page_payloads,
        "evidence": evidence,
        "limits": limits,
        "unknowns": [
            "layout_confidence",
            "text_confidence",
            "provider_usage_per_page_when_absent",
        ]
        + (
            [
                "word_pagination"
                if (processing.get("renderer") or {}).get("pagination") == "document"
                else "native_pdf_header_roles",
                "image_semantics_unverified",
            ]
            if processing.get("extraction")
            else []
        ),
    }
    if failed_images:
        canonical["image_ocr_failures"] = failed_images
    return canonical


def _table_html(table: dict[str, Any]) -> str:
    parts = ['<table class="ocr">']
    for row in table["rows"]:
        parts.append("<tr>")
        for cell in row:
            tag = "th" if cell["header"] else "td"
            attributes = ""
            if cell["col_span"] > 1:
                attributes += f' colspan="{cell["col_span"]}"'
            if cell["row_span"] > 1:
                attributes += f' rowspan="{cell["row_span"]}"'
            parts.append(f"<{tag}{attributes}>{escape(cell['text'])}</{tag}>")
        parts.append("</tr>")
    parts.append("</table>")
    return "".join(parts)


def render_markdown(canonical: dict[str, Any]) -> str:
    """Derived Markdown keeps literal text and marks each page; tables stay structured."""
    identity = canonical["identity"]
    lines = [
        f"<!-- {MARKDOWN_VERSION} -->",
        f"<!-- source_sha256: {identity['source_sha256']} -->",
        f"<!-- run_id: {identity['run_id']} generation: {identity['generation']} -->",
        "",
    ]
    renderer = canonical.get("processing", {}).get("renderer", {})
    unit = "document" if renderer.get("pagination") == "document" else "page"
    for page in canonical["pages"]:
        lines.append(f"<!-- {unit} {page['page_number']} -->")
        if page["status"] in {"failed", "uncertain"}:
            lines.append(f"<!-- page_status: {page['status']} error: {page['error']} -->")
            lines.append("")
            continue
        if page["status"] == "blank":
            lines.append("<!-- page_status: blank -->")
            lines.append("")
            continue
        for failure in page.get("image_ocr_failures", ()):
            bbox = failure.get("bbox")
            box = f" bbox={bbox}" if bbox is not None else ""
            lines.append(
                f"<!-- image_ocr_failed: asset={failure['image_asset_no']}{box}"
                f" error={failure['error_code']} -->"
            )
        for block in page["blocks"]:
            if image := block.get("image"):
                lines.append(f"![Ảnh trong tài liệu]({image['filename']})")
                lines.append("")
            table = block.get("table")
            if table is not None and table["status"] == "parsed":
                lines.append(_table_html(table))
                lines.append("")
                continue
            if block["text"]:
                lines.append(block["text"])
                lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_manifest(
    *,
    canonical: dict[str, Any],
    artifacts: list[dict[str, Any]],
    validation: dict[str, Any],
    canonical_sha256: str,
    markdown_sha256: str,
) -> dict[str, Any]:
    """Manifest binds every artifact hash to the run and its technical verdict."""
    pages = canonical["pages"]
    return {
        "schema_version": MANIFEST_SCHEMA,
        "run_id": canonical["identity"]["run_id"],
        "generation": canonical["identity"]["generation"],
        "identity": canonical["identity"],
        "processing": canonical["processing"],
        "artifacts": artifacts,
        "checks": {
            "pages_expected": len(pages),
            "pages_completed": sum(1 for page in pages if page["status"] == "completed"),
            "pages_blank": sum(1 for page in pages if page["status"] == "blank"),
            "pages_failed": sum(1 for page in pages if page["status"] == "failed"),
            "pages_uncertain": sum(1 for page in pages if page["status"] == "uncertain"),
            "images_failed": sum(len(page.get("image_ocr_failures", ())) for page in pages),
            "page_image_sha256": {
                str(page["page_number"]): page["image"]["sha256"] for page in pages
            },
            "canonical_sha256": canonical_sha256,
            "markdown_sha256": markdown_sha256,
        },
        "validation": validation,
    }
