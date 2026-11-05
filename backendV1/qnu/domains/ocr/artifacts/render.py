"""Render PDF/DOCX into fixed-layout page images, with measured hashes.

PDF pages are rasterised directly. DOCX uses its pinned converter to produce a
fixed-layout PDF; that intermediate artifact is what the OCR actually saw.

MuPDF is not thread-safe: every call is serialised behind one lock, and the blocking
work runs in a worker thread so the event loop stays free.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
from dataclasses import dataclass, field

import httpx
import pymupdf

from qnu.domains.ocr.artifacts.docx_html import convert_docx_to_html
from qnu.domains.ocr.config import ProcessingConfig
from qnu.platform.errors import AppException, DependencyUnavailable
from qnu.platform.logging import get_logger

logger = get_logger(__name__)

PAGE_MEDIA = "a4"
PAGE_MARGIN = 36
# A page is blank only when it carries (almost) no dark pixel at all. Counting a
# fixed *ratio* would wrongly discard title-only pages, where one short line is a
# tiny fraction of an A4 sheet; the absolute dark-pixel count is the honest signal.
INK_PIXEL_MAX = 210
BLANK_MIN_INK_PIXELS = 24
INK_SAMPLE_ROWS = 400

STYLE_CSS = """
body { font-family: sans-serif; font-size: 11pt; line-height: 1.35; }
h1 { font-size: 16pt; } h2 { font-size: 14pt; } h3 { font-size: 12pt; }
h1, h2, h3, h4 { margin: 8pt 0 4pt 0; }
p { margin: 0 0 4pt 0; }
table.docx { border-collapse: collapse; width: 100%; margin: 6pt 0; }
table.docx td, table.docx th { border: 1px solid #555; padding: 3pt 4pt; vertical-align: top; }
table.docx th { background-color: #eeeeee; font-weight: bold; }
.footnotes { font-size: 9pt; margin-top: 12pt; }
sup.fn { font-size: 7pt; }
img.docx-image { max-width: 100%; }
"""

_render_lock = asyncio.Lock()


@dataclass(frozen=True, slots=True)
class PageImage:
    page_number: int
    png: bytes | None
    width: int | None
    height: int | None
    sha256: str | None
    blank: bool
    ink_ratio: float | None


@dataclass(frozen=True, slots=True)
class RenderedDocument:
    extension: str
    renderer: dict
    pages: tuple[PageImage, ...]
    fixed_layout_pdf: bytes | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)


def _content_error(detail: str, code: str) -> AppException:
    return AppException(detail, code=code, status_code=422, title="Tài liệu không xử lý được")


def ink_stats(pixmap: pymupdf.Pixmap) -> tuple[float, int]:
    """Measure ink density as (ratio, dark_pixels) over whole sampled rows.

    Whole rows are scanned rather than strided single pixels: a strided sample can
    step over a thin glyph stroke and make a page with text look empty. Sampling
    rows keeps the cost bounded while never missing ink horizontally.
    """
    height, width, channels = pixmap.height, pixmap.width, pixmap.n
    if not height or not width:
        return 0.0, 0
    row_bytes = width * channels
    step = max(1, height // INK_SAMPLE_ROWS)
    samples = pixmap.samples
    dark = 0
    seen = 0
    for row in range(0, height, step):
        offset = row * row_bytes
        for column in range(0, row_bytes, channels):
            base = offset + column
            if (
                samples[base] < INK_PIXEL_MAX
                or (channels > 1 and samples[base + 1] < INK_PIXEL_MAX)
                or (channels > 2 and samples[base + 2] < INK_PIXEL_MAX)
            ):
                dark += 1
            seen += 1
    return (dark / seen if seen else 0.0), dark


def ink_ratio(pixmap: pymupdf.Pixmap) -> float:
    """Fraction of sampled pixels that carry ink; measured, never assumed."""
    return ink_stats(pixmap)[0]


def _rasterise(document: pymupdf.Document, config: ProcessingConfig) -> list[PageImage]:
    pages: list[PageImage] = []
    for index, page in enumerate(document, 1):
        pixmap = page.get_pixmap(dpi=config.dpi, alpha=False)
        png = pixmap.tobytes("png")
        if len(png) > config.max_page_bytes:
            raise _content_error(
                f"Ảnh trang {index} vượt giới hạn {config.max_page_bytes} byte.",
                "page_image_too_large",
            )
        ratio, dark = ink_stats(pixmap)
        pages.append(
            PageImage(
                page_number=index,
                png=png,
                width=pixmap.width,
                height=pixmap.height,
                sha256=hashlib.sha256(png).hexdigest(),
                blank=dark < BLANK_MIN_INK_PIXELS,
                ink_ratio=round(ratio, 6),
            )
        )
    return pages


def _open_pdf(payload: bytes, config: ProcessingConfig) -> pymupdf.Document:
    try:
        document = pymupdf.open(stream=payload, filetype="pdf")
    except Exception as exc:
        raise _content_error("Tệp PDF không mở được.", "pdf_invalid") from exc
    if document.needs_pass or document.is_encrypted:
        raise _content_error("PDF được bảo vệ bằng mật khẩu.", "pdf_encrypted")
    if document.page_count == 0:
        raise _content_error("PDF không có trang nào.", "pdf_no_pages")
    if document.page_count > config.max_pages:
        raise _content_error(
            f"Tài liệu có {document.page_count} trang, vượt giới hạn {config.max_pages}.",
            "document_too_many_pages",
        )
    return document


def _docx_to_pdf_gotenberg(
    payload: bytes, config: ProcessingConfig
) -> tuple[bytes, dict, list[str]]:
    """Convert DOCX to PDF via Gotenberg LibreOffice endpoint in Docker."""
    if not config.gotenberg_url:
        raise AppException(
            "Lượt xử lý thiếu endpoint Gotenberg đã ghim.",
            code="processing_config_invalid",
            status_code=409,
        )
    target_url = f"{config.gotenberg_url.rstrip('/')}/forms/libreoffice/convert"
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                target_url,
                files={"files": ("document.docx", payload)},
            )
            if resp.status_code == 200 and resp.content.startswith(b"%PDF-"):
                pdf_bytes = resp.content
                stats = {
                    "converter": "gotenberg-libreoffice",
                    "revision": config.renderer_revision,
                    "bytes": len(pdf_bytes),
                }
                return pdf_bytes, stats, []
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("docx_converter_unavailable", error_type=type(exc).__name__)
        raise DependencyUnavailable(
            "Không kết nối được Gotenberg đã chọn; không tự đổi bộ chuyển đổi.",
            code="docx_converter_unavailable",
        ) from None
    logger.warning("docx_conversion_failed", status_code=resp.status_code)
    raise DependencyUnavailable(
        "Gotenberg không trả về PDF hợp lệ; chưa tạo kết quả chuyển đổi.",
        code="docx_conversion_failed",
    )


def _docx_to_pdf(payload: bytes, config: ProcessingConfig) -> tuple[bytes, dict, list[str]]:
    if config.docx_converter == "gotenberg-libreoffice":
        return _docx_to_pdf_gotenberg(payload, config)
    if config.docx_converter != "docx-story":
        raise AppException(
            "Bộ chuyển đổi đã ghim không được hỗ trợ.",
            code="processing_config_invalid",
            status_code=409,
        )

    conversion = convert_docx_to_html(payload)
    buffer = io.BytesIO()
    story = pymupdf.Story(html=conversion.html, user_css=STYLE_CSS)
    media_box = pymupdf.paper_rect(PAGE_MEDIA)
    where = media_box + (PAGE_MARGIN, PAGE_MARGIN, -PAGE_MARGIN, -PAGE_MARGIN)
    writer = pymupdf.DocumentWriter(buffer)
    more = 1
    pages = 0
    try:
        while more:
            device = writer.begin_page(media_box)
            more, _ = story.place(where)
            story.draw(device)
            writer.end_page()
            pages += 1
            if pages > config.max_pages:
                raise _content_error(
                    f"Tài liệu vượt giới hạn {config.max_pages} trang sau khi dàn trang.",
                    "document_too_many_pages",
                )
    except AppException:
        raise
    except Exception as exc:
        raise _content_error("Không dàn trang được DOCX.", "docx_render_failed") from exc
    finally:
        writer.close()

    stats = {
        "converter": "docx-story",
        "paragraphs": conversion.paragraphs,
        "tables": conversion.tables,
        "table_rows": conversion.table_rows,
        "footnotes": conversion.footnotes,
        "images": conversion.images,
        "skipped_images": conversion.skipped_images,
        "pages": pages,
    }
    return buffer.getvalue(), stats, list(conversion.warnings)


def render_document(payload: bytes, extension: str, config: ProcessingConfig) -> RenderedDocument:
    """Blocking render; callers run this in a thread through :func:`render_async`."""
    suffix = extension.lower()
    if suffix == ".pdf":
        document = _open_pdf(payload, config)
        try:
            pages = _rasterise(document, config)
        finally:
            document.close()
        return RenderedDocument(
            extension=suffix,
            renderer={
                "name": "pymupdf",
                "version": pymupdf.version[0],
                "dpi": config.dpi,
                "converter": "pdf-direct",
            },
            pages=tuple(pages),
        )

    if suffix == ".docx":
        pdf_bytes, stats, warnings = _docx_to_pdf(payload, config)
        return _render_converted_docx(pdf_bytes, stats, warnings, config)

    raise AppException(
        f"Định dạng '{suffix or 'không rõ'}' chưa được hỗ trợ xử lý OCR.",
        code="processing_unsupported_format",
        status_code=415,
        title="Định dạng chưa hỗ trợ xử lý",
    )


def _render_converted_docx(
    pdf_bytes: bytes, stats: dict, warnings: list[str], config: ProcessingConfig
) -> RenderedDocument:
    document = _open_pdf(pdf_bytes, config)
    try:
        pages = _rasterise(document, config)
    finally:
        document.close()
    gotenberg = stats.get("converter") == "gotenberg-libreoffice"
    return RenderedDocument(
        extension=".docx",
        renderer={
            "name": "gotenberg" if gotenberg else "pymupdf",
            "version": None if gotenberg else pymupdf.version[0],
            "revision": config.renderer_revision,
            "rasterizer_version": pymupdf.version[0],
            "dpi": config.dpi,
            "converter": stats.get("converter", "docx-story"),
            "conversion": stats,
        },
        pages=tuple(pages),
        fixed_layout_pdf=pdf_bytes,
        warnings=tuple(warnings),
    )


def render_saved_pdf(
    payload: bytes, config: ProcessingConfig, renderer: dict, warnings: tuple[str, ...]
) -> RenderedDocument:
    """Rasterise the immutable DOCX conversion artifact without calling its converter."""
    _check_renderer_version(config)
    document = _open_pdf(payload, config)
    try:
        pages = _rasterise(document, config)
    finally:
        document.close()
    return RenderedDocument(
        extension=".docx",
        renderer=renderer,
        pages=tuple(pages),
        fixed_layout_pdf=payload,
        warnings=warnings,
    )


async def render_saved_pdf_async(
    payload: bytes, config: ProcessingConfig, renderer: dict, warnings: tuple[str, ...]
) -> RenderedDocument:
    async with _render_lock:
        return await asyncio.to_thread(render_saved_pdf, payload, config, renderer, warnings)


async def render_async(
    payload: bytes, extension: str, config: ProcessingConfig
) -> RenderedDocument:
    """Wait for external conversion outside the lock reserved for MuPDF work."""
    _check_renderer_version(config)
    if extension.lower() == ".docx" and config.docx_converter == "gotenberg-libreoffice":
        pdf, stats, warnings = await asyncio.to_thread(_docx_to_pdf_gotenberg, payload, config)
        async with _render_lock:
            return await asyncio.to_thread(_render_converted_docx, pdf, stats, warnings, config)
    async with _render_lock:
        return await asyncio.to_thread(render_document, payload, extension, config)


def _check_renderer_version(config: ProcessingConfig) -> None:
    if config.pymupdf_version is not None and config.pymupdf_version != pymupdf.version[0]:
        raise AppException(
            "Bộ kết xuất trang đã thay đổi; cần tạo lượt xử lý mới.",
            code="renderer_version_changed",
            status_code=409,
        )
