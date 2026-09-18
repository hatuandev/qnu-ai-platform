"""Citation Guard & Groundedness Policy — Strict Source Verification & Hallucination Prevention."""

from __future__ import annotations

import logging
import re

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

ACADEMIC_STOPWORDS = {
    "sinh", "viên", "trường", "đại", "học", "quy", "nhơn", "được", "trong", "theo",
    "những", "các", "cho", "với", "của", "và", "hoặc", "khi", "thì", "tại", "này",
    "mỗi", "một", "hai", "ba", "bốn", "tối", "đa", "thiểu", "người", "thời",
    "gian", "thực", "hiện", "định", "có", "không", "phải", "để", "biết", "thêm",
    "chi", "tiết", "trực", "tiếp", "quý", "vị", "bạn", "chào", "xin", "cảm", "ơn",
    "liên", "hệ", "qua", "số", "điện", "thoại", "vui", "lòng", "năm",
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
            quote = c.content[:1500].strip() + ("..." if len(c.content) > 1500 else "")

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

    def filter_evidence_citations(
        self,
        citations: list[Citation],
        answer: str,
        min_overlap_words: int = 3,
    ) -> list[Citation]:
        """Filter candidate citations to only those whose quotes provide actual evidence used in the answer."""
        if not answer.strip() or not citations:
            return []

        answer_lower = answer.lower()
        if any(msg in answer_lower for msg in [
            "thông tin này hiện chưa có",
            "chưa có trong tài liệu chính thức",
            "chưa có dữ liệu chính thức",
            "vui lòng liên hệ hotline",
            "vui lòng liên hệ ban tư vấn",
            "vui lòng liên hệ phòng đào tạo",
        ]):
            return []

        answer_words = {
            w for w in re.findall(r"\b\w{2,}\b", answer_lower)
            if w not in ACADEMIC_STOPWORDS
        }
        filtered: list[Citation] = []

        for cite in citations:
            quote_text = cite.quote or ""
            if not quote_text:
                continue
            quote_words = {
                w for w in re.findall(r"\b\w{2,}\b", quote_text.lower())
                if w not in ACADEMIC_STOPWORDS
            }
            overlap = len(answer_words.intersection(quote_words))
            if overlap >= min_overlap_words:
                filtered.append(cite)

        return filtered

    def get_no_answer_response(self, module_code: str = "general") -> str:
        """Return friendly rejection response when context is insufficient."""
        return NO_ANSWER_MESSAGES.get(module_code, NO_ANSWER_MESSAGES["general"])


citation_guard = CitationGuard()
