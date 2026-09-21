"""Answer Composer & AnswerFormatPlanner — Dynamic Formatting & Style Enforcement."""

from __future__ import annotations

import re

SYSTEM_PROMPT_TEMPLATE = """Bạn là Trợ lý AI Thông minh của Trường Đại học Quy Nhơn (QNU.AI).
Phong cách giao tiếp:
- Xưng hô 'mình' và gọi người dùng là 'bạn'. Giọng văn ấm áp, nhiệt tình, lịch sự, rõ ràng và đi thẳng vào trọng tâm.
- BÁM SÁT TRỌNG TÂM CÂU HỎI: Chỉ trả lời đúng và đủ khía cạnh người dùng hỏi. Tuyệt đối không tự ý mở rộng sang các chủ đề khác (như học phí, điểm chuẩn, lệ phí, ký túc xá) nếu câu hỏi không yêu cầu.
- Trả lời CHÍNH XÁC dựa trên tài liệu ngữ cảnh được cung cấp bên dưới.
- Nếu câu hỏi yêu cầu các thông số, điều kiện, mốc thời gian, hãy trích xuất dưới dạng bảng hoặc gạch đầu dòng rõ ràng.
- Tuyệt đối KHÔNG suy diễn hoặc bịa đặt số liệu ngoài tài liệu được cung cấp.
- TUYỆT ĐỐI KHÔNG viết các câu hỏi tu từ đóng ở cuối bài như: "Bạn có muốn mình chia sẻ thêm về...", "Bạn có quan tâm đến...".
- GỢI Ý CÂU HỎI TIẾP THEO: Ở cuối câu trả lời, hãy đề xuất đúng 2 câu hỏi cụ thể liên quan để người dùng tra cứu tiếp, định dạng theo khối sau (hệ thống sẽ tự động bóc tách thành nút bấm tương tác):
[GỢI Ý]:
- "Câu hỏi cụ thể liên quan 1?"
- "Câu hỏi cụ thể liên quan 2?"
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
    r"(?:\n\s*)*(?:\[GỢI Ý(?:\s+CÂU HỎI TIẾP THEO)?\]:?|💡\s*(?:Gợi ý|Câu hỏi bạn có thể quan tâm)[^:\n]*:?|Nếu bạn cần hỗ trợ thêm, bạn có thể tham khảo 2 câu hỏi sau:?|Bạn có thể muốn tìm hiểu thêm:?)\s*\n([\s\S]*)$",
    re.IGNORECASE,
)


def extract_suggested_questions(raw_answer: str) -> tuple[str, list[str]]:
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

        # Parse bullet lines or numbered lines
        for line in block_text.splitlines():
            line_clean = line.strip()
            # Remove leading bullets -, *, 1., 2.
            line_clean = (
                re.sub(r"^[-*•\d.]+\s*", "", line_clean).strip().strip('"').strip("'")
            )
            if (
                line_clean
                and len(line_clean) > 8
                and (
                    line_clean.endswith("?")
                    or "bao nhiêu" in line_clean
                    or "thế nào" in line_clean
                    or "gì" in line_clean
                )
            ):
                suggestions.append(line_clean)

        if suggestions:
            # Also clean any leftover repetitive question before the block
            for pattern in _REPETITIVE_TRAIL_PATTERNS:
                body_text = pattern.sub("", body_text).strip()
            return body_text, suggestions[:3]

    # 2. If no explicit block, check if there's a passive trailing question to convert
    for pattern in _REPETITIVE_TRAIL_PATTERNS:
        trail_match = pattern.search(text)
        if trail_match:
            trail_str = trail_match.group(0).strip()
            body_text = text[: trail_match.start()].strip()

            lower_trail = trail_str.lower()
            converted: list[str] = []
            if "điểm chuẩn" in lower_trail:
                converted.append("Điểm chuẩn các năm gần nhất của ngành này là bao nhiêu?")
            if "phương thức" in lower_trail:
                converted.append("Ngành này áp dụng những phương thức xét tuyển nào?")
            if "chỉ tiêu" in lower_trail:
                converted.append("Chỉ tiêu tuyển sinh năm 2026 của ngành này là bao nhiêu?")
            if "học phí" in lower_trail or "học bổng" in lower_trail:
                converted.append("Mức học phí và chính sách học bổng của ngành này ra sao?")
            if "tổ hợp" in lower_trail or "môn" in lower_trail:
                converted.append("Tổ hợp môn xét tuyển của ngành này gồm những môn nào?")

            if converted:
                return body_text, converted[:2]
            return body_text, []

    return text, []


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
