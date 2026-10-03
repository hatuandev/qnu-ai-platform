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

_DEFAULT_GEMINI_OCR_MODEL = "gemini-3.1-flash-lite"


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
            "kèm theo Bounding Boxes bố cục trang chuẩn xác 100% theo các quy tắc bắt buộc sau:\n"
            "1. BẢO TOÀN NỘI DUNG & CHÍNH TẢ: Giữ nguyên 100% nội dung chữ, tiêu đề cấp mục (#, ##, ###), "
            "số hiệu văn bản, ngày tháng, họ tên, các điều khoản, ghi chú, con dấu và chữ ký. Nhận diện chính xác "
            "thuật ngữ hành chính, công nghệ và tài chính (ví dụ: 'chỉ số' không viết nhầm thành 'số chỉ', 'kinh phí', 'ký kết', "
            "'Trung tâm Số và Học liệu', mã số thuế, số tài khoản, tên ngân hàng).\n"
            "2. CẤM TUYỆT ĐỐI THẺ HTML THÔ (ZERO RAW HTML TAGS): Tuyệt đối KHÔNG sử dụng các thẻ HTML như "
            "<table>, <tr>, <td>, <hr>, <br>, <center>, <b>, <i> để dàn trang. 100% sử dụng Markdown GFM thuần khiết. "
            "Các khối Quốc hiệu, tiêu ngữ, số hiệu văn bản (đầu trang) và Nơi nhận, người ký (cuối trang) "
            "phải viết dưới dạng văn bản Markdown chuẩn (dùng in đậm **, in nghiêng *, danh sách -), "
            "tuyệt đối không bọc trong bảng HTML.\n"
            "3. BẢNG BIỂU CHUẨN GFM & PHẲNG HÓA DỮ LIỆU (FLATTEN ROWS): Mọi bảng biểu phải chuyển thành bảng Markdown "
            "với hàng tiêu đề và hàng phân cách '|:---|:---|' rõ ràng. Giữ nguyên vẹn toàn bộ các hàng và cột.\n"
            "   - NGUYÊN TẮC PHẲNG HÓA BẢNG HỌC PHÍ / CHỈ TIÊU: Đối với các bảng số liệu tuyển sinh, học phí, chỉ tiêu: "
            "nếu một ngành có nhiều phương án đào tạo (nhiều mức thời gian học, nhiều hình thức hoặc các mức học phí khác nhau), "
            "BẮT BUỘC PHẢI TÁCH THÀNH TỪNG HÀNG ĐỘC LẬP trong bảng (mỗi hàng chứa đầy đủ STT, Tên ngành, Khối ngành, Thời gian học, "
            "Hình thức đào tạo, Học phí toàn khóa). TUYỆT ĐỐI KHÔNG gộp nhiều mức học phí khác nhau vào cùng một ô bằng thẻ <br> hay dấu xuống dòng.\n"
            "   - ĐỐI VỚI BẢNG NHIỆM VỤ CÔNG VIỆC: Mỗi mục/nhiệm vụ (1.1, 1.2...) nằm trọn vẹn trong một hàng bảng duy nhất. "
            "Nếu có nhiều đoạn mô tả, hãy viết liền mạch trong ô mô tả bằng văn bản thuần.\n"
            "4. BẢNG BIỂU QUA NHIỀU TRANG (CROSS-PAGE TABLE & ZERO DATA LOSS): Khi một bảng kéo dài sang trang tiếp theo:\n"
            "   - TUYỆT ĐỐI KHÔNG ĐƯỢC BỎ SÓT BẤT KỲ HÀNG NÀO ở đầu trang tiếp theo! Kể cả khi ô STT hoặc Tên ngành ở đầu trang sau "
            "bị để trống trên bản in scan (do kế thừa từ mục của trang trước), BẮT BUỘC PHẢI GIỮ LẠI ĐẦY ĐỦ HÀNG ĐÓ và điền lại STT, Tên ngành tương ứng.\n"
            "   - Tại đầu trang tiếp theo, lặp lại hàng tiêu đề của bảng và hàng phân cách '|:---|:---|' để đảm bảo cú pháp GFM hợp lệ.\n"
            "   - TUYỆT ĐỐI KHÔNG chèn ký tự '---' vào giữa các hàng của một khối bảng biểu.\n"
            "5. CHỐNG BẺ ĐÔI TỪ QUA TRANG (NO WORD SPLITTING): Nếu từ ngữ hoặc câu văn bị ngắt dòng ở cuối trang "
            "(ví dụ: 'banner, giới' ở cuối trang trước và 'thiệu, hình ảnh' ở đầu trang sau), BẮT BUỘC phải hoàn tất trọn vẹn từ ngữ đó "
            "('banner, giới thiệu, hình ảnh...'), tuyệt đối không để từ tiếng Việt bị chặt đôi qua trang.\n"
            "6. PHÂN TÁCH TRANG CHUẨN XÁC: Đặt nhãn phân cách trang: <!-- Trang X --> tại đầu mỗi trang văn bản. "
            "Chỉ dùng '---' để phân cách giữa các trang văn bản thông thường bên ngoài bảng biểu.\n"
            "7. KHÔNG BỊA ĐẶT / KHÔNG TẮT: Tuyệt đối cấm tự ý tóm tắt, cắt xén, bỏ bớt hàng bảng hoặc phát sinh thông tin sai lệch.\n"
            "8. CHUẨN UTF-8: Đảm bảo toàn bộ ký tự tiếng Việt hiển thị sạch sẽ theo chuẩn Unicode NFC.\n"
            "9. KHUNG TỌA ĐỘ BỐ CỤC (BOUNDING BOXES): Tại đầu mỗi trang (ngay sau dòng <!-- Trang X -->), chèn một khối ```layout_json "
            "chứa danh sách các khối trên trang với tọa độ chuẩn hóa box_2d [ymin, xmin, ymax, xmax] (thang đo 0 đến 1000):\n"
            "   - 'header': Quốc hiệu, tiêu ngữ, tên cơ quan, số hiệu văn bản (đỉnh trang).\n"
            "   - 'title': Tiêu đề văn bản (THÔNG BÁO, QUYẾT ĐỊNH, QUY ĐỊNH...).\n"
            "   - 'table': Vùng bao quanh toàn bộ bảng số liệu (STT, ngành, học phí, chỉ tiêu...).\n"
            "   - 'list': Danh sách gạch đầu dòng, danh sách hồ sơ, Nơi nhận...\n"
            "   - 'text': Các đoạn văn bản thông thường, căn cứ pháp lý.\n"
            "   - 'signature': Vùng con dấu đỏ và chữ ký của lãnh đạo.\n"
            "Ví dụ mẫu đầu mỗi trang:\n"
            "<!-- Trang 1 -->\n"
            "```layout_json\n"
            "[\n"
            "  {\"label\": \"header\", \"box_2d\": [40, 80, 160, 920], \"snippet\": \"BỘ GIÁO DỤC...\"},\n"
            "  {\"label\": \"title\", \"box_2d\": [180, 180, 240, 820], \"snippet\": \"THÔNG BÁO...\"},\n"
            "  {\"label\": \"table\", \"box_2d\": [320, 80, 480, 920], \"snippet\": \"STT | Mã ngành...\"}\n"
            "]\n"
            "```\n"
            "[Tiếp theo là toàn bộ nội dung Markdown chi tiết của trang]\n"
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
        raw_page_chunks: list[tuple[int, str]] = []
        page_pattern = re.compile(r"<!--\s*Trang\s*(\d+)\s*-->", re.IGNORECASE)
        splits = page_pattern.split(extracted_raw)

        if len(splits) > 1:
            if splits[0].strip():
                raw_page_chunks.append((1, splits[0].strip()))
            for i in range(1, len(splits), 2):
                p_num = int(splits[i])
                p_text = splits[i + 1].strip() if i + 1 < len(splits) else ""
                p_text = re.sub(r"\n+---+\s*$", "", p_text).strip()
                raw_page_chunks.append((p_num, p_text))
        else:
            raw_pages_split = re.split(r"\n+---+\n+", extracted_raw)
            for idx, p_text in enumerate(raw_pages_split, start=1):
                clean_p = p_text.strip()
                if clean_p:
                    raw_page_chunks.append((idx, clean_p))

        if not raw_page_chunks:
            raw_page_chunks = [(1, extracted_raw)]

        # Process each page: extract layout_json bounding boxes and clean pure Markdown
        parsed_pages: list[tuple[int, str, list[dict[str, Any]]]] = []
        for p_num, raw_p_text in raw_page_chunks:
            clean_text, layout_blks = self._parse_page_layout_and_markdown(raw_p_text, p_num)
            parsed_pages.append((p_num, clean_text, layout_blks))

        geometry_by_page: dict[int, list[dict[str, Any]]] = {}
        for p_num, _, layout_blks in parsed_pages:
            if layout_blks:
                geometry_by_page[p_num] = layout_blks

        # Extract visual geometry using SmartLayoutDetector (PyMuPDF hybrid + OpenCV) if available
        # Only fallback if gemini layout blocks were not emitted
        missing_geom_pages = [p_num for p_num, _, _ in parsed_pages if p_num not in geometry_by_page]
        if missing_geom_pages:
            try:
                import pymupdf as fitz

                from app.modules.ocr.layout_detector import SmartLayoutDetector

                detector = SmartLayoutDetector()
                raw_pages_text = {p_num: text for p_num, text, _ in parsed_pages}

                if ext == ".pdf":
                    pdf = fitz.open(stream=content, filetype="pdf")
                    for p_num in missing_geom_pages:
                        if p_num <= len(pdf):
                            page = pdf[p_num - 1]
                            try:
                                page_txt = raw_pages_text.get(p_num) or page.get_text() or ""
                                regs = detector.detect_layout_regions(
                                    None,
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
            except Exception as exc:
                logger.debug("SmartLayoutDetector skipped in Gemini OCR adapter: %s", exc)

        # Fallback to Semantic Markdown Partitioning for any pages still missing geometry
        for p_num, text, _ in parsed_pages:
            if p_num not in geometry_by_page and text:
                geometry_by_page[p_num] = self._semantic_markdown_partition(text, p_num)

        pages_out: list[dict[str, Any]] = []
        all_text: list[str] = []

        for p_num, text, _ in parsed_pages:
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

        raw_joined = "\n\n---\n\n".join(all_text)
        from app.modules.ocr.cleaner import post_process_ocr_output

        cleaned_text, cleaned_pages = post_process_ocr_output(raw_joined, pages_out)

        return {
            "engine_used": self.name,
            "total_pages": len(cleaned_pages or pages_out),
            "overall_confidence": 0.99,
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
                import json
                data = json.loads(json_str)
                if isinstance(data, list):
                    for item in data:
                        box = item.get("box_2d")
                        if isinstance(box, (list, tuple)) and len(box) == 4 and all(isinstance(v, (int, float)) for v in box):
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
        """Fallback thông minh: phân tích Markdown thực tế để phân chia vùng layout, tuyệt đối không gán cứng."""
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

            is_table = any(l.startswith("|") and l.endswith("|") for l in lines)
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

