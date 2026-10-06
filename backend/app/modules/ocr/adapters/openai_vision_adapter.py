"""OpenAI-Compatible Vision OCR Engine Adapter — Universal Multimodal Document Intelligence.

Supports all OpenAI-standard vision APIs:
- Qwen-VL (Qwen-2.5-VL-72B / 7B via OpenRouter, DashScope, SiliconFlow)
- OpenAI (GPT-4o, GPT-4o-mini Vision)
- Claude Multimodal (via OpenRouter)
- DeepSeek-VL, Pixtral, Llama-Vision
- Local / Self-hosted (vLLM, Ollama)
"""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
import os
import re
from typing import Any

import httpx

from app.core.config import settings
from app.modules.ocr.adapters.base import BaseOCRAdapter

logger = logging.getLogger(__name__)

_DEFAULT_VISION_OCR_MODEL = "qwen/qwen-2.5-vl-72b-instruct"
_DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenAIVisionOCRAdapter(BaseOCRAdapter):
    """Universal Adapter sending document pages to any OpenAI-compatible Vision API."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        adapter_name: str = "openai_vision_ocr",
    ) -> None:
        self._api_key = api_key
        self._model_name = model_name or _DEFAULT_VISION_OCR_MODEL
        self._adapter_name = adapter_name

        from app.core.config import resolve_ollama_network_url

        if not base_url and ("qwen3-vl" in self._model_name.lower() or "qwen" in self._model_name.lower()):
            default_ollama = getattr(settings, "OLLAMA_BASE_URL", "") or "http://tormemrtxproto.tail0924dd.ts.net:11434"
            self._base_url = resolve_ollama_network_url(default_ollama).rstrip("/")
        else:
            raw_base = base_url or getattr(settings, "OPENROUTER_BASE_URL", _DEFAULT_OPENROUTER_BASE_URL)
            self._base_url = resolve_ollama_network_url(raw_base).rstrip("/")

    @property
    def name(self) -> str:
        return self._adapter_name

    @property
    def display_name(self) -> str:
        if "qwen" in self.model_name.lower():
            return f"Qwen Vision OCR ({self.model_name})"
        if "gpt" in self.model_name.lower():
            return f"OpenAI GPT Vision OCR ({self.model_name})"
        return f"OpenAI Vision OCR ({self.model_name})"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def _is_ollama(self) -> bool:
        return (
            "11434" in self._base_url
            or "ollama" in self._base_url.lower()
            or "qwen3-vl" in self._model_name.lower()
        )

    @property
    def api_key(self) -> str | None:
        if self._is_ollama:
            return "ollama"
        if self._api_key and self._api_key.strip():
            return self._api_key.strip()
        return (
            getattr(settings, "OPENROUTER_API_KEY", None)
            or getattr(settings, "OPENAI_API_KEY", None)
            or None
        )

    def is_available(self) -> bool:
        if self._is_ollama:
            return True
        key = self.api_key
        return bool(key and key.strip())

    async def extract(self, content: bytes, filename: str) -> dict[str, Any]:
        """Call OpenAI-compatible Vision API or native Ollama to extract structured Markdown and detect page layouts."""
        is_ollama = self._is_ollama
        key = self.api_key or ("ollama" if is_ollama else None)

        if not key or not key.strip():
            # Attempt to retrieve from database if runtime settings not yet populated
            from sqlalchemy import select

            from app.core.crypto import decrypt_secret, is_encrypted
            from app.core.database import AsyncSessionFactory
            from app.modules.modelops.models import ModelProviderConfig

            try:
                async with AsyncSessionFactory() as db:
                    stmt = select(ModelProviderConfig).where(
                        ModelProviderConfig.provider_type.in_([
                            "openrouter",
                            "qwen",
                            "openai",
                            "siliconflow",
                            "ollama",
                        ]),
                        ModelProviderConfig.is_active.is_(True),
                    )
                    res = await db.execute(stmt)
                    providers = res.scalars().all()
                    for p in providers:
                        if p.provider_type == "ollama":
                            key = "ollama"
                            if p.api_base_url and not self._base_url:
                                from app.core.config import resolve_ollama_network_url

                                self._base_url = resolve_ollama_network_url(p.api_base_url).rstrip("/")
                            break
                        if p and p.api_key_encrypted:
                            raw_key = p.api_key_encrypted
                            key = decrypt_secret(raw_key) if is_encrypted(raw_key) else raw_key
                            if p.api_base_url and not self._base_url:
                                self._base_url = p.api_base_url.rstrip("/")
                            break
            except Exception as db_exc:
                logger.debug("Failed fetching Vision-compatible API key from database: %s", db_exc)

        if not is_ollama and (not key or not key.strip()):
            raise RuntimeError(
                f"Khóa API cho {self.display_name} chưa được cấu hình. "
                "Vui lòng thiết lập API Key trong phần Quản lý Nhà cung cấp (ModelOps)."
            )

        ext = os.path.splitext(filename)[1].lower() if "." in filename else ".pdf"

        # Prepare images per page
        page_images: list[tuple[int, bytes, str]] = []  # (page_number, img_bytes, mime_type)
        if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
            mime_type = mimetypes.types_map.get(ext, "image/png")
            page_images.append((1, content, mime_type))
        else:
            # Multi-page or single-page PDF: convert to high-fidelity images via PyMuPDF
            try:
                import pymupdf as fitz

                pdf = fitz.open(stream=content, filetype="pdf")
                for p_idx, page in enumerate(pdf):
                    p_num = p_idx + 1
                    pix = page.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("jpeg")
                    page_images.append((p_num, img_bytes, "image/jpeg"))
                pdf.close()
            except Exception as pdf_err:
                logger.warning("PyMuPDF failed to render PDF pages for Vision OCR: %s", pdf_err)
                raise RuntimeError(
                    f"Không thể kết xuất trang PDF để gửi tới Vision OCR: {pdf_err}"
                ) from pdf_err

        if not page_images:
            raise RuntimeError("Tài liệu không có trang nào để nhận dạng.")

        pages_out: list[dict[str, Any]] = []
        all_text: list[str] = []

        endpoint = (
            f"{self._base_url.removesuffix('/v1')}/api/chat"
            if is_ollama
            else f"{self._base_url}/chat/completions"
        )
        headers = {
            "Authorization": f"Bearer {key.strip()}",
            "Content-Type": "application/json",
        }

        # Process each page with Vision LLM
        for p_num, img_bytes, mime_type in page_images:
            b64_data = base64.b64encode(img_bytes).decode("utf-8")
            data_url = f"data:{mime_type};base64,{b64_data}"

            prompt = (
                f"Bạn là chuyên gia OCR và phân tích cấu trúc tài liệu hành chính tiếng Việt cao cấp "
                f"của Trường Đại học Quy Nhơn (QNU). Hãy bóc tách nội dung Trang {p_num} của tài liệu này.\n"
                "Quy tắc bắt buộc:\n"
                "1. BẢO TOÀN NỘI DUNG & CHÍNH TẢ: Giữ nguyên 100% nội dung chữ, tiêu đề cấp mục (#, ##, ###), "
                "số hiệu văn bản, ngày tháng, họ tên, các điều khoản, ghi chú, con dấu và chữ ký. Nhận diện chuẩn xác "
                "thuật ngữ hành chính và tài chính.\n"
                "2. CẤM TUYỆT ĐỐI THẺ HTML THÔ (ZERO RAW HTML TAGS): Tuyệt đối KHÔNG sử dụng các thẻ HTML như "
                "<table>, <tr>, <td>, <hr>, <br>, <center>, <b>, <i> để dàn trang. 100% sử dụng Markdown GFM thuần khiết. "
                "Các khối Quốc hiệu, tiêu ngữ, số hiệu văn bản và Nơi nhận, người ký phải viết dưới dạng văn bản Markdown chuẩn (**, *, -).\n"
                "3. BẢNG BIỂU CHUẨN GFM & PHẲNG HÓA DỮ LIỆU: Mọi bảng biểu phải chuyển thành bảng Markdown hoàn chỉnh với hàng tiêu đề "
                "và hàng phân cách '|:---|:---|'. Giữ nguyên vẹn toàn bộ các hàng và cột.\n"
                "   - BẢNG HỌC PHÍ / CHỈ TIÊU: Mỗi phương án đào tạo (thời gian học, mức học phí) tách thành 1 HÀNG ĐỘC LẬP đầy đủ thông tin. "
                "TUYỆT ĐỐI KHÔNG gộp nhiều mức học phí vào cùng một ô bằng thẻ <br> hay dấu xuống dòng.\n"
                "   - BẢNG TIẾP NỐI QUA TRANG: Giữ lại đầy đủ 100% các hàng tiếp nối ở đầu trang (kể cả hàng có STT bị để trống). Lặp lại hàng tiêu đề bảng.\n"
                "4. CHỐNG BẺ ĐÔI TỪ: Không bẻ gãy từ tiếng Việt.\n"
                "5. CHUẨN UTF-8: Đảm bảo toàn bộ ký tự tiếng Việt hiển thị sạch sẽ theo chuẩn Unicode NFC.\n"
                "6. KHUNG TỌA ĐỘ BỐ CỤC (BOUNDING BOXES): Tại đầu trang, chèn một khối ```layout_json "
                "chứa danh sách các khối trên trang với tọa độ chuẩn hóa box_2d [ymin, xmin, ymax, xmax] (thang đo 0 đến 1000):\n"
                "   - 'header': Quốc hiệu, tiêu ngữ, tên cơ quan, số hiệu văn bản (đỉnh trang).\n"
                "   - 'title': Tiêu đề văn bản (THÔNG BÁO, QUYẾT ĐỊNH, QUY ĐỊNH...).\n"
                "   - 'table': Vùng bao quanh toàn bộ bảng số liệu.\n"
                "   - 'list': Danh sách gạch đầu dòng, danh sách hồ sơ, Nơi nhận...\n"
                "   - 'text': Các đoạn văn bản thông thường, căn cứ pháp lý.\n"
                "   - 'signature': Vùng con dấu đỏ và chữ ký của lãnh đạo.\n"
                "Ví dụ mẫu đầu trang:\n"
                "```layout_json\n"
                "[\n"
                "  {\"label\": \"header\", \"box_2d\": [40, 80, 160, 920], \"snippet\": \"BỘ GIÁO DỤC...\"},\n"
                "  {\"label\": \"title\", \"box_2d\": [180, 180, 240, 820], \"snippet\": \"THÔNG BÁO...\"},\n"
                "  {\"label\": \"table\", \"box_2d\": [320, 80, 480, 920], \"snippet\": \"STT | Mã ngành...\"}\n"
                "]\n"
                "```\n"
                "[Tiếp theo là toàn bộ nội dung Markdown chi tiết của trang]\n"
            )

            if is_ollama:
                payload = {
                    "model": self.model_name,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                            "images": [b64_data],
                        }
                    ],
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 8192,
                    },
                    "stream": False,
                }
            else:
                payload = {
                    "model": self.model_name,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": data_url},
                                },
                            ],
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 8192,
                }

            logger.info(
                "Gửi Trang %d/%d (%s) tới Vision OCR (%s @ %s)",
                p_num,
                len(page_images),
                filename,
                self.model_name,
                endpoint,
            )

            async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
                resp = await client.post(endpoint, json=payload, headers=headers)

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
                    f"Vision OCR API error ({resp.status_code}): {err_msg}"
                )

            data = resp.json()
            if is_ollama:
                extracted_page_raw = data.get("message", {}).get("content") or ""
            else:
                choices = data.get("choices") or []
                if not choices:
                    raise RuntimeError(f"Vision OCR không trả về kết quả cho Trang {p_num}.")
                extracted_page_raw = choices[0].get("message", {}).get("content") or ""
            clean_text, layout_blks = self._parse_page_layout_and_markdown(extracted_page_raw, p_num)

            # Fallback to semantic partition if model didn't emit layout_json
            if not layout_blks and clean_text:
                layout_blks = self._semantic_markdown_partition(clean_text, p_num)

            words = clean_text.split()
            lines = [line for line in clean_text.splitlines() if line.strip()]
            has_tables = any(
                line.strip().startswith("|") and line.strip().endswith("|") for line in lines
            )

            pages_out.append({
                "page_number": p_num,
                "extracted_text": clean_text,
                "confidence": 0.98 if clean_text else 0.50,
                "word_count": len(words),
                "line_count": len(lines),
                "has_tables": has_tables,
                "blocks": layout_blks,
            })
            if clean_text:
                all_text.append(f"<!-- Trang {p_num} -->\n\n{clean_text}")

        raw_joined = "\n\n---\n\n".join(all_text)
        from app.modules.ocr.cleaner import post_process_ocr_output

        cleaned_text, cleaned_pages = post_process_ocr_output(raw_joined, pages_out)

        return {
            "engine_used": self.name,
            "total_pages": len(cleaned_pages or pages_out),
            "overall_confidence": 0.98,
            "pages": cleaned_pages or pages_out,
            "raw_text": cleaned_text,
        }

    @staticmethod
    def _parse_page_layout_and_markdown(
        raw_page_content: str, page_number: int
    ) -> tuple[str, list[dict[str, Any]]]:
        """Extract layout_json bounding boxes from page content and clean up pure Markdown."""
        layout_blocks: list[dict[str, Any]] = []
        clean_text = raw_page_content

        m = re.search(r"```(?:layout_json|json)\s*\n([\s\S]*?)\n```", raw_page_content)
        if m:
            json_str = m.group(1).strip()
            try:
                data = json.loads(json_str)
                if isinstance(data, list):
                    for item in data:
                        box = item.get("box_2d")
                        if (
                            isinstance(box, (list, tuple))
                            and len(box) == 4
                            and all(isinstance(v, (int, float)) for v in box)
                        ):
                            ymin, xmin, ymax, xmax = [float(v) for v in box]
                            lbl = str(item.get("label") or "text").strip().lower()
                            if lbl not in {"header", "title", "table", "list", "text", "signature"}:
                                lbl = "text"
                            top = max(0.0, min(100.0, round(ymin / 10.0, 1)))
                            left = max(0.0, min(100.0, round(xmin / 10.0, 1)))
                            w_pct = max(1.0, min(100.0 - left, round((xmax - xmin) / 10.0, 1)))
                            h_pct = max(1.0, min(100.0 - top, round((ymax - ymin) / 10.0, 1)))
                            snippet = str(item.get("snippet") or item.get("text") or item.get("label"))[:160]

                            layout_blocks.append({
                                "type": lbl,
                                "label": lbl,
                                "coordinates": {
                                    "x": left,
                                    "y": top,
                                    "width": w_pct,
                                    "height": h_pct,
                                },
                                "content_snippet": snippet,
                                "confidence": 0.98 if lbl in ("table", "signature") else 0.95,
                            })
            except Exception as parse_err:
                logger.debug("Failed parsing layout_json on page %d: %s", page_number, parse_err)
            clean_text = (raw_page_content[:m.start()] + raw_page_content[m.end():]).strip()

        return clean_text, layout_blocks

    @staticmethod
    def _semantic_markdown_partition(text: str, page_number: int) -> list[dict[str, Any]]:
        """Fallback thông minh: phân tích Markdown thực tế để phân chia vùng layout."""
        blocks: list[dict[str, Any]] = []
        raw_paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if not raw_paragraphs:
            return []

        total_p = len(raw_paragraphs)
        cur_y = 6.0

        for idx, p in enumerate(raw_paragraphs):
            lines = [line.strip() for line in p.splitlines() if line.strip()]
            first_line = lines[0] if lines else ""
            first_line_upper = first_line.upper()

            is_table = any(line.startswith("|") and line.endswith("|") for line in lines)
            is_header = (
                page_number == 1
                and idx == 0
                and (
                    "CỘNG HÒA XÃ HỘI" in p.upper()
                    or "BỘ GIÁO DỤC" in p.upper()
                    or "ĐẠI HỌC QUY NHƠN" in p.upper()
                )
            )
            is_title = (
                any(
                    kw in first_line_upper
                    for kw in [
                        "THÔNG BÁO",
                        "QUYẾT ĐỊNH",
                        "QUY ĐỊNH",
                        "KẾ HOẠCH",
                        "PHƯƠNG ÁN",
                        "ĐỀ ÁN",
                    ]
                )
                or (first_line.startswith("#") and idx < 3)
            )
            is_sig = (
                idx >= total_p - 2
                and any(
                    kw in p.upper()
                    for kw in [
                        "HIỆU TRƯỞNG",
                        "PHÓ HIỆU TRƯỞNG",
                        "TRƯỞNG PHÒNG",
                        "ĐÃ KÝ",
                        "CHỮ KÝ",
                        "CON DẤU",
                    ]
                )
            )
            is_list = (
                not is_table
                and not is_header
                and not is_title
                and any(
                    first_line.lstrip().startswith(m)
                    for m in ("-", "*", "+", "•", "1.", "2.", "a)", "b)")
                )
            )

            if is_table:
                lbl = "table"
                bh = min(45.0, max(12.0, len(lines) * 3.5))
                bx = 10.0
                bw = 80.0
            elif is_header:
                lbl = "header"
                bx = 8.0
                bw = 84.0
                bh = 12.0
            elif is_title:
                lbl = "title"
                bx = 15.0
                bw = 70.0
                bh = min(10.0, max(4.0, len(lines) * 2.8))
            elif is_sig:
                lbl = "signature"
                bx = 52.0
                bw = 38.0
                bh = min(22.0, max(10.0, len(lines) * 3.0))
            elif is_list:
                lbl = "list"
                bx = 10.0
                bw = 80.0
                bh = min(35.0, max(5.0, len(lines) * 2.5))
            else:
                lbl = "text"
                bx = 10.0
                bw = 80.0
                bh = min(25.0, max(4.0, len(lines) * 2.2))

            by = min(92.0, round(cur_y, 1))
            blocks.append({
                "type": lbl,
                "label": lbl,
                "coordinates": {
                    "x": bx,
                    "y": by,
                    "width": bw,
                    "height": min(round(bh, 1), round(98.0 - by, 1)),
                },
                "content_snippet": p[:160],
                "confidence": 0.98 if lbl in ("table", "signature") else 0.92,
            })
            cur_y += bh + 2.0
            cur_y = min(92.0, cur_y)

        return blocks


class QwenOCRAdapter(OpenAIVisionOCRAdapter):
    """Backwards-compatible subclass specifically named for Qwen-VL."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model_name=model_name or "qwen3-vl:8b",
            base_url=base_url,
            adapter_name="qwen_ocr",
        )

