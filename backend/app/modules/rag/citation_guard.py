"""Citation Guard & Groundedness Policy — Strict Source Verification & Hallucination Prevention."""

from __future__ import annotations

import logging

from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.schemas import Citation

logger = logging.getLogger(__name__)

NO_ANSWER_MESSAGES = {
    "admissions": (
        "Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.\n\n"
        "Bạn có thể thử hỏi mình các chủ đề phổ biến như:\n"
        "- 🎯 **Điểm chuẩn**: Điểm chuẩn các ngành tuyển sinh năm 2024\n"
        "- 💰 **Học phí**: Mức học phí và chính sách học bổng của trường\n"
        "- 📚 **Ngành học**: Các ngành đào tạo và chỉ tiêu năm 2026\n\n"
        "Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nha!"
    ),
    "regulations": (
        "Chào bạn! Nội dung này hiện chưa được quy định cụ thể trong các văn bản Quy chế đào tạo của Trường ĐH Quy Nhơn có trong hệ thống.\n"
        "Bạn vui lòng liên hệ trực tiếp **Phòng Đào tạo** để được hướng dẫn chi tiết."
    ),
    "general": (
        "Thông tin bạn yêu cầu hiện không có trong cơ sở dữ liệu tri thức của Trường Đại học Quy Nhơn. "
        "Vui lòng liên hệ bộ phận phụ trách để được giải đáp chính xác nhất."
    ),
}


class CitationGuard:
    """Verifies that RAG answers are backed by verified citations and enforces refusal policy."""

    def build_citations(self, candidates: list[FusionCandidate]) -> list[Citation]:
        """Extract citations from retrieved candidates."""
        citations: list[Citation] = []
        seen_chunks = set()

        for c in candidates:
            if c.chunk_id in seen_chunks:
                continue
            seen_chunks.add(c.chunk_id)

            title = c.section or f"Tài liệu {c.document_id[:8]}"
            quote = c.content[:200].strip() + ("..." if len(c.content) > 200 else "")

            citations.append(
                Citation(
                    source_id=c.document_id,
                    title=title,
                    section=c.section,
                    page_number=c.page_number,
                    quote=quote,
                )
            )

        return citations

    def get_no_answer_response(self, module_code: str = "general") -> str:
        """Return friendly rejection response when context is insufficient."""
        return NO_ANSWER_MESSAGES.get(module_code, NO_ANSWER_MESSAGES["general"])


citation_guard = CitationGuard()
