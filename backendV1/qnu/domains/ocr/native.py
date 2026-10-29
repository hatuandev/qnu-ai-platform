"""Source-bound native PDF text and DOCX render text; image pages retain OCR evidence.

DOCX page coordinates refer to the retained fixed-layout PDF, never Word pagination.
Native output is not a provider response. Image bytes and their measured positions
are retained independently; OCR output can supplement images without replacing text.
"""

import asyncio
import hashlib
import unicodedata
from dataclasses import asdict, dataclass, replace

import pymupdf

from qnu.domains.ocr.artifacts.render import RenderedDocument, _render_lock
from qnu.domains.ocr.layout import Block, Cell, PageLayout, Table
from qnu.domains.ocr.native_order import reading_order
from qnu.domains.ocr.native_tables import table_regions
from qnu.platform.errors import AppException

NATIVE_VERSION = "qnu-native/v1"


@dataclass(frozen=True)
class EmbeddedImage:
    asset_no: int
    payload: bytes
    descriptor: dict


@dataclass(frozen=True)
class NativePage:
    page_number: int
    layout: PageLayout
    images: tuple[EmbeddedImage, ...]
    needs_ocr: bool
    native_text: bool


@dataclass(frozen=True)
class NativePlan:
    pages: tuple[NativePage, ...]
    source_artifact: str


def _bbox(rect, bounds):
    clipped = pymupdf.Rect(rect) & bounds
    return (
        clipped.x0 / bounds.width,
        clipped.y0 / bounds.height,
        clipped.x1 / bounds.width,
        clipped.y1 / bounds.height,
    )


def _usable(text: str) -> bool:
    return bool(text.strip()) and not any(
        c == "\ufffd" or (unicodedata.category(c).startswith("C") and c not in "\n\r\t")
        for c in text
    )


def _ordered(blocks, warnings=()):
    return PageLayout(
        tuple(replace(b, order=i) for i, b in enumerate(reading_order(blocks), 1)),
        tuple(warnings),
    )


def _page(page, number, blank):
    bounds = page.rect
    raw = page.get_text("dict", sort=True)
    blocks, images, warnings = [], [], []
    tables = table_regions(page)
    for rect, table in tables:
        text = "\n".join(" | ".join(c.text for c in row) for row in table.rows)
        if table.status != "parsed":
            text = page.get_text("text", clip=rect)
        blocks.append(
            Block(
                0,
                "Table",
                "table",
                text,
                _bbox(rect, bounds),
                table.status != "parsed",
                table,
                origin="native",
            )
        )
    for item in raw["blocks"]:
        rect = pymupdf.Rect(item["bbox"]) & bounds
        if rect.is_empty:
            continue
        if item["type"] == 1:
            if len(images) >= 2048:
                raise AppException(
                    "Trang có quá nhiều ảnh nhúng.", code="native_too_many_images", status_code=422
                )
            asset_no = number * 10000 + len(images) + 1
            payload = item["image"]
            extension = item.get("ext", "bin")
            if extension not in {"png", "jpeg", "jpg", "gif", "bmp", "tiff", "jpx"}:
                extension = "bin"
            descriptor = {
                "asset_no": asset_no,
                "filename": f"images/{asset_no}.{extension}",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "content_type": "image/jpeg"
                if extension in {"jpg", "jpeg"}
                else f"image/{extension}"
                if extension != "bin"
                else "application/octet-stream",
                "width": item["width"],
                "height": item["height"],
            }
            images.append(EmbeddedImage(asset_no, payload, descriptor))
            blocks.append(
                Block(
                    0,
                    "Picture",
                    "figure",
                    "",
                    _bbox(rect, bounds),
                    True,
                    origin="native",
                    image=descriptor,
                )
            )
            continue
        for line in item.get("lines", []):
            spans = [
                s
                for s in line["spans"]
                if not any(
                    t.contains(
                        pymupdf.Point(
                            (s["bbox"][0] + s["bbox"][2]) / 2, (s["bbox"][1] + s["bbox"][3]) / 2
                        )
                    )
                    for t, _ in tables
                )
            ]
            if not spans:
                continue
            text = "".join(s["text"] for s in spans)
            if text.strip():
                blocks.append(
                    Block(
                        0, "Text", "text", text, _bbox(line["bbox"], bounds), False, origin="native"
                    )
                )
    native_text = any(b.text.strip() for b in blocks)
    usable = native_text and all(_usable(b.text) for b in blocks if b.text.strip())
    if page.rotation:
        usable = False
        warnings.append("native_rotated_page_requires_ocr")
    if native_text and not usable:
        warnings.append("native_text_unusable_requires_ocr")
    if usable and any(
        b.text.strip()
        and (pymupdf.Rect(b.bbox) & pymupdf.Rect(image.bbox)).get_area()
        >= pymupdf.Rect(b.bbox).get_area() * 0.5
        for b in blocks
        for image in blocks
        if image.image
    ):
        # A scan's hidden text layer or overlapping text/graphics cannot be merged
        # by concatenation. Preserve native evidence but use one OCR page layout.
        usable = False
        warnings.append("native_image_text_overlap_requires_ocr")
    return NativePage(
        number,
        _ordered(blocks, warnings),
        tuple(images),
        not blank and (not usable or bool(images)),
        usable,
    )


def extract_native(payload: bytes, rendered: RenderedDocument) -> NativePlan:
    if any(w.startswith("docx_image_skipped:") for w in rendered.warnings):
        raise AppException(
            "DOCX có ảnh chưa được bộ đọc hỗ trợ; hãy cung cấp PDF giữ đầy đủ nội dung.",
            code="docx_image_unsupported",
            status_code=422,
        )
    data = rendered.fixed_layout_pdf if rendered.extension == ".docx" else payload
    with pymupdf.open(stream=data, filetype="pdf") as document:
        pages = tuple(
            _page(page, i, rendered.pages[i - 1].blank) for i, page in enumerate(document, 1)
        )
    if rendered.extension == ".docx":
        from qnu.domains.ocr.native_docx import restore_source_tables

        pages = restore_source_tables(payload, pages)
    return NativePlan(pages, "render_pdf" if rendered.extension == ".docx" else "source_revision")


async def extract_native_async(payload: bytes, rendered: RenderedDocument) -> NativePlan:
    async with _render_lock:
        return await asyncio.to_thread(extract_native, payload, rendered)


def page_payload(page: NativePage, source_artifact: str) -> dict:
    return {
        "schema_version": NATIVE_VERSION,
        "source_artifact": source_artifact,
        "page_number": page.page_number,
        "needs_ocr": page.needs_ocr,
        "native_text": page.native_text,
        "warnings": list(page.layout.warnings),
        "blocks": [asdict(b) for b in page.layout.blocks],
    }


def page_from_payload(payload: dict) -> NativePage:
    if payload.get("schema_version") != NATIVE_VERSION:
        raise AppException(
            "Phiên bản bóc tách không tương thích.", code="native_version_changed", status_code=409
        )
    blocks = []
    for item in payload["blocks"]:
        record = dict(item)
        record["bbox"] = tuple(record["bbox"])
        if table := record.get("table"):
            record["table"] = Table(
                table["status"],
                tuple(tuple(Cell(**c) for c in row) for row in table["rows"]),
                table["column_count"],
                table["reason"],
            )
        blocks.append(Block(**record))
    return NativePage(
        payload["page_number"],
        PageLayout(tuple(blocks), tuple(payload["warnings"])),
        (),
        payload["needs_ocr"],
        payload["native_text"],
    )


def merge_layout(native: NativePage, ocr: PageLayout | None) -> PageLayout:
    images = [b for b in native.layout.blocks if b.image]
    if not native.native_text:
        return _ordered(images + list(ocr.blocks if ocr else ()), native.layout.warnings)
    extra = []
    for block in ocr.blocks if ocr else ():
        rect = pymupdf.Rect(block.bbox)
        # Most of a supplementary OCR block must lie inside an embedded picture.
        if any(
            (rect & pymupdf.Rect(image.bbox)).get_area() >= rect.get_area() * 0.5
            for image in images
        ):
            extra.append(block)
    return _ordered(list(native.layout.blocks) + extra, native.layout.warnings)
