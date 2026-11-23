"""Extract source-bound PowerPoint text, tables and speaker notes by slide."""

import asyncio
from importlib.metadata import version
from io import BytesIO
from zipfile import BadZipFile, ZipFile

from lxml.etree import XMLSyntaxError
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.exc import PackageNotFoundError
from pptx.shapes.picture import Picture

from qnu.domains.ocr.artifacts.render import PageImage, RenderedDocument
from qnu.domains.ocr.layout import MAX_TABLE_COLUMNS, MAX_TABLE_ROWS, Block, Cell, PageLayout, Table
from qnu.domains.ocr.native import NativePage, NativePlan
from qnu.platform.errors import AppException

MAX_EXPANDED_BYTES = 256 * 1024 * 1024
_GRAPHICAL_SHAPES = {
    MSO_SHAPE_TYPE.PICTURE,
    MSO_SHAPE_TYPE.LINKED_PICTURE,
    MSO_SHAPE_TYPE.CHART,
    MSO_SHAPE_TYPE.DIAGRAM,
    MSO_SHAPE_TYPE.IGX_GRAPHIC,
    MSO_SHAPE_TYPE.EMBEDDED_OLE_OBJECT,
    MSO_SHAPE_TYPE.LINKED_OLE_OBJECT,
    MSO_SHAPE_TYPE.MEDIA,
    MSO_SHAPE_TYPE.FREEFORM,
}


def _clean_text(value: str) -> str:
    return value.replace("\v", "\n").strip()


def _table_block(order: int, table, locator: dict) -> Block:
    width = len(table.columns)
    if width > MAX_TABLE_COLUMNS or len(table.rows) > MAX_TABLE_ROWS:
        raise AppException(
            "Bảng trong PowerPoint vượt giới hạn hàng hoặc cột.",
            code="pptx_table_too_large",
            status_code=422,
        )
    rows = tuple(
        tuple(
            Cell(
                _clean_text(cell.text),
                cell.span_height,
                cell.span_width,
                table.first_row and i == 0,
            )
            for cell in row.cells
            if not cell.is_spanned
        )
        for i, row in enumerate(table.rows)
    )
    text = "\n".join(" | ".join(cell.text for cell in row) for row in rows)
    return Block(
        order,
        "Table",
        "table",
        text,
        None,
        False,
        table=Table("parsed", rows, width, source_mapping=dict(locator)),
        origin="native",
        source_locator=locator,
    )


def _shape_blocks(shape, title_id: int | None, locator: dict, blocks: list[Block]) -> None:
    if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
        for child in shape.shapes:
            _shape_blocks(child, title_id, locator, blocks)
        return
    order = len(blocks) + 1
    source = {**locator, "shape_id": shape.shape_id}
    if shape.has_table:
        blocks.append(_table_block(order, shape.table, source))
    elif shape.has_text_frame and (text := _clean_text(shape.text)):
        is_title = shape.shape_id == title_id
        if is_title:
            source["level"] = 1
        blocks.append(
            Block(
                order,
                "Title" if is_title else "Text",
                "title" if is_title else "text",
                text,
                None,
                False,
                origin="native",
                source_locator=source,
            )
        )
    elif shape.has_chart or isinstance(shape, Picture) or shape.shape_type in _GRAPHICAL_SHAPES:
        blocks.append(
            Block(order, "Figure", "figure", "", None, True, origin="native", source_locator=source)
        )


def _slide_layout(slide, number: int) -> PageLayout:
    source = {"format": "pptx", "slide": number}
    title = slide.shapes.title
    title_id = None if title is None else title.shape_id
    blocks: list[Block] = []
    if title is not None:
        _shape_blocks(title, title_id, source, blocks)
    for shape in slide.shapes:
        if shape.shape_id != title_id:
            _shape_blocks(shape, title_id, source, blocks)
    if slide.has_notes_slide:
        notes = slide.notes_slide.notes_placeholder
        if notes is not None and (text := _clean_text(notes.text)):
            blocks.append(
                Block(
                    len(blocks) + 1,
                    "Speaker notes",
                    "text",
                    text,
                    None,
                    False,
                    origin="native",
                    source_locator={**source, "part": "notes", "shape_id": notes.shape_id},
                )
            )
    warnings = ()
    if any(block.requires_review for block in blocks):
        if not any(block.text for block in blocks):
            raise AppException(
                f"Slide {number} chỉ có nội dung hình ảnh chưa bóc tách được.",
                code="pptx_slide_requires_review",
                status_code=422,
            )
        warnings = ("pptx_graphic_requires_review",)
    return PageLayout(tuple(blocks), warnings)


def extract_pptx(payload: bytes, max_pages: int) -> tuple[RenderedDocument, NativePlan]:
    try:
        with ZipFile(BytesIO(payload)) as archive:
            if sum(entry.file_size for entry in archive.infolist()) > MAX_EXPANDED_BYTES:
                raise AppException(
                    "Tệp PowerPoint vượt giới hạn dung lượng sau giải nén.",
                    code="pptx_expanded_too_large",
                    status_code=422,
                )
        deck = Presentation(BytesIO(payload))
        if len(deck.slides) > max_pages:
            raise AppException(
                f"Tệp PowerPoint vượt giới hạn {max_pages} slide.",
                code="pptx_too_many_slides",
                status_code=422,
            )
        layouts = [_slide_layout(slide, i) for i, slide in enumerate(deck.slides, 1)]
    except (BadZipFile, PackageNotFoundError, XMLSyntaxError, KeyError, ValueError) as exc:
        raise AppException(
            "Không đọc được tệp PowerPoint.", code="pptx_invalid", status_code=422
        ) from exc
    if not any(layout.text for layout in layouts):
        raise AppException(
            "Tệp PowerPoint không có nội dung đọc được.", code="pptx_empty", status_code=422
        )
    pages = tuple(
        NativePage(i, layout, (), False, bool(layout.text)) for i, layout in enumerate(layouts, 1)
    )
    rendered = RenderedDocument(
        extension=".pptx",
        renderer={"name": "python-pptx", "version": version("python-pptx"), "pagination": "slides"},
        pages=tuple(
            PageImage(i, None, None, None, None, not layout.text, None)
            for i, layout in enumerate(layouts, 1)
        ),
    )
    return rendered, NativePlan(pages, "source_revision")


async def extract_pptx_async(payload: bytes, max_pages: int) -> tuple[RenderedDocument, NativePlan]:
    return await asyncio.to_thread(extract_pptx, payload, max_pages)
