"""Mistral OCR Engine Adapter — High-Speed Cloud Vision & Document Intelligence."""

from __future__ import annotations

import base64
import logging
import mimetypes
import os
from typing import Any

import httpx

from app.core.config import settings
from app.modules.ocr.adapters.base import BaseOCRAdapter

logger = logging.getLogger(__name__)


class MistralOCRAdapter(BaseOCRAdapter):
    """Adapter sending documents to Mistral OCR Cloud API (mistral-ocr-latest)."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self._api_key = api_key
        self._base_url = (base_url or "https://api.mistral.ai/v1").rstrip("/")

    @property
    def name(self) -> str:
        return "mistral_ocr"

    @property
    def display_name(self) -> str:
        return "Mistral OCR (Cloud API Vision & Document Intelligence)"

    @property
    def api_key(self) -> str | None:
        return self._api_key or settings.MISTRAL_API_KEY

    def is_available(self) -> bool:
        key = self.api_key
        return bool(key and key.strip())

    async def extract(self, content: bytes, filename: str) -> dict[str, Any]:
        """Call Mistral OCR API to extract structured markdown and pages."""
        key = self.api_key
        if not key or not key.strip():
            raise RuntimeError(
                "Mistral API Key chưa được cấu hình. Vui lòng thiết lập MISTRAL_API_KEY trong hệ thống."
            )

        ext = os.path.splitext(filename)[1].lower() if "." in filename else ".pdf"
        mime_type = "application/pdf"
        if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
            mime_type = mimetypes.types_map.get(ext, "image/png")

        b64_data = base64.b64encode(content).decode("utf-8")
        data_url = f"data:{mime_type};base64,{b64_data}"

        payload = {
            "model": "mistral-ocr-latest",
            "document": {
                "type": "document_url",
                "document_url": data_url,
            },
        }

        headers = {
            "Authorization": f"Bearer {key.strip()}",
            "Content-Type": "application/json",
        }

        endpoint = f"{self._base_url}/ocr"
        logger.info(
            "Gửi tài liệu '%s' (%d bytes) tới Mistral OCR API: %s",
            filename,
            len(content),
            endpoint,
        )

        async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
            resp = await client.post(endpoint, json=payload, headers=headers)

        if resp.status_code != 200:
            err_msg = resp.text
            try:
                err_json = resp.json()
                err_msg = err_json.get("message") or err_json.get("detail") or resp.text
            except Exception:
                pass
            raise RuntimeError(f"Mistral OCR API error ({resp.status_code}): {err_msg}")

        data = resp.json()
        raw_pages = data.get("pages", [])
        if not raw_pages:
            raise RuntimeError("Mistral OCR không trích xuất được trang nào từ tài liệu.")

        pages_out: list[dict[str, Any]] = []
        all_text: list[str] = []

        # Extract visual geometry using SmartLayoutDetector (PyMuPDF hybrid + OpenCV)
        geometry_by_page: dict[int, list[dict[str, Any]]] = {}
        raw_pages_text = {
            int(p.get("index", 0)) + 1: (p.get("markdown") or "").strip()
            for p in raw_pages
        }
        try:
            import cv2
            import numpy as np
            import pymupdf as fitz

            from app.modules.ocr.layout_detector import SmartLayoutDetector

            detector = SmartLayoutDetector()
            if ext == ".pdf":
                pdf = fitz.open(stream=content, filetype="pdf")
                for p_idx, page in enumerate(pdf):
                    p_num = p_idx + 1
                    try:
                        pix = page.get_pixmap(dpi=150)
                        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                            (pix.height, pix.width, pix.n)
                        )
                        if pix.n == 4:
                            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
                        elif pix.n == 3:
                            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                        else:
                            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_GRAY2BGR)

                        page_txt = raw_pages_text.get(p_num) or page.get_text() or ""
                        regs = detector.detect_layout_regions(
                            img_bgr,
                            markdown_text=page_txt,
                            page_number=p_num,
                            fitz_page=page,
                        )
                        if regs:
                            geometry_by_page[p_num] = [
                                {
                                    "type": str(r.get("type", "text")),
                                    "label": str(r.get("label") or r.get("type", "text")),
                                    "content_snippet": str(r.get("text") or "")[:160],
                                    "coordinates": {
                                        "x": float(r.get("left", 0.0)),
                                        "y": float(r.get("top", 0.0)),
                                        "width": float(r.get("width", 0.0)),
                                        "height": float(r.get("height", 0.0)),
                                    },
                                    "confidence": 0.98 if r.get("type") in ("table", "signature") else 0.92,
                                }
                                for r in regs
                            ]
                    except Exception as p_err:
                        logger.debug("Failed layout extraction on PDF page %d: %s", p_num, p_err)
                pdf.close()
            elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
                nparr = np.frombuffer(content, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is not None:
                    page_txt = raw_pages_text.get(1) or ""
                    regs = detector.detect_layout_regions(img, markdown_text=page_txt, page_number=1)
                    if regs:
                        geometry_by_page[1] = [
                            {
                                "type": str(r.get("type", "text")),
                                "label": str(r.get("label") or r.get("type", "text")),
                                "content_snippet": str(r.get("text") or "")[:160],
                                "coordinates": {
                                    "x": float(r.get("left", 0.0)),
                                    "y": float(r.get("top", 0.0)),
                                    "width": float(r.get("width", 0.0)),
                                    "height": float(r.get("height", 0.0)),
                                },
                                "confidence": 0.98 if r.get("type") in ("table", "signature") else 0.92,
                            }
                            for r in regs
                        ]
        except Exception as exc:
            logger.debug("SmartLayoutDetector skipped in Mistral adapter: %s", exc)

        for p in raw_pages:
            pnum = int(p.get("index", 0)) + 1
            text = (p.get("markdown") or "").strip()
            words = text.split()
            lines = [line for line in text.splitlines() if line.strip()]
            has_tables = any(
                line.strip().startswith("|") and line.strip().endswith("|") for line in lines
            )

            # Use detected computer vision / vector geometry if available
            blocks = geometry_by_page.get(pnum, [])

            pages_out.append({
                "page_number": pnum,
                "extracted_text": text,
                "confidence": 0.98 if text else 0.50,
                "word_count": len(words),
                "line_count": len(lines),
                "has_tables": has_tables,
                "blocks": blocks,
            })
            if text:
                all_text.append(f"<!-- Trang {pnum} -->\n\n{text}")

        total_pages = len(pages_out)
        return {
            "engine_used": self.name,
            "total_pages": total_pages,
            "overall_confidence": 0.98,
            "pages": pages_out,
            "raw_text": "\n\n---\n\n".join(all_text),
        }
