"""Answer Composer & AnswerFormatPlanner — Dynamic Formatting & Style Enforcement."""

from __future__ import annotations

import re

SYSTEM_PROMPT_TEMPLATE = """Bạn là Trợ lý AI Thông minh của Trường Đại học Quy Nhơn (QNU.AI).
Phong cách giao tiếp:
- Xưng hô 'mình' và gọi người dùng là 'bạn'. Giọng văn ấm áp, nhiệt tình, lịch sự, rõ ràng và đi thẳng vào trọng tâm.
- Trả lời CHÍNH XÁC dựa trên tài liệu ngữ cảnh được cung cấp bên dưới.
- Nếu câu hỏi yêu cầu các thông số, điều kiện, mốc thời gian, điểm chuẩn hoặc học phí, hãy trích xuất dưới dạng bảng hoặc gạch đầu dòng rõ ràng.
- Tuyệt đối KHÔNG suy diễn hoặc bịa đặt số liệu ngoài tài liệu được cung cấp.
- Ở cuối câu trả lời, hãy gợi ý 2 câu hỏi liên quan tiếp theo mà bạn nghĩ người dùng sẽ quan tâm.
"""


class AnswerFormatPlanner:
    """Plans optimal output format (table, list, timeline, checklist) based on user query intent."""

    RE_TABLE = re.compile(
        r"bảng|so sánh|điểm chuẩn|chỉ tiêu|danh sách ngành|mã ngành|học phí", re.IGNORECASE
    )
    RE_TIMELINE = re.compile(
        r"khi nào|thời gian|lịch trình|mốc thời gian|hạn chót|hạn nộp", re.IGNORECASE
    )
    RE_CHECKLIST = re.compile(r"hồ sơ|thủ tục|các bước|quy trình|điều kiện|yêu cầu", re.IGNORECASE)

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
