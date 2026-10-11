"""PaddleOCR-VL Layout Parsing Engine Adapter — Enterprise On-Premise Vision & Document Intelligence."""

from __future__ import annotations

import base64
import logging
import os
import unicodedata
from typing import Any

import httpx

from app.core.exceptions import AppException
from app.modules.ocr.adapters.base import BaseOCRAdapter

logger = logging.getLogger(__name__)

class PaddleOCRVLAdapter(BaseOCRAdapter):
    """Adapter sending documents to PaddleOCR-VL Document Layout Parsing service."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 90.0,
        model_name: str | None = None,
    ) -> None:
        self._base_url = (base_url or "").rstrip("/")
        self._timeout = timeout
        self._model_name = model_name or ""

    @property
    def name(self) -> str:
        return "paddleocr_ocr"

    @property
    def display_name(self) -> str:
        return f"PaddleOCR-VL ({self._model_name})"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def base_url(self) -> str:
        return self._base_url

    def is_available(self) -> bool:
        """PaddleOCR-VL on-premise engine is considered available if configured with valid URL."""
        return bool(self._base_url and self._base_url.startswith("http"))

    async def extract(self, content: bytes, filename: str) -> dict[str, Any]:
        """Call PaddleOCR-VL /layout-parsing to extract structured markdown and layout structure.

        Args:
            content: Document raw binary stream (PDF, PNG, JPG, etc.).
            filename: Original file name to determine file format type.

        Returns:
            Structured dict conforming to BaseOCRAdapter contract:
            - engine_used: "paddleocr_vl"
            - total_pages: int
            - overall_confidence: float
            - pages: list of page dicts
            - raw_text: concatenated Markdown string
        """
        if not self.is_available():
            raise AppException("Provider OCR chưa được cấu hình.", code="OCR_PROVIDER_UNAVAILABLE", status_code=503)
        if not content:
            raise AppException(
                message="Tệp tài liệu rỗng, không thể thực hiện bóc tách OCR.",
                code="DOCUMENT_CONTENT_EMPTY",
                status_code=400,
            )

        ext = os.path.splitext(filename)[1].lower() if "." in filename else ".pdf"
        # 0 = PDF, 1 = Image (PNG, JPG, TIFF, etc.) according to OpenAPI InferRequest schema
        file_type = 0 if ext == ".pdf" else 1

        b64_file = base64.b64encode(content).decode("utf-8")
        payload = {
            "file": b64_file,
            "fileType": file_type,
            "visualize": False,
        }

        endpoint = f"{self._base_url}/layout-parsing"
        logger.info(
            "Calling PaddleOCR-VL layout parsing at %s for %s (%d bytes, type=%s)",
            endpoint,
            filename,
            len(content),
            "PDF" if file_type == 0 else "Image",
        )

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(endpoint, json=payload)
        except httpx.TimeoutException as exc:
            logger.error("PaddleOCR-VL timeout after %.1f seconds: %s", self._timeout, exc)
            raise AppException(
                message=f"Dịch vụ PaddleOCR-VL quá thời gian phản hồi ({self._timeout}s). Vui lòng thử lại sau.",
                code="OCR_SERVICE_TIMEOUT",
                status_code=504,
            ) from exc
        except httpx.RequestError as exc:
            logger.error("PaddleOCR-VL connection failed at %s: %s", endpoint, exc)
            raise AppException(
                message=f"Không thể kết nối đến máy chủ PaddleOCR-VL ({endpoint}): {exc}",
                code="OCR_SERVICE_UNAVAILABLE",
                status_code=502,
            ) from exc

        if response.status_code != 200:
            logger.error("PaddleOCR-VL HTTP error %d: %s", response.status_code, response.text[:300])
            raise AppException(
                message=f"Máy chủ PaddleOCR-VL phản hồi mã lỗi HTTP {response.status_code}.",
                code="OCR_INFERENCE_ERROR",
                status_code=502,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise AppException("Phản hồi OCR không phải JSON hợp lệ.", code="OCR_RESPONSE_INVALID", status_code=502) from exc
        if not isinstance(data, dict):
            raise AppException("Cấu trúc phản hồi OCR không hợp lệ.", code="OCR_RESPONSE_INVALID", status_code=502)
        error_code = data.get("errorCode", 0)
        error_msg = data.get("errorMsg", "Success")

        if error_code != 0 and error_code is not None:
            logger.error("PaddleOCR-VL inference error: code=%s msg=%s", error_code, error_msg)
            raise AppException(
                message=f"PaddleOCR-VL bóc tách thất bại: {error_msg} (Mã lỗi: {error_code})",
                code="OCR_INFERENCE_FAILED",
                status_code=422,
            )

        result = data.get("result")
        layout_results = result.get("layoutParsingResults") if isinstance(result, dict) else None
        if not isinstance(layout_results, list):
            raise AppException("Phản hồi OCR thiếu danh sách trang.", code="OCR_RESPONSE_INVALID", status_code=502)
        if not layout_results:
            raise AppException("OCR không trả về nội dung trang.", code="OCR_CONTENT_EMPTY", status_code=422)

        pages_data: list[dict[str, Any]] = []
        raw_text_parts: list[str] = []

        for idx, item in enumerate(layout_results):
            page_no = idx + 1
            md_block = item.get("markdown") if isinstance(item, dict) else None
            page_text = md_block.get("text") if isinstance(md_block, dict) else None
            if not isinstance(page_text, str):
                raise AppException("Nội dung trang OCR không hợp lệ.", code="OCR_RESPONSE_INVALID", status_code=502)
            # Enforce Unicode NFC Canonical Normalization
            normalized_text = unicodedata.normalize("NFC", page_text).strip()

            pruned = item.get("prunedResult") or {}
            # Detect tables from Markdown or pruned result keys
            has_tables = "|" in normalized_text or "table" in str(pruned).lower()

            words = len(normalized_text.split())
            lines = len(normalized_text.splitlines()) if normalized_text else 0

            # 1. Parse Image Dimensions used by the OCR engine
            img_width = pruned.get("width") if isinstance(pruned.get("width"), (int, float)) else None
            img_height = pruned.get("height") if isinstance(pruned.get("height"), (int, float)) else None
            dimensions = {"width": int(img_width), "height": int(img_height)} if img_width and img_height else None

            # 2. Extract Layout Detection scores (separating layout confidence from OCR text confidence)
            layout_boxes = (pruned.get("layout_det_res") or {}).get("boxes", []) if isinstance(pruned.get("layout_det_res"), dict) else []
            scores_by_order: dict[int, float] = {}
            for box in layout_boxes:
                if isinstance(box, dict) and "order" in box and "score" in box:
                    try:
                        scores_by_order[int(box["order"])] = float(box["score"])
                    except (ValueError, TypeError):
                        pass

            # 3. Parse parsing_res_list into structured blocks
            parsing_list = pruned.get("parsing_res_list", []) if isinstance(pruned.get("parsing_res_list"), list) else []
            blocks: list[dict[str, Any]] = []

            label_vi_map = {
                "text": "Khối văn bản",
                "title": "Tiêu đề",
                "table": "Bảng dữ liệu",
                "figure": "Hình ảnh",
                "header": "Đầu trang",
                "footer": "Chân trang",
                "stamp": "Con dấu",
                "signature": "Chữ ký",
            }

            for b_idx, block in enumerate(parsing_list):
                if not isinstance(block, dict):
                    continue
                b_id = block.get("block_id", b_idx)
                b_order = block.get("block_order", b_idx + 1)
                b_label = str(block.get("block_label") or "text").lower()
                b_content = unicodedata.normalize("NFC", str(block.get("block_content") or "")).strip()
                b_bbox = block.get("block_bbox")
                b_polygon = block.get("block_polygon_points")

                # Layout detection confidence vs OCR text confidence distinction
                layout_conf = scores_by_order.get(b_order)

                # Normalized coordinates calculation (0 - 100%)
                coords: dict[str, Any] = {}
                left_pct = 0.0
                top_pct = 0.0
                width_pct = 0.0
                height_pct = 0.0
                is_valid_coord = False

                if dimensions and isinstance(b_bbox, list) and len(b_bbox) >= 4:
                    try:
                        x0, y0, x1, y1 = float(b_bbox[0]), float(b_bbox[1]), float(b_bbox[2]), float(b_bbox[3])
                        w = max(0.0, x1 - x0)
                        h = max(0.0, y1 - y0)
                        if dimensions["width"] > 0 and dimensions["height"] > 0:
                            left_pct = round(max(0.0, min(100.0, (x0 / dimensions["width"]) * 100)), 2)
                            top_pct = round(max(0.0, min(100.0, (y0 / dimensions["height"]) * 100)), 2)
                            width_pct = round(max(0.0, min(100.0 - left_pct, (w / dimensions["width"]) * 100)), 2)
                            height_pct = round(max(0.0, min(100.0 - top_pct, (h / dimensions["height"]) * 100)), 2)
                            is_valid_coord = True
                    except (ValueError, TypeError):
                        pass

                coords = {
                    "left": left_pct,
                    "top": top_pct,
                    "width": width_pct,
                    "height": height_pct,
                    "raw_bbox": b_bbox,
                    "is_valid": is_valid_coord,
                    "coordinate_system": "normalized_percent",
                }

                blocks.append({
                    "id": f"block_{page_no}_{b_id}",
                    "order": b_order,
                    "type": b_label,
                    "label": label_vi_map.get(b_label, b_label.capitalize()),
                    "text": b_content,
                    "content_snippet": b_content[:100],
                    "layout_confidence": layout_conf,
                    "text_confidence": None,
                    "confidence_source": "unavailable",
                    "polygon": b_polygon,
                    "coordinates": coords,
                    "top": top_pct,
                    "left": left_pct,
                    "width": width_pct,
                    "height": height_pct,
                })

            pages_data.append(
                {
                    "page_number": page_no,
                    "extracted_text": normalized_text,
                    "confidence": 0.0,
                    "confidence_source": "unavailable",
                    "word_count": words,
                    "line_count": lines,
                    "has_tables": has_tables,
                    "dimensions": dimensions,
                    "blocks": blocks,
                    "layout_pruned": pruned if isinstance(pruned, dict) else {},
                }
            )
            raw_text_parts.append(f"<!-- Trang {page_no} -->\n{normalized_text}")

        if not any(page["extracted_text"] for page in pages_data):
            raise AppException("OCR không nhận dạng được văn bản.", code="OCR_CONTENT_EMPTY", status_code=422)

        full_raw_text = "\n\n".join(raw_text_parts)

        return {
            "engine_used": "paddleocr_vl",
            "total_pages": len(pages_data),
            "overall_confidence": 0.0,
            "confidence_source": "unavailable",
            "pages": pages_data,
            "raw_text": full_raw_text,
        }
