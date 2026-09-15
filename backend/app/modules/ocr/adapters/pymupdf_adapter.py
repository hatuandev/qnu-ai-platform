"""PyMuPDF Engine Adapter for Digital & Scanned Document Text Extraction."""

from __future__ import annotations

import asyncio
from typing import Any

import pymupdf as fitz

from app.modules.ocr.adapters.base import BaseOCRAdapter


class PyMuPDFOCRAdapter(BaseOCRAdapter):
    """Adapter extracting text and page structure using PyMuPDF (fitz)."""

    @property
    def name(self) -> str:
        return "pymupdf_ocr"

    @property
    def display_name(self) -> str:
        return "PyMuPDF Fast Document Extractor"

    def is_available(self) -> bool:
        return True

    def _sync_extract(self, content: bytes, filename: str) -> dict[str, Any]:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
        filetype = ext if ext in ["pdf", "png", "jpg", "jpeg", "webp", "bmp"] else "pdf"

        doc = fitz.open(stream=content, filetype=filetype)
        pages_out = []
        all_text = []

        total_pages = len(doc)
        for i, page in enumerate(doc):
            pnum = i + 1
            text = page.get_text("text").strip()
            confidence = 0.95 if text else 0.60
            lines = [line for line in text.splitlines() if line.strip()]
            words = text.split()
            has_tables = False
            if "|" in text:
                has_tables = True
            else:
                try:
                    tabs = page.find_tables()
                    has_tables = bool(getattr(tabs, "tables", []))
                except Exception:
                    has_tables = False

            pages_out.append({
                "page_number": pnum,
                "extracted_text": text,
                "confidence": confidence,
                "word_count": len(words),
                "line_count": len(lines),
                "has_tables": has_tables,
            })
            if text:
                all_text.append(text)

        raw_text = "\n\n".join(all_text)
        overall_conf = round(sum(p["confidence"] for p in pages_out) / max(total_pages, 1), 2)

        return {
            "engine_used": self.name,
            "total_pages": total_pages,
            "overall_confidence": overall_conf,
            "pages": pages_out,
            "raw_text": raw_text,
        }

    async def extract(self, content: bytes, filename: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._sync_extract, content, filename)
