"""Answer Composer & AnswerFormatPlanner — Dynamic Formatting & Style Enforcement."""

from __future__ import annotations

import re

SYSTEM_PROMPT_TEMPLATE = """Bạn là Trợ lý AI Thông minh của Trường Đại học Quy Nhơn (QNU.AI).
Phong cách giao tiếp:
- Xưng hô 'mình' và gọi người dùng là 'bạn'. Giọng văn ấm áp, nhiệt tình, lịch sự, rõ ràng và đi thẳng vào trọng tâm.
- BÁM SÁT TRỌNG TÂM CÂU HỎI: Chỉ trả lời đúng và đủ khía cạnh người dùng hỏi. Tuyệt đối không tự ý mở rộng sang các chủ đề khác (như học phí, điểm chuẩn, lệ phí, ký túc xá) nếu câu hỏi không yêu cầu.
- CÂU HỎI TỔNG QUAN VỀ TRƯỜNG: Khi người dùng hỏi chung về trường (như "phương thức tuyển sinh của trường", "phương thức tuyển sinh năm 2026"), BẮT BUỘC trả lời về toàn trường (các phương thức 1, 2, 3, 4, 5). TUYỆT ĐỐI KHÔNG tự ý thu hẹp vào một ngành cụ thể từ lịch sử trò chuyện nếu người dùng không yêu cầu.
- TRA CỨU TỔ HỢP MÔN: Chỉ liệt kê những ngành/chuyên ngành có MỘT TỔ HỢP CỤ THỂ chứa ĐỦ TẤT CẢ các môn được hỏi. Tuyệt đối không ghép các môn từ nhiều tổ hợp khác nhau của cùng một ngành để trả lời (ví dụ: nếu một ngành có tổ hợp (Toán, Văn, Anh) và (Văn, Anh, Hóa), ngành đó KHÔNG có tổ hợp (Toán, Anh, Hóa), tuyệt đối không được liệt kê).
- TRÍCH XUẤT THEO THỰC THỂ: Khi tài liệu hoặc Bảng số liệu chứa nhiều ngành/đối tượng khác nhau, CHỈ ĐƯỢC trích xuất duy nhất thông tin của ngành/đối tượng mà người dùng đang hỏi. TUYỆT ĐỐI KHÔNG sao chép hoặc liệt kê thông tin của các ngành khác trong bảng.
- ĐỊNH DẠNG CHUẨN MỰC: Tuyệt đối KHÔNG sao chép nguyên văn các ký tự phân cách thô dạng `||||||` hoặc ký hiệu bảng vỡ từ tài liệu gốc. Trình bày nội dung sạch sẽ bằng văn phong sư phạm chuẩn mực, diễn giải rõ ràng các ký hiệu viết tắt hoặc con số (ví dụ: giải thích các phương thức 1, 2, 3, 4).
- Trả lời CHÍNH XÁC dựa trên tài liệu ngữ cảnh được cung cấp bên dưới.
- Nếu câu hỏi yêu cầu các thông số, điều kiện, mốc thời gian, hãy trích xuất dưới dạng bảng hoặc gạch đầu dòng rõ ràng.
- Tuyệt đối KHÔNG suy diễn hoặc bịa đặt số liệu ngoài tài liệu được cung cấp.
- TUYỆT ĐỐI KHÔNG viết các câu hỏi tu từ đóng ở cuối bài như: "Bạn có muốn mình chia sẻ thêm về...", "Bạn có quan tâm đến...".
- GỢI Ý CÂU HỎI TIẾP THEO (TƯƠNG TÁC 1-CLICK):
  + Ở cuối câu trả lời, hãy đề xuất đúng 2 câu hỏi cụ thể liên quan để hệ thống tạo nút bấm cho người dùng tra cứu tiếp.
  + QUY TẮC BẮT BUỘC: Câu hỏi gợi ý là NÚT BẤM DÀNH CHO NGƯỜI DÙNG CLICK ĐỂ HỎI TIẾP, do đó BẮT BUỘC PHẢI VIẾT DƯỚI GÓC ĐỘ NGƯỜI DÙNG HỎI TRỢ LÝ (User-Perspective Actionable Questions).
  + Ví dụ ĐÚNG:
    - "Tổ hợp môn xét tuyển ngành Công nghệ thông tin gồm những môn nào?"
    - "Chỉ tiêu tuyển sinh năm 2026 của trường là bao nhiêu?"
    - "Phương thức xét học bạ năm 2026 cần chuẩn bị hồ sơ gì?"
  + TUYỆT ĐỐI CẤM viết câu hỏi từ góc độ của bạn hỏi người dùng, cấm bắt đầu bằng: "Bạn có muốn...", "Bạn có quan tâm...", "Bạn có cần...", "Mình có thể...".
  + Định dạng bắt buộc theo khối:
[GỢI Ý]:
- "Câu hỏi gợi ý từ góc độ người dùng 1?"
- "Câu hỏi gợi ý từ góc độ người dùng 2?"
"""

_REPETITIVE_TRAIL_PATTERNS = [
    re.compile(
        r"(?:\n\s*)*Bạn có muốn\s+(?:mình\s+)?(?:chia sẻ|tìm hiểu|biết thêm|cho biết thêm|hỏi thêm)[^\n?]*\??\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:\n\s*)*Bạn có quan tâm đến[^\n?]*\??\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:\n\s*)*Bạn có muốn tìm hiểu thêm về[^\n?]*\??(?:\s*Hoặc bạn có quan tâm đến[^\n?]*\??)?\s*$",
        re.IGNORECASE,
    ),
]

_EXPLICIT_SUGGESTION_BLOCK = re.compile(
    r"(?:\n\s*)*(?:\**\[(?:GỢI\s*Ý|GIZ|GOI\s*Y|SUGGESTION|GỢI\s*Ý\s+CÂU\s*HỎI(?:\s+TIẾP\s+THEO)?)[^\]]*\]\**(?::|\.)?|💡\s*(?:Gợi ý|Câu hỏi bạn có thể quan tâm)[^:\n]*:?|Nếu bạn cần hỗ trợ thêm, bạn có thể tham khảo 2 câu hỏi sau:?|Bạn có thể muốn tìm hiểu thêm:?)\s*([\s\S]*)$",
    re.IGNORECASE,
)

_TRAILING_TAG_PATTERN = re.compile(
    r"(?:\n\s*)*\**\[[A-Za-zÀ-ỹ0-9_\s]{2,20}\]\**(?::|\.)?\s*$",
    re.IGNORECASE,
)


def _clean_suggestion_candidate(raw: str) -> str:
    """Strip bullets, brackets, quotes and trailing separators, keeping terminal ?."""
    cleaned = raw.strip()
    cleaned = re.sub(r"^[\s\-\*\•\d\.\)\(\[\]\"\'“”]+", "", cleaned).strip()
    cleaned = re.sub(r"[\s\]\"\'“”,;]+$", "", cleaned).strip()
    return cleaned


def _is_question_like(text: str) -> bool:
    return bool(
        text
        and len(text) > 8
        and (
            text.endswith("?")
            or "bao nhiêu" in text
            or "thế nào" in text
            or "gì" in text
        )
    )


def convert_or_filter_suggestion_perspective(candidate: str) -> str | None:
    """Convert assistant-perspective suggestion ('Bạn có muốn...') to user-perspective, or filter it out."""
    if not candidate:
        return None

    cleaned = _clean_suggestion_candidate(candidate)
    if not cleaned or len(cleaned) < 6:
        return None

    lower = cleaned.lower()

    # If it is already a direct user-facing question (not starting with assistant-ask-user patterns)
    inverted_pattern = re.compile(
        r"^(?:bạn\s+có\s+(?:muốn|thể\s+muốn|quan\s+tâm|cần)|mình\s+có\s+thể|nếu\s+bạn\s+muốn)\b",
        re.IGNORECASE,
    )
    if not inverted_pattern.search(cleaned):
        if not cleaned.endswith("?") and not cleaned.endswith("."):
            cleaned = f"{cleaned}?"
        return cleaned

    # Otherwise, it's an inverted assistant question: try to transform it to an actionable user question
    if "tổ hợp" in lower or "môn" in lower:
        major_match = re.search(
            r"\b(?:ngành|chuyên ngành)\s+([A-ZÀ-Ỹa-zà-ỹ\s]{3,40})\b", cleaned, re.IGNORECASE
        )
        if major_match:
            major_cand = major_match.group(1).strip()
            major_cand = re.sub(
                r"\b(?:không|nhỉ|ạ|năm\s+\d{4}|ở\s+đâu|như\s+thế\s+nào).*$",
                "",
                major_cand,
                flags=re.IGNORECASE,
            ).strip()
            if len(major_cand) >= 3 and not any(
                p in major_cand.lower() for p in ("cụ thể", "nào", "gì", "bất kỳ", "khác")
            ):
                return f"Tổ hợp môn xét tuyển của ngành {major_cand.title()} gồm những môn nào?"
        return "Các ngành của trường xét tuyển những tổ hợp môn nào?"

    if "phương thức" in lower or "xét tuyển" in lower:
        if "học bạ" in lower:
            return "Phương thức xét học bạ năm 2026 áp dụng như thế nào?"
        if "đánh giá năng lực" in lower or "đgnl" in lower:
            return "Phương thức xét điểm đánh giá năng lực áp dụng như thế nào?"
        return "Trường Đại học Quy Nhơn áp dụng những phương thức tuyển sinh nào năm 2026?"

    if "học phí" in lower:
        return "Mức học phí năm 2026 của trường là bao nhiêu?"

    if "học bổng" in lower:
        return "Chính sách học bổng của trường như thế nào?"

    if "chỉ tiêu" in lower:
        return "Chỉ tiêu tuyển sinh năm 2026 của trường là bao nhiêu?"

    if "điểm chuẩn" in lower:
        return "Điểm chuẩn các năm gần nhất của trường như thế nào?"

    if "ký túc xá" in lower:
        return "Điều kiện và thủ tục đăng ký ký túc xá như thế nào?"

    # Try generic extraction: e.g. "Bạn có muốn tìm hiểu về X không?" -> "Thông tin về X như thế nào?"
    m_topic = re.search(
        r"(?:chia sẻ|tìm hiểu|biết thêm|hỏi thêm)?\s*(?:về|thông tin về)\s+([^?]+?)(?:\s+không|\?|$)",
        cleaned,
        re.IGNORECASE,
    )
    if m_topic:
        topic = m_topic.group(1).strip()
        topic = re.sub(r"\b(?:của\s+)?ngành\s+cụ\s+thể\s+nào\b", "các ngành", topic, flags=re.IGNORECASE)
        if len(topic) >= 4 and not any(w in topic.lower() for w in ("bạn", "mình")):
            return f"Thông tin về {topic} như thế nào?"

    # Cannot safely convert: return None so it is completely excluded
    return None


def _extract_candidates_from_block(block_text: str) -> list[str]:
    """Parse bullet lists, single-line JSON arrays and semicolon-separated suggestions."""
    block = (block_text or "").strip()
    if not block:
        return []
    raw_candidates: list[str] = []

    # 1. Quoted questions first: handles inline JSON arrays like ["A?", "B?"]
    for quoted in re.findall(r'"([^"\n]{8,}?)"', block):
        cleaned = _clean_suggestion_candidate(quoted)
        if _is_question_like(cleaned):
            raw_candidates.append(cleaned)
    for quoted in re.findall(r"'([^'\n]{8,}?)'", block):
        cleaned = _clean_suggestion_candidate(quoted)
        if _is_question_like(cleaned) and cleaned not in raw_candidates:
            raw_candidates.append(cleaned)

    # 2. Bullet / numbered lines, each possibly holding several ;-separated items
    if not raw_candidates:
        for line in block.splitlines():
            for part in re.split(r"[;\n]+", line):
                cleaned = _clean_suggestion_candidate(part)
                if _is_question_like(cleaned):
                    raw_candidates.append(cleaned)

    # 3. Filter and convert perspective for every candidate
    final_candidates: list[str] = []
    for cand in raw_candidates:
        processed = convert_or_filter_suggestion_perspective(cand)
        if processed and processed not in final_candidates:
            final_candidates.append(processed)

    return final_candidates


def _is_too_similar_to_query(suggestion: str, query: str | None) -> bool:
    """Check whether a suggestion is an echo of the user's current question."""
    if not query:
        return False
    from app.modules.workflows.nodes.query_rewrite_node import _unaccent
    s_words = {_unaccent(w) for w in re.findall(r"\w+", suggestion.lower()) if len(w) >= 2}
    q_words = {_unaccent(w) for w in re.findall(r"\w+", query.lower()) if len(w) >= 2}
    if not s_words or not q_words:
        return False
    overlap = len(s_words & q_words)
    return (overlap / len(s_words)) >= 0.70 or (overlap / len(q_words)) >= 0.70


def extract_suggested_questions(
    raw_answer: str, current_query: str | None = None
) -> tuple[str, list[str]]:
    """Extract follow-up suggestions from raw LLM answer and clean trailing boilerplate."""
    if not raw_answer:
        return "", []

    text = raw_answer.strip()
    suggestions: list[str] = []

    # 1. Try to find an explicit suggestion block at the bottom
    match = _EXPLICIT_SUGGESTION_BLOCK.search(text)
    if match:
        block_text = match.group(1).strip()
        body_text = text[: match.start()].strip()

        candidates = _extract_candidates_from_block(block_text)
        suggestions = [
            c for c in candidates
            if not _is_too_similar_to_query(c, current_query)
        ]

        # Also clean any leftover repetitive question before the block
        for pattern in _REPETITIVE_TRAIL_PATTERNS:
            body_text = pattern.sub("", body_text).strip()
        # Clean any trailing leftover header markers e.g. [GIZ]:, [GỢI Ý]:
        body_text = _TRAILING_TAG_PATTERN.sub("", body_text).strip()

        if suggestions:
            return body_text, suggestions[:3]
        return body_text, []

    # 2. If no explicit block, check if there's a passive trailing question to convert
    for pattern in _REPETITIVE_TRAIL_PATTERNS:
        trail_match = pattern.search(text)
        if trail_match:
            trail_str = trail_match.group(0).strip()
            body_text = text[: trail_match.start()].strip()
            body_text = _TRAILING_TAG_PATTERN.sub("", body_text).strip()

            lower_trail = trail_str.lower()
            converted: list[str] = []
            if "điểm chuẩn" in lower_trail:
                converted.append("Điểm chuẩn các năm gần nhất của trường như thế nào?")
            if "phương thức" in lower_trail:
                converted.append("Trường áp dụng những phương thức tuyển sinh nào?")
            if "chỉ tiêu" in lower_trail:
                converted.append("Chỉ tiêu tuyển sinh năm 2026 của trường là bao nhiêu?")
            if "học phí" in lower_trail or "học bổng" in lower_trail:
                converted.append("Mức học phí và chính sách học bổng của trường ra sao?")
            if "tổ hợp" in lower_trail or "môn" in lower_trail:
                converted.append("Các ngành của trường xét tuyển những tổ hợp môn nào?")

            filtered_converted = [
                c for c in converted
                if not _is_too_similar_to_query(c, current_query)
            ]
            if filtered_converted:
                return body_text, filtered_converted[:2]
            return body_text, []

    body_text = _TRAILING_TAG_PATTERN.sub("", text).strip()
    return body_text, []


def sanitize_rag_answer(raw_answer: str, target_entity: str | None = None) -> str:
    """Clean raw OCR pipe artifacts, broken table syntax, and prevent multi-major verbatim table dumps."""
    if not raw_answer:
        return ""

    text = raw_answer.strip()

    # 1. Handle verbatim multi-major dumps if target_entity is known
    # e.g. '|||||| (Toán, Anh, Sử) || 31 | 7380101 | Luật ... || 36 | 7480201 | Công nghệ thông tin ...'
    if target_entity:
        entity_clean = target_entity.strip().lower()
        major_row_pattern = re.compile(
            r"(?:\|\|\s*\d+\s*\|\s*\d{7}\s*\|\s*[^|]+?\s*\|\s*[\d,\s]+\s*\|\|[^\n|]+(?=\|\|\s*\d+\s*\||$))",
            re.DOTALL,
        )
        rows = major_row_pattern.findall(text)
        if len(rows) > 1:
            matching_rows = [r for r in rows if entity_clean in r.lower()]
            if matching_rows:
                intro_match = re.match(r"^(.*?)(?:\|{2,}.*)$", text, re.DOTALL)
                intro = intro_match.group(1).strip() if intro_match else ""

                row = matching_rows[0]
                parts = [p.strip() for p in re.split(r"\|+", row) if p.strip()]
                subject_hints = (
                    "toán", "văn", "anh", "lý", "hóa", "sinh", "sử", "địa",
                    "tin", "giáo dục", "công nghệ",
                )
                all_parens = re.findall(r"\(([^)]+)\)", row)
                combos = [c.strip() for c in all_parens if any(h in c.lower() for h in subject_hints)]

                methods = ""
                for p in parts:
                    if re.match(r"^[\d,\s]+$", p) and len(p) <= 10 and ("," in p or p in ("1", "2", "3", "4")):
                        methods = p
                        break

                formatted_lines = []
                if intro:
                    formatted_lines.append(intro)
                else:
                    formatted_lines.append(
                        "Chào bạn! Dựa trên Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn, "
                        "thông tin xét tuyển chi tiết như sau:"
                    )

                formatted_lines.append(f"\n**Ngành**: {target_entity.title()}")
                if methods:
                    formatted_lines.append(f"- **Phương thức xét tuyển**: Áp dụng cho các Phương thức {methods}")
                if combos:
                    formatted_lines.append("- **Các tổ hợp môn xét tuyển**:")
                    for c in combos:
                        formatted_lines.append(f"  * ({c.strip()})")

                return "\n".join(formatted_lines).strip()

    # 2. General cleanup for raw OCR pipes
    text = re.sub(r"\|{3,}", "", text)
    text = re.sub(r"(?m)^\s*\|{2,}\s*", "", text)
    text = re.sub(r"(?m)\s*\|{2,}\s*$", "", text)

    # Remove isolated trailing pipe at the end of a non-table line
    cleaned_lines = []
    for line in text.split("\n"):
        stripped = line.rstrip()
        if not stripped.startswith("|") and stripped.endswith(" |"):
            cleaned_lines.append(stripped[:-2].rstrip())
        elif not stripped.startswith("|") and stripped.endswith("|") and not stripped.startswith("#"):
            cleaned_lines.append(stripped[:-1].rstrip())
        else:
            cleaned_lines.append(line)
    text = "\n".join(cleaned_lines)

    # 3. Clean any trailing leftover header markers e.g. [GIZ]:, [GỢI Ý]:
    text = _TRAILING_TAG_PATTERN.sub("", text).strip()

    return text.strip()


class AnswerFormatPlanner:
    """Plans optimal output format (table, list, timeline, checklist) based on user query intent."""

    RE_TABLE = re.compile(
        r"bảng|so sánh|điểm chuẩn|chỉ tiêu|danh sách|mã ngành|mã số|học phí|"
        r"giáo trình|tài liệu|ma trận|chuẩn đầu ra|thống kê|liệt kê",
        re.IGNORECASE,
    )
    RE_TIMELINE = re.compile(
        r"khi nào|thời gian|lịch trình|mốc thời gian|hạn chót|hạn nộp|"
        r"ngày ban hành|ngày hiệu lực|hạn hoàn thành",
        re.IGNORECASE,
    )
    RE_CHECKLIST = re.compile(
        r"hồ sơ|thủ tục|các bước|quy trình|điều kiện|yêu cầu|"
        r"hướng dẫn|thủ tục mượn|điều khoản",
        re.IGNORECASE,
    )

    def plan_format(self, query: str, context_has_table: bool = False) -> str:
        """Decide the best answer presentation format."""
        if context_has_table or self.RE_TABLE.search(query):
            return "markdown_table"
        if self.RE_TIMELINE.search(query):
            return "timeline"
        if self.RE_CHECKLIST.search(query):
            return "checklist"
        return "bullet_list"

    def get_format_instructions(
        self,
        format_type: str,
        target_entity: str | None = None,
        is_combo_query: bool = False,
    ) -> str:
        """Generate clear presentation rules for LLM based on format intent."""
        lines = ["CHỈ ĐẠO ĐỊNH DẠNG & TRÌNH BÀY:"]
        if is_combo_query:
            lines.append(
                "- Về tổ hợp môn xét tuyển: Trình bày danh sách gạch đầu dòng (-) rõ ràng từng tổ hợp môn kèm tên môn chi tiết. "
                "Ví dụ: `(Toán, Tiếng Anh, Vật lý)`.\n"
                "- Diễn giải các ký hiệu/con số phương thức nếu có (ví dụ: 'Áp dụng cho các Phương thức xét tuyển 1, 2, 3 và 4').\n"
                "- Tuyệt đối KHÔNG sao chép các ký tự phân cách thô `||` hoặc các ngành khác trong bảng."
            )
        elif format_type == "markdown_table":
            lines.append(
                "- Trình bày dữ liệu dưới dạng BẢNG MARKDOWN hoàn chỉnh, có dòng tiêu đề cột rõ ràng và căn chỉnh chuẩn (| Cột 1 | Cột 2 |).\n"
                "- Tuyệt đối KHÔNG viết các ký tự phân cách thô `||` dính liền nhau hoặc làm vỡ cấu trúc bảng."
            )
        elif format_type == "timeline":
            lines.append(
                "- Trình bày các mốc thời gian theo thứ tự thời gian tăng dần dạng danh sách hoặc bảng mốc thời gian rõ ràng."
            )
        elif format_type == "checklist":
            lines.append(
                "- Trình bày các bước hoặc điều kiện/thủ tục theo dạng checklist từng bước (Bước 1, Bước 2,... hoặc gạch đầu dòng có điều kiện tiên quyết)."
            )
        else:
            lines.append(
                "- Trình bày thành danh sách gạch đầu dòng (-) mạch lạc, có câu mở đầu thân thiện và đi thẳng vào đối tượng được hỏi."
            )

        if target_entity:
            lines.append(
                f"- Trọng tâm thực thể: Chỉ giải đáp cho '{target_entity}'. Không sao chép các đối tượng khác ngoài phạm vi."
            )

        return "\n".join(lines)

    def assemble_prompt(
        self,
        query: str,
        context_chunks: list[str],
        fact_table: str = "",
        custom_system_prompt: str | None = None,
    ) -> str:
        """Assemble full prompt with context and format instructions."""
        context_block = "\n\n---\n\n".join(context_chunks)
        if fact_table:
            context_block = f"### BẢNG SỰ THẬT CHÍNH XÁC (ƯU TIÊN TUYỆT ĐỐI):\n{fact_table}\n\n### TÀI LIỆU THAM KHẢO:\n{context_block}"

        prompt = (
            f"{custom_system_prompt or SYSTEM_PROMPT_TEMPLATE}\n\n"
            f"NGỮ CẢNH TÀI LIỆU:\n{context_block}\n\n"
            f"CÂU HỎI CỦA NGƯỜI DÙNG: {query}\n\n"
            f"CÂU TRẢ LỜI CỦA BẠN:"
        )
        return prompt


answer_format_planner = AnswerFormatPlanner()
