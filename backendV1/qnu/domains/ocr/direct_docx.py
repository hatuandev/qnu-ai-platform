"""Project a Docling Word document into the shared evidence format."""

import asyncio
import hashlib
import re
from dataclasses import replace
from importlib.metadata import version
from pathlib import PurePosixPath

from docling_core.types.doc import (
    ContentLayer,
    PictureItem,
    SectionHeaderItem,
    TableData,
    TableItem,
    TextItem,
)
from docx.table import _Cell

from qnu.domains.ocr.artifacts.render import PageImage, RenderedDocument
from qnu.domains.ocr.layout import MAX_TABLE_COLUMNS, MAX_TABLE_ROWS, Block, Cell, PageLayout, Table
from qnu.domains.ocr.native import EmbeddedImage, NativePage, NativePlan
from qnu.platform.errors import AppException

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _source_cells(source) -> dict:
    if source is None:
        return {}
    rows = {}
    for row_no, row in enumerate(source.findall(W + "tr")):
        before = row.find(f"{W}trPr/{W}gridBefore")
        column = int(before.get(W + "val", "0")) if before is not None else 0
        for cell in row.findall(W + "tc"):
            rows[row_no, column] = cell
            column += cell.grid_span
    return rows


def _cell_text(cell, source_cell, backend) -> str:
    if source_cell is None or not any(
        element.tag in {W + "fldSimple", W + "instrText"} for element in source_cell.iter()
    ):
        return cell.text
    # Docling's table shortcut uses python-docx Cell.text, which can skip
    # field wrappers. The paragraph reader includes the cached visible runs.
    word_cell = _Cell(source_cell, backend.docx_obj)
    return "\n".join(
        backend._get_paragraph_text(paragraph)
        for paragraph in word_cell.paragraphs
        if not backend._is_hidden_paragraph(paragraph)
    )


def _table(data: TableData, source, backend) -> Table:
    if not (0 < data.num_rows <= MAX_TABLE_ROWS and 0 < data.num_cols <= MAX_TABLE_COLUMNS):
        return Table("unsupported", reason="docx_table_size")
    header_rows = set()
    if source is not None:
        for i, row in enumerate(source.findall(W + "tr")):
            header = row.find(f"{W}trPr/{W}tblHeader")
            if header is not None and header.get(W + "val", "true") not in {"0", "false", "off"}:
                header_rows.add(i)
    cells = {}
    occupied = set()
    source_cells = _source_cells(source)
    for cell in data.table_cells:
        row, col = cell.start_row_offset_idx, cell.start_col_offset_idx
        if not (
            0 <= row < row + cell.row_span <= data.num_rows
            and 0 <= col < col + cell.col_span <= data.num_cols
        ):
            return Table("unsupported", reason="docx_table_grid")
        slots = {
            (y, x) for y in range(row, row + cell.row_span) for x in range(col, col + cell.col_span)
        }
        if slots & occupied:
            return Table("unsupported", reason="docx_table_grid")
        occupied.update(slots)
        cells[row, col] = Cell(
            _cell_text(cell, source_cells.get((row, col)), backend),
            cell.row_span,
            cell.col_span,
            row in header_rows or cell.column_header or cell.row_header,
        )
    # The canonical grid uses a blank placeholder for each absent OOXML slot.
    # Record these separately from actual empty source cells.
    omitted = []
    rows = []
    for row in range(data.num_rows):
        values = []
        for col in range(data.num_cols):
            if (row, col) in cells:
                values.append(cells[row, col])
            elif (row, col) not in occupied:
                omitted.append([row, len(values), col])
                values.append(Cell(""))
        rows.append(tuple(values))
    return Table(
        "parsed",
        tuple(rows),
        data.num_cols,
        source_mapping={"basis": "docx_grid", "omitted_slots": omitted},
    )


def _image(order: int, source: tuple, item: PictureItem) -> EmbeddedImage:
    payload, mime, locator = source
    size = item.image.size
    suffix = PurePosixPath(locator["image_part"]).suffix.lower()
    if not re.fullmatch(r"\.[a-z]+", suffix):
        suffix = ".bin"
    asset = 10000 + order
    return EmbeddedImage(
        asset,
        payload,
        {
            "asset_no": asset,
            "filename": f"images/{asset}{suffix}",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "content_type": mime,
            "width": int(size.width),
            "height": int(size.height),
        },
    )


def _text_kind(item: TextItem, locator: dict) -> str:
    name = PurePosixPath(locator.get("part", "")).name
    if name.startswith(("header", "footer")):
        return "header" if name.startswith("header") else "footer"
    return {
        "section_header": "title",
        "title": "title",
        "footnote": "footnote",
        "caption": "caption",
        "formula": "formula",
    }.get(item.label.value, "text")


def _table_text(data: TableData) -> str:
    rows: dict[int, list[str]] = {}
    for cell in data.table_cells:
        rows.setdefault(cell.start_row_offset_idx, []).append(cell.text)
    return "\n".join(" | ".join(rows[row]) for row in sorted(rows))


def _table_block(
    order: int, data: TableData, source, locator: dict, backend, *, label="Table"
) -> Block:
    table = _table(data, source, backend)
    value = "\n".join(" | ".join(c.text for c in row) for row in table.rows)
    return Block(
        order,
        label,
        "table",
        value if table.status == "parsed" else _table_text(data),
        None,
        table.status != "parsed",
        table,
        origin="native",
        source_locator=locator,
    )


def extract_docx(payload: bytes) -> tuple[RenderedDocument, NativePlan]:
    from qnu.domains.ocr.docling_source import read_docling

    document, backend = read_docling(payload)
    blocks, images, warnings = [], [], []
    # Rich cells contain Docling child text used for formatting. Their cell text
    # is already present in the table. Keep child tables and pictures separately.
    for item, _ in document.iterate_items(
        included_content_layers={ContentLayer.BODY, ContentLayer.FURNITURE}
    ):
        locator = {
            "format": "docx",
            "docling_ref": item.self_ref,
            **backend.locators.get(item.self_ref, {}),
        }
        order = len(blocks) + 1
        if isinstance(item, TableItem):
            blocks.append(
                _table_block(
                    order, item.data, backend.table_sources.get(item.self_ref), locator, backend
                )
            )
        elif isinstance(item, PictureItem):
            source = backend.picture_sources.get(item.self_ref)
            chart = item.meta.tabular_chart if item.meta else None
            if chart:
                blocks.append(
                    _table_block(order, chart.chart_data, None, locator, backend, label="Chart")
                )
            elif source and item.image:
                if len(images) >= 2048:
                    raise AppException(
                        "DOCX có quá nhiều ảnh nhúng.",
                        code="native_too_many_images",
                        status_code=422,
                    )
                image = _image(len(images) + 1, source, item)
                images.append(image)
                blocks.append(
                    Block(
                        order,
                        "Picture",
                        "figure",
                        "",
                        None,
                        True,
                        origin="native",
                        image=image.descriptor,
                        source_locator={**locator, **source[2]},
                    )
                )
            else:
                warnings.append("docx_drawing_requires_review")
                blocks.append(
                    Block(
                        order,
                        "Picture",
                        "figure",
                        "",
                        None,
                        True,
                        origin="native",
                        source_locator=locator,
                    )
                )
        elif isinstance(item, TextItem) and item.text.strip():
            parent = item.parent.resolve(document) if item.parent else None
            while parent and not isinstance(parent, TableItem):
                parent = parent.parent.resolve(document) if parent.parent else None
            if parent is None:
                value = getattr(item, "marker", "") or ""
                if isinstance(item, SectionHeaderItem):
                    locator["level"] = item.level
                blocks.append(
                    Block(
                        order,
                        item.label.value,
                        _text_kind(item, locator),
                        f"{value} {item.text}" if value else item.text,
                        None,
                        False,
                        origin="native",
                        source_locator=locator,
                    )
                )
    if backend.unrendered_drawings:
        warnings.append("docx_drawing_requires_review")
    if not blocks:
        raise AppException("DOCX không có nội dung đọc được.", code="docx_empty", status_code=422)
    page = NativePage(
        1,
        PageLayout(tuple(blocks), tuple(dict.fromkeys(warnings))),
        tuple(images),
        bool(images),
        any(block.text.strip() for block in blocks),
    )
    rendered = RenderedDocument(
        ".docx",
        {"name": "docling", "version": version("docling-slim"), "pagination": "document"},
        (PageImage(1, None, None, None, None, False, None),),
    )
    return rendered, NativePlan((page,), "source_revision")


async def extract_docx_async(payload: bytes) -> tuple[RenderedDocument, NativePlan]:
    return await asyncio.to_thread(extract_docx, payload)


def merge_docx_layout(native: NativePage, ocr: PageLayout | None) -> PageLayout:
    blocks = []
    for block in native.layout.blocks:
        blocks.append(block)
        if block.image and ocr:
            blocks.extend(
                replace(child, source_locator=block.source_locator)
                for child in ocr.blocks
                if child.source_image_asset_no == block.image["asset_no"]
            )
    warnings = (*native.layout.warnings, *(ocr.warnings if ocr else ()))
    return PageLayout(
        tuple(replace(block, order=i) for i, block in enumerate(blocks, 1)),
        tuple(dict.fromkeys(warnings)),
    )
