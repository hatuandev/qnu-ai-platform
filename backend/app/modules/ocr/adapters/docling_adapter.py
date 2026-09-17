"""IBM Docling Engine Adapter — Layout Analysis & TableFormer to Markdown.

Docling is an OPTIONAL heavy dependency (pulls torch). This adapter uses lazy
imports so the backend boots fine without it; :meth:`is_available` reports
readiness via ``importlib.util.find_spec`` and :meth:`extract` raises a clear
error when the package is missing instead of silently returning fake data.
"""

from __future__ import annotations

import asyncio
import importlib.util
import io
import logging
from typing import Any

from app.modules.ocr.adapters.base import BaseOCRAdapter

logger = logging.getLogger(__name__)


def is_docling_installed() -> bool:
    """Check Docling availability without importing the heavy package."""
    return importlib.util.find_spec("docling") is not None


class DoclingOCRAdapter(BaseOCRAdapter):
    """Adapter converting PDFs/images to Markdown via Docling TableFormer."""

    @property
    def name(self) -> str:
        return "docling"

    @property
    def display_name(self) -> str:
        return "IBM Docling TableFormer (Layout + Tables to Markdown)"

    def is_available(self) -> bool:
        return is_docling_installed()

    def _sync_extract(self, content: bytes, filename: str) -> dict[str, Any]:
        try:
            from docling.datamodel.base_models import DocumentStream
            from docling.document_converter import DocumentConverter
        except ImportError as exc:
            raise RuntimeError(
                "Docling is not installed. Install it with "
                "'uv add docling' to enable the TableFormer engine."
            ) from exc

        converter = DocumentConverter()
        stream = DocumentStream(name=filename, stream=io.BytesIO(content))
        result = converter.convert(stream)
        full_markdown = result.document.export_to_markdown()

        page_markdowns = self._split_markdown_by_page(result, full_markdown)

        pages_out: list[dict[str, Any]] = []
        all_text: list[str] = []
        for page_number, page_md in sorted(page_markdowns.items()):
            text = page_md.strip()
            words = text.split()
            lines = [line for line in text.splitlines() if line.strip()]
            has_tables = any(
                line.strip().startswith("|") and line.strip().endswith("|") for line in lines
            )
            pages_out.append(
                {
                    "page_number": page_number,
                    "extracted_text": text,
                    "confidence": 0.97 if text else 0.50,
                    "word_count": len(words),
                    "line_count": len(lines),
                    "has_tables": has_tables,
                }
            )
            if text:
                all_text.append(text)

        total_pages = max(page_markdowns.keys(), default=1)
        overall_conf = (
            round(sum(p["confidence"] for p in pages_out) / len(pages_out), 2)
            if pages_out
            else 0.0
        )
        return {
            "engine_used": self.name,
            "total_pages": total_pages,
            "overall_confidence": overall_conf,
            "pages": pages_out,
            "raw_text": "\n\n".join(all_text),
        }

    @staticmethod
    def _split_markdown_by_page(result: Any, full_markdown: str) -> dict[int, str]:
        """Group markdown content per page using item provenance when available."""
        try:
            buckets: dict[int, list[str]] = {}
            document = result.document
            for item, _level in document.iterate_items():
                prov_list = getattr(item, "prov", None) or []
                page_no: int | None = None
                for prov in prov_list:
                    page_no = getattr(prov, "page_no", None)
                    if page_no is not None:
                        break
                if page_no is None:
                    continue
                text = getattr(item, "text", "") or ""
                if text.strip():
                    buckets.setdefault(int(page_no), []).append(text.strip())
            if buckets:
                return {page: "\n\n".join(parts) for page, parts in buckets.items()}
        except Exception as exc:
            logger.debug("Docling per-page grouping failed, using whole markdown: %s", exc)
        return {1: full_markdown}

    async def extract(self, content: bytes, filename: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._sync_extract, content, filename)
