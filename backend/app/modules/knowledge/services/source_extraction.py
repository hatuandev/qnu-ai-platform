"""Shared snapshot extraction: native geometry, selective OCR and Office preview."""

from __future__ import annotations

import asyncio
import hashlib
import math
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

import pymupdf
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.storage import storage_service
from app.modules.knowledge.parsers import get_document_parser
from app.modules.knowledge.parsers.base import ParsedContent
from app.modules.knowledge.services.layout_text import reconstruct_layout_text
from app.modules.knowledge.services.source_pages import canonical_pages
from app.modules.ocr.service import OCRService

EXTRACTION_VERSION = "layout-v3"


@dataclass
class SourceExtraction:
    raw_text: str
    page_count: int
    pages: list[dict[str, Any]] = field(default_factory=list)
    tables: list[Any] = field(default_factory=list)
    engine_used: str = "native"
    preview_pdf: bytes | None = None


def normalize_layout_block(block: dict[str, Any], page: int, index: int) -> dict[str, Any]:
    """Adapters already provide percentages; do not guess units or confidence."""
    result = dict(block)
    coordinates = dict(block.get("coordinates") or {})
    if "x" in coordinates:
        coordinates["left"] = coordinates.pop("x")
    if "y" in coordinates:
        coordinates["top"] = coordinates.pop("y")
    valid = all(isinstance(coordinates.get(key), (int, float)) and math.isfinite(coordinates[key])
                for key in ("left", "top", "width", "height"))
    if not valid:
        coordinates = {}
    coordinates.update(is_valid=valid and coordinates.get("is_valid", True)
                       and coordinates.get("width", 0) > 0 and coordinates.get("height", 0) > 0,
                       coordinate_system="normalized_percent")
    result.update(id=f"page_{page}_block_{index}", coordinates=coordinates,
                  text=block.get("text") or block.get("content_snippet") or "")
    return result


def build_native_pages(content: bytes, parsed: ParsedContent) -> tuple[list[dict[str, Any]], list[int], bytes]:
    """Use actual page content, not document-wide emptiness, to route scan pages."""
    texts = {p["page_number"]: p["markdown_content"] for p in canonical_pages(parsed.raw_text, parsed.page_count)}
    records, selected = [], []
    with pymupdf.open(stream=content, filetype="pdf") as document, pymupdf.open() as scan:
        for index, page in enumerate(document):
            number = index + 1
            text = page.get_text().strip()
            image_area = sum((pymupdf.Rect(b["bbox"]) & page.rect).get_area() for b in page.get_image_info())
            image_coverage = image_area / max(page.rect.get_area(), 1)
            broken = text.count("\ufffd") / max(len(text), 1) > 0.01
            encoding_issue = bool(parsed.metadata.get("has_encoding_issues")) and number in parsed.metadata.get("pages_needing_ocr", [])
            needs_ocr = (broken or (image_coverage > 0.5 and len(text) < 80)
                         or encoding_issue or (not text and (image_area > 0 or len(page.get_drawings()) > 50)))
            blocks = [normalize_layout_block(b, number, i) for i, b in enumerate(parsed.blocks or [])
                      if b.get("page_number") == number]
            glyph_blocks = page.get_text("rawdict", flags=pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_IMAGES)["blocks"]
            for block in blocks:
                coords = block["coordinates"]
                if coords["is_valid"] and block.get("type") != "table":
                    left, top = coords["left"] / 100 * page.rect.width, coords["top"] / 100 * page.rect.height
                    clip = (left, top, left + coords["width"] / 100 * page.rect.width,
                            top + coords["height"] / 100 * page.rect.height)
                    block["text"] = reconstruct_layout_text(glyph_blocks, clip) or block["text"]
            records.append({"page_number": number, "extracted_text": texts.get(number, ""),
                            "alignment_text": reconstruct_layout_text(glyph_blocks),
                            "dimensions": {"width": page.rect.width, "height": page.rect.height},
                            "blocks": blocks, "has_tables": any(b.get("type") == "table" for b in blocks),
                            "engine_used": "native"})
            if needs_ocr:
                selected.append(number)
                scan.insert_pdf(document, from_page=index, to_page=index)
        scan_bytes = scan.tobytes() if selected else b""
    return records, selected, scan_bytes


async def extract_pdf(db: AsyncSession, content: bytes, filename: str, profile: str,
                      engine: str | None, tenant_id: str) -> SourceExtraction:
    parsed = await get_document_parser("pdf").parse(content, filename)
    pages, selected, scan_bytes = await asyncio.to_thread(build_native_pages, content, parsed)
    explicit = engine and engine not in {"auto", "native", "pymupdf_ocr"}
    if profile == "layout_analysis" or explicit:
        selected, scan_bytes = list(range(1, len(pages) + 1)), content
    if selected:
        response = await OCRService().extract_document(session=db, content=scan_bytes, filename="selected.pdf",
                                                       engine_name=engine if explicit else "paddleocr", tenant_id=tenant_id)
        if len(response.pages) != len(selected) or not response.success:
            raise AppException("OCR không trả đủ các trang yêu cầu.", code="OCR_PAGE_COUNT_MISMATCH", status_code=422)
        by_number = {p.page_number: p for p in response.pages}
        for local, original in enumerate(selected, 1):
            if local not in by_number:
                raise AppException("OCR trả số trang không hợp lệ.", code="OCR_PAGE_COUNT_MISMATCH", status_code=422)
            record = by_number[local].model_dump()
            if not record["extracted_text"].strip():
                raise AppException(f"Không nhận dạng được trang {original}.", code="EMPTY_OCR_PAGE", status_code=422)
            record.update(page_number=original, engine_used=response.engine_used)
            record["blocks"] = [normalize_layout_block(b, original, i) for i, b in enumerate(record["blocks"])]
            pages[original - 1] = record
        engines = sorted({p["engine_used"] for p in pages})
        used = "+".join(engines)
    else:
        used = "native"
    raw_text = "\n\n".join(f"<!-- Trang {p['page_number']} -->\n{p['extracted_text']}" for p in pages)
    return SourceExtraction(raw_text, len(pages), pages, parsed.tables or [], used)


def align_office_markdown(markdown: str, pages: list[dict[str, Any]]) -> None:
    """Transfer only evidenced token boundaries; reject unrelated render output."""
    tokens = list(re.finditer(r"\w+", markdown))
    native_tokens, native_pages = [], []
    for page in pages:
        values = re.findall(r"\w+", page.get("alignment_text", page["extracted_text"]))
        native_tokens.extend(word.casefold() for word in values)
        native_pages.extend([page["page_number"]] * len(values))
    matcher = SequenceMatcher(None, [t.group().casefold() for t in tokens], native_tokens, autojunk=False)
    matches = matcher.get_matching_blocks()
    if not tokens or sum(m.size for m in matches) / len(tokens) < 0.9:
        raise AppException("Nội dung Docling không khớp bản PDF xem trước; cần kiểm tra font/chuyển đổi.",
                           code="DOCX_LAYOUT_ALIGNMENT_FAILED", status_code=422)
    originals = {p["page_number"]: p["extracted_text"] for p in pages}
    matched_pages: set[int] = set()
    starts = {1: 0}
    for match in matches:
        for offset in range(match.size):
            number = native_pages[match.b + offset]
            matched_pages.add(number)
            starts.setdefault(number, tokens[match.a + offset].start())
    ordered = sorted(starts.items())
    for index, (number, start) in enumerate(ordered):
        end = ordered[index + 1][1] if index + 1 < len(ordered) else len(markdown)
        pages[number - 1]["extracted_text"] = markdown[start:end].strip()
    for page in pages:
        if page.get("engine_used") != "native" and page["page_number"] not in matched_pages:
            page["extracted_text"] = originals[page["page_number"]]
        if page["page_number"] not in starts and page.get("engine_used") == "native":
            page["extracted_text"] = ""


async def extract_source(db: AsyncSession, content: bytes, filename: str, file_type: str,
                         profile: str, engine: str | None, tenant_id: str) -> SourceExtraction:
    extension = file_type.lower().lstrip(".")
    if content.startswith(b"%PDF") or extension == "pdf":
        return await extract_pdf(db, content, filename, profile, engine, tenant_id)
    if extension == "docx":
        from app.modules.knowledge.services.ingestion_service import IngestionService

        parsed = await get_document_parser(extension).parse(content, filename)
        parsed.raw_text = unicodedata.normalize("NFC", parsed.raw_text)
        preview = await IngestionService()._convert_office_to_pdf(content, filename)
        result = await extract_pdf(db, preview, "preview.pdf", profile, engine, tenant_id)
        await asyncio.to_thread(align_office_markdown, parsed.raw_text, result.pages)
        result.raw_text = "\n\n".join(f"<!-- Trang {p['page_number']} -->\n{p['extracted_text']}" for p in result.pages)
        result.tables = parsed.tables or []
        result.engine_used = f"{parsed.metadata.get('parser', 'docling')}+{result.engine_used}"
        result.preview_pdf = preview
        return result
    if extension in {"png", "jpg", "jpeg", "webp", "bmp"}:
        response = await OCRService().extract_document(session=db, content=content, filename=filename,
                                                       engine_name=engine if engine and engine != "auto" else "paddleocr",
                                                       tenant_id=tenant_id)
        if not response.success or len(response.pages) != 1:
            raise AppException("OCR không trả trang ảnh hợp lệ.", code="OCR_PAGE_COUNT_MISMATCH", status_code=422)
        pages = [p.model_dump() for p in response.pages]
        for page in pages:
            page["blocks"] = [normalize_layout_block(b, page["page_number"], i) for i, b in enumerate(page["blocks"])]
        return SourceExtraction(response.raw_text, response.total_pages, pages, engine_used=response.engine_used)
    parsed = await get_document_parser(extension).parse(content, filename)
    return SourceExtraction(parsed.raw_text, parsed.page_count, tables=parsed.tables or [])


async def save_source_preview(snapshot_path: str, result: SourceExtraction) -> str | None:
    if result.preview_pdf:
        path = snapshot_path + "." + hashlib.sha256(result.preview_pdf).hexdigest() + ".preview.pdf"
        await storage_service.save(path, result.preview_pdf)
        return path
    return None
