"""Preserve evidenced page boundaries; never infer pagination from text length."""

from __future__ import annotations

import re
from typing import Any

from app.modules.knowledge.chunker import BaseChunker, ChunkDraft
from app.modules.knowledge.cleaner import clean_markdown_text

_PAGE_MARKER = re.compile(r"<!--\s*(?:Trang|Page)\s+(\d+)\s*-->", re.IGNORECASE)


def merge_edited_manifest(original: list[dict[str, Any]], edited: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Layout belongs to the binary snapshot, not manually corrected text."""
    by_page = {entry["page"]: entry for entry in original if entry.get("page") is not None}
    merged = []
    for entry in edited:
        result = dict(by_page.get(entry.get("page"), {}))
        result.update(entry)
        if result.get("blocks"):
            result["layout_text_alignment"] = "stale"
        merged.append(result)
    return merged


def manifest_page_count(manifest: list[dict[str, Any]] | None) -> int:
    """Zero signals unknown pagination, including unmapped legacy artifacts."""
    if not manifest or any(p.get("page") is None for p in manifest):
        return 0
    return max(p["page"] for p in manifest)


def chunk_source_pages(
    chunker: BaseChunker, markdown: str, page_count: int, **config: Any,
) -> list[ChunkDraft]:
    """Keep each chunk within one evidenced page regardless of chunking strategy."""
    chunks: list[ChunkDraft] = []
    for page in canonical_pages(markdown, page_count):
        for chunk in chunker.chunk(page["markdown_content"], **config):
            chunk.page_number = page["page_number"]
            chunk.index = len(chunks)
            chunks.append(chunk)
    return chunks


def canonical_pages(markdown: str | None, page_count: int = 1) -> list[dict[str, Any]]:
    """Return page content for facts/citations, or an unknown page when unmapped."""
    if not markdown:
        return []
    markers = list(_PAGE_MARKER.finditer(markdown))
    if not markers:
        return [{"page_number": 1 if page_count == 1 else None, "markdown_content": markdown}]
    pages: list[dict[str, Any]] = []
    prefix = markdown[:markers[0].start()].strip()
    if prefix:
        pages.append({"page_number": None, "markdown_content": prefix})
    for idx, marker in enumerate(markers):
        end = markers[idx + 1].start() if idx + 1 < len(markers) else len(markdown)
        pages.append({"page_number": int(marker.group(1)), "markdown_content": markdown[marker.end():end].strip()})
    return pages


def normalize_source_pages(
    raw_text: str, page_count: int = 1, pages: list[Any] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Normalize each OCR page independently so table cleaning cannot erase boundaries."""
    if pages:
        records = [
            {
                "page_number": p["page_number"] if isinstance(p, dict) else p.page_number,
                "markdown_content": p["extracted_text"] if isinstance(p, dict) else p.extracted_text,
                "dimensions": p.get("dimensions") if isinstance(p, dict) else getattr(p, "dimensions", None),
                "blocks": p.get("blocks", []) if isinstance(p, dict) else getattr(p, "blocks", []),
                "has_tables": p.get("has_tables", False) if isinstance(p, dict) else getattr(p, "has_tables", False),
                "engine_used": p.get("engine_used") if isinstance(p, dict) else None,
                "content_status": p.get("content_status") if isinstance(p, dict) else None,
                "blank_detection": p.get("blank_detection") if isinstance(p, dict) else None,
            }
            for p in pages
        ]
    else:
        records = canonical_pages(raw_text, page_count)
    parts = []
    manifest = []
    marked = bool(pages or _PAGE_MARKER.search(raw_text))
    for record in records:
        content = clean_markdown_text(record["markdown_content"])
        page = record["page_number"]
        parts.append(f"<!-- Trang {page} -->\n{content}" if marked and page is not None else content)
        manifest_item: dict[str, Any] = {
            "page": page,
            "chars": len(content),
        }
        if record.get("dimensions"):
            manifest_item["dimensions"] = record["dimensions"]
        if record.get("blocks"):
            manifest_item["blocks"] = record["blocks"]
        if record.get("has_tables"):
            manifest_item["has_tables"] = True
        if record.get("engine_used"):
            manifest_item["engine_used"] = record["engine_used"]
        if record.get("content_status"):
            manifest_item["content_status"] = record["content_status"]
        if record.get("blank_detection"):
            manifest_item["blank_detection"] = record["blank_detection"]
        manifest.append(manifest_item)
    return "\n\n".join(parts).strip(), manifest
