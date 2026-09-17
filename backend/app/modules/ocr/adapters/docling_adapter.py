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
        geometry_by_page = self._extract_geometry_blocks(result)

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
                    "blocks": geometry_by_page.get(page_number, []),
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

    @staticmethod
    def _extract_geometry_blocks(result: Any) -> dict[int, list[dict[str, Any]]]:
        """Collect real layout boxes (provenance bboxes) grouped per page.

        Coordinates are normalized to 0–100 %. Per-block confidence is not
        exposed by this Docling API version, so blocks carry the engine-level
        default confidence documented in the response (never invented content).
        """
        from app.modules.knowledge.parsers.blocks import to_percent

        geometry: dict[int, list[dict[str, Any]]] = {}
        try:
            document = result.document
            page_sizes: dict[int, tuple[float, float]] = {}
            for page_no, page_item in (getattr(document, "pages", None) or {}).items():
                size = getattr(page_item, "size", None)
                if size is not None:
                    page_sizes[int(page_no)] = (
                        float(getattr(size, "width", 0) or 0),
                        float(getattr(size, "height", 0) or 0),
                    )
            counters: dict[str, int] = {}
            for item, _level in document.iterate_items():
                prov_list = getattr(item, "prov", None) or []
                if not prov_list:
                    continue
                prov = prov_list[0]
                page_no = getattr(prov, "page_no", None)
                bbox = getattr(prov, "bbox", None)
                if page_no is None or bbox is None:
                    continue
                page_no = int(page_no)
                if page_no not in page_sizes:
                    continue
                page_width, page_height = page_sizes[page_no]
                if page_width <= 0 or page_height <= 0:
                    continue
                try:
                    coords = to_percent(
                        float(getattr(bbox, "l", 0)),
                        float(getattr(bbox, "t", 0)),
                        float(getattr(bbox, "r", 0)),
                        float(getattr(bbox, "b", 0)),
                        page_width,
                        page_height,
                    )
                except (TypeError, ValueError):
                    continue
                raw_label = str(getattr(item, "label", "text") or "text").lower()
                if "table" in raw_label:
                    box_type, default_conf = "table", 0.95
                elif "header" in raw_label or "title" in raw_label:
                    box_type, default_conf = "header", 0.92
                else:
                    box_type, default_conf = "text", 0.90
                counters[box_type] = counters.get(box_type, 0) + 1
                snippet = str(getattr(item, "text", "") or "").strip().replace("\n", " ")
                geometry.setdefault(page_no, []).append(
                    {
                        "type": box_type,
                        "coordinates": coords,
                        "label": f"{box_type.capitalize()} {counters[box_type]}",
                        "content_snippet": snippet[:160],
                        "confidence": default_conf,
                    }
                )
        except Exception as exc:
            logger.debug("Docling geometry extraction failed (boxes omitted): %s", exc)
        return geometry

    async def extract(self, content: bytes, filename: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._sync_extract, content, filename)
