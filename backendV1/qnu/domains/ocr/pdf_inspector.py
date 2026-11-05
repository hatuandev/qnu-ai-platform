"""PDF Inspector supplies text. Measured PDF regions anchor it to source evidence."""

import asyncio
from dataclasses import replace

import pdf_inspector
import pymupdf

from qnu.domains.ocr.artifacts.render import RenderedDocument, _render_lock
from qnu.domains.ocr.native import NativePlan, _page, _usable
from qnu.platform.errors import AppException


def _geometry(page):
    raw = page.get_text("dict", sort=True)
    tables = page.find_tables(strategy="lines_strict").tables
    # The Inspector assigns overlapping text to the first matching region.
    # Table cells must claim their text before line boxes or whole-table boxes.
    regions = dict.fromkeys(
        tuple(cell) for table in tables for row in table.rows for cell in row.cells if cell
    )
    regions.update(
        dict.fromkeys(
            tuple(line["bbox"]) for block in raw["blocks"] for line in block.get("lines", ())
        )
    )
    return (raw, tables), list(regions)


def extract_pdf(payload: bytes, rendered: RenderedDocument) -> NativePlan:
    report = pdf_inspector.extract_pages_markdown_bytes(payload)
    metadata = {page.page: page for page in report.pages}
    if metadata.keys() != set(range(len(rendered.pages))):
        raise AppException(
            "Kết quả PDF Inspector không khớp số trang nguồn.",
            code="pdf_inspector_page_mismatch",
            status_code=422,
        )
    with pymupdf.open(stream=payload, filetype="pdf") as document:
        geometry = {index: _geometry(page) for index, page in enumerate(document)}
        requested = [
            (index, [list(rect) for rect in regions])
            for index, (_, regions) in geometry.items()
            if regions and not metadata[index].needs_ocr and not document[index].rotation
        ]
        found = (
            {
                result.page: result.regions
                for result in pdf_inspector.extract_text_in_regions_bytes(payload, requested)
            }
            if requested
            else {}
        )
        if found.keys() != {index for index, _ in requested}:
            raise AppException(
                "PDF Inspector trả thiếu vùng nội dung.",
                code="pdf_inspector_regions_incomplete",
                status_code=422,
            )
        pages = []
        for index, page in enumerate(document):
            info = metadata[index]
            layout_geometry, regions = geometry[index]
            results = found.get(index)
            measured = dict(zip(regions, results, strict=True)) if results is not None else {}

            recovered_regions = 0
            needs_ocr = info.needs_ocr or bool(page.rotation)

            def region_text(rect, original, measured=measured, needs_ocr=needs_ocr):
                nonlocal recovered_regions
                if needs_ocr:
                    return ""
                value = measured.get(tuple(rect))
                text = value.text.strip() if value is not None else ""
                if "".join(text.split()) == "".join(original.split()):
                    return text
                if _usable(original):
                    recovered_regions += 1
                    return original
                return text if not original.strip() else original

            rendered_page = rendered.pages[index]
            native = _page(
                page,
                index + 1,
                rendered_page.blank,
                geometry=layout_geometry,
                read_region=region_text,
            )
            warnings = list(native.layout.warnings)
            if recovered_regions:
                warnings.append(f"pdf_inspector_native_regions_recovered:{recovered_regions}")
            rejected = info.needs_ocr or any(
                value.needs_ocr and not _usable(value.text)
                for value in measured.values()
                if value.text
            )
            if rejected and not rendered_page.blank:
                warnings.append("pdf_inspector_text_requires_ocr")
            if index + 1 in report.pages_with_tables and not native.layout.has_tables:
                warnings.append("pdf_inspector_table_geometry_unverified")
            pages.append(
                replace(
                    native,
                    layout=replace(native.layout, warnings=tuple(warnings)),
                    native_text=native.native_text and not rejected,
                    needs_ocr=not rendered_page.blank and (native.needs_ocr or rejected),
                    inspector_markdown=info.markdown,
                )
            )
    return NativePlan(tuple(pages), "source_revision")


async def extract_pdf_async(payload: bytes, rendered: RenderedDocument) -> NativePlan:
    try:
        async with _render_lock:
            return await asyncio.to_thread(extract_pdf, payload, rendered)
    except (RuntimeError, ValueError) as exc:
        raise AppException(
            "PDF Inspector không đọc được tài liệu.", code="pdf_inspector_failed", status_code=422
        ) from exc
