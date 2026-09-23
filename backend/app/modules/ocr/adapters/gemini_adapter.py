"""Google Gemini Vision OCR Engine Adapter — High-Speed Cloud Multimodal Document Intelligence."""

from __future__ import annotations

import base64
import logging
import mimetypes
import os
import re
from typing import Any

import httpx

from app.core.config import settings
from app.modules.ocr.adapters.base import BaseOCRAdapter

logger = logging.getLogger(__name__)

_DEFAULT_GEMINI_OCR_MODEL = "gemini-2.5-flash"


class GeminiOCRAdapter(BaseOCRAdapter):
    """Adapter sending documents to Google Gemini Vision / Multimodal API for high-fidelity OCR."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._model_name = model_name or _DEFAULT_GEMINI_OCR_MODEL
        self._base_url = (
            base_url or "https://generativelanguage.googleapis.com/v1beta"
        ).rstrip("/")

    @property
    def name(self) -> str:
        return "gemini_ocr"

    @property
    def display_name(self) -> str:
        return f"Google Gemini Vision OCR ({self.model_name})"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def api_key(self) -> str | None:
        if self._api_key and self._api_key.strip():
            return self._api_key.strip()
        return settings.GEMINI_API_KEY or None

    def is_available(self) -> bool:
        key = self.api_key
        return bool(key and key.strip())

    async def extract(self, content: bytes, filename: str) -> dict[str, Any]:
        """Call Google Gemini Vision API to extract structured Markdown and detect page layouts."""
        key = self.api_key
        if not key or not key.strip():
            # Attempt to retrieve from database if runtime settings not yet populated
            from sqlalchemy import select

            from app.core.crypto import decrypt_secret, is_encrypted
            from app.core.database import AsyncSessionFactory
            from app.modules.modelops.models import ModelProviderConfig

            try:
                async with AsyncSessionFactory() as db:
                    stmt = select(ModelProviderConfig).where(
                        ModelProviderConfig.provider_type == "gemini",
                        ModelProviderConfig.is_active.is_(True),
                    )
                    res = await db.execute(stmt)
                    p = res.scalars().first()
                    if p and p.api_key_encrypted:
                        raw_key = p.api_key_encrypted
                        key = decrypt_secret(raw_key) if is_encrypted(raw_key) else raw_key
                        settings.GEMINI_API_KEY = key
            except Exception as db_exc:
                logger.debug("Failed fetching Gemini API key from database: %s", db_exc)

        if not key or not key.strip():
            raise RuntimeError(
                "Google Gemini API Key chưa được cấu hình. Vui lòng thiết lập GEMINI_API_KEY trong hệ thống."
            )

        ext = os.path.splitext(filename)[1].lower() if "." in filename else ".pdf"
        mime_type = "application/pdf"
        if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
            mime_type = mimetypes.types_map.get(ext, "image/png")

        b64_data = base64.b64encode(content).decode("utf-8")

        prompt = (
            "Bạn là chuyên gia OCR và phân tích cấu trúc tài liệu hành chính tiếng Việt cao cấp "
            "của Trường Đại học Quy Nhơn (QNU).\n"
            "Hãy bóc tách TOÀN BỘ nội dung của tài liệu này thành định dạng GitHub Flavored Markdown (GFM) "
            "chuẩn xác 100% theo các quy tắc bắt buộc sau:\n"
            "1. BẢO TOÀN NỘI DUNG: Giữ nguyên 100% nội dung chữ, tiêu đề cấp mục (#, ##, ###), "
            "số hiệu văn bản, ngày tháng, họ tên, các điều khoản, ghi chú, con dấu và chữ ký.\n"
            "2. BẢNG BIỂU CHUẨN GFM: Mọi bảng biểu phải chuyển thành bảng Markdown hoàn chỉnh với hàng tiêu đề "
            "và hàng phân cách '|:---|:---|' rõ ràng. Giữ nguyên vẹn toàn bộ các hàng và cột.\n"
            "3. PHÂN TÁCH TRANG CHUẨN XÁC: Nếu tài liệu có nhiều trang, BẮT BUỘC phải đặt nhãn phân cách trang:\n"
            "<!-- Trang X -->\n"
            "[Nội dung trang X]\n\n---\n\n"
            "4. KHÔNG BỊA ĐẶT / KHÔNG TẮT: Tuyệt đối cấm tự ý tóm tắt, cắt xén, bỏ bớt hàng bảng hoặc phát sinh thông tin sai lệch.\n"
            "5. CHUẨN UTF-8: Đảm bảo toàn bộ ký tự tiếng Việt hiển thị sạch sẽ theo chuẩn Unicode NFC."
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": b64_data,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 65536,
            },
        }

        endpoint = (
            f"{self._base_url}/models/{self.model_name}:generateContent?key={key.strip()}"
        )
        logger.info(
            "Gửi tài liệu '%s' (%d bytes) tới Google Gemini Vision OCR (%s)",
            filename,
            len(content),
            self.model_name,
        )

        async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
            resp = await client.post(endpoint, json=payload)

        if resp.status_code != 200:
            err_msg = resp.text
            try:
                err_json = resp.json()
                err_msg = (
                    err_json.get("error", {}).get("message")
                    or err_json.get("message")
                    or resp.text
                )
            except Exception:
                pass
            raise RuntimeError(
                f"Google Gemini Vision OCR API error ({resp.status_code}): {err_msg}"
            )

        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError("Google Gemini OCR không trả về kết quả khả dụng.")

        extracted_raw = ""
        parts = candidates[0].get("content", {}).get("parts") or []
        for part in parts:
            if "text" in part:
                extracted_raw += part["text"]

        extracted_raw = extracted_raw.strip()
        if not extracted_raw:
            raise RuntimeError("Nội dung bóc tách từ Google Gemini OCR bị rỗng.")

        # Parse pages by standard <!-- Trang N --> or --- delimiters
        page_chunks: list[tuple[int, str]] = []
        page_pattern = re.compile(r"<!--\s*Trang\s*(\d+)\s*-->", re.IGNORECASE)
        splits = page_pattern.split(extracted_raw)

        if len(splits) > 1:
            # Format: [preamble, page_num_1, page_text_1, page_num_2, page_text_2, ...]
            # First element might be preamble
            if splits[0].strip():
                page_chunks.append((1, splits[0].strip()))
            for i in range(1, len(splits), 2):
                p_num = int(splits[i])
                p_text = splits[i + 1].strip() if i + 1 < len(splits) else ""
                # Strip trailing page separator if present
                p_text = re.sub(r"\n+---+\s*$", "", p_text).strip()
                page_chunks.append((p_num, p_text))
        else:
            # Split by Markdown page divider ---
            raw_pages_split = re.split(r"\n+---+\n+", extracted_raw)
            for idx, p_text in enumerate(raw_pages_split, start=1):
                clean_p = p_text.strip()
                if clean_p:
                    page_chunks.append((idx, clean_p))

        if not page_chunks:
            page_chunks = [(1, extracted_raw)]

        # Extract visual geometry using SmartLayoutDetector (PyMuPDF hybrid + OpenCV)
        geometry_by_page: dict[int, list[dict[str, Any]]] = {}
        raw_pages_text = {p_num: p_text for p_num, p_text in page_chunks}

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
                                    "confidence": 0.99 if r.get("type") in ("table", "signature") else 0.95,
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
                                "confidence": 0.99 if r.get("type") in ("table", "signature") else 0.95,
                            }
                            for r in regs
                        ]
        except Exception as exc:
            logger.debug("SmartLayoutDetector skipped in Gemini OCR adapter: %s", exc)

        pages_out: list[dict[str, Any]] = []
        all_text: list[str] = []

        for p_num, text in page_chunks:
            words = text.split()
            lines = [line for line in text.splitlines() if line.strip()]
            has_tables = any(
                line.strip().startswith("|") and line.strip().endswith("|") for line in lines
            )
            blocks = geometry_by_page.get(p_num, [])

            pages_out.append({
                "page_number": p_num,
                "extracted_text": text,
                "confidence": 0.99 if text else 0.50,
                "word_count": len(words),
                "line_count": len(lines),
                "has_tables": has_tables,
                "blocks": blocks,
            })
            if text:
                all_text.append(f"<!-- Trang {p_num} -->\n\n{text}")

        return {
            "engine_used": self.name,
            "total_pages": len(pages_out),
            "overall_confidence": 0.99,
            "pages": pages_out,
            "raw_text": "\n\n---\n\n".join(all_text),
        }
