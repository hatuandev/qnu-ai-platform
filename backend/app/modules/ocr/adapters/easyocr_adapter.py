"""EasyOCR Engine Adapter — Vietnamese/English Text Recognition for Scans.

EasyOCR is an OPTIONAL dependency. Like the Docling adapter, imports are lazy:
:meth:`is_available` uses ``find_spec`` and :meth:`extract` raises a clear
error when the package (or its models) is missing. PDF pages are rasterized
with PyMuPDF before recognition.
"""

from __future__ import annotations

import asyncio
import importlib.util
import logging
from typing import Any

from app.modules.ocr.adapters.base import BaseOCRAdapter

logger = logging.getLogger(__name__)

_ocr_reader: Any = None


def is_easyocr_installed() -> bool:
    """Check EasyOCR availability without importing the heavy package."""
    return importlib.util.find_spec("easyocr") is not None


def _get_reader() -> Any:
    """Lazily build a shared Vietnamese+English EasyOCR reader."""
    global _ocr_reader
    if _ocr_reader is None:
        try:
            import easyocr
        except ImportError as exc:
            raise RuntimeError(
                "EasyOCR is not installed. Install it with "
                "'uv add easyocr' to enable scan/stamp recognition."
            ) from exc
        _ocr_reader = easyocr.Reader(["vi", "en"], gpu=False)
    return _ocr_reader


class EasyOCRAdapter(BaseOCRAdapter):
    """Adapter recognizing text in scanned pages and red stamps via EasyOCR."""

    @property
    def name(self) -> str:
        return "easyocr"

    @property
    def display_name(self) -> str:
        return "EasyOCR Local (Scanned Pages & Red Stamps, vi+en)"

    def is_available(self) -> bool:
        return is_easyocr_installed()

    def _sync_extract(self, content: bytes, filename: str) -> dict[str, Any]:
        import pymupdf as fitz

        reader = _get_reader()
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"

        page_images: list[tuple[int, bytes]] = []
        if ext in ("png", "jpg", "jpeg", "webp", "bmp"):
            page_images = [(1, content)]
        else:
            doc = fitz.open(stream=content, filetype="pdf")
            for page in doc:
                pix = page.get_pixmap(dpi=200)
                page_images.append((page.number + 1, pix.tobytes("png")))
            doc.close()

        pages_out: list[dict[str, Any]] = []
        all_text: list[str] = []
        for page_number, image_bytes in page_images:
            try:
                import numpy as np

                image_array = np.frombuffer(image_bytes, dtype="uint8")
                segments: list[str] = reader.readtext(image_array, detail=0)
            except Exception as exc:
                logger.warning("EasyOCR page %d failed: %s", page_number, exc)
                segments = []
            text = "\n".join(s.strip() for s in segments if s and s.strip())
            words = text.split()
            lines = [line for line in text.splitlines() if line.strip()]
            pages_out.append(
                {
                    "page_number": page_number,
                    "extracted_text": text,
                    "confidence": 0.90 if text else 0.40,
                    "word_count": len(words),
                    "line_count": len(lines),
                    "has_tables": False,
                }
            )
            if text:
                all_text.append(f"\n\n<!-- Page {page_number} -->\n{text}")

        overall_conf = (
            round(sum(p["confidence"] for p in pages_out) / len(pages_out), 2)
            if pages_out
            else 0.0
        )
        return {
            "engine_used": self.name,
            "total_pages": len(pages_out),
            "overall_confidence": overall_conf,
            "pages": pages_out,
            "raw_text": "".join(all_text).strip(),
        }

    async def extract(self, content: bytes, filename: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._sync_extract, content, filename)
