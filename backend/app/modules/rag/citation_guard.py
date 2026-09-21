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

            meta = c.metadata or {}
            source_pages = meta.get("source_pages")
            if not source_pages and c.page_number:
                source_pages = [c.page_number]
            entity_key = meta.get("entity_key")

            citations.append(
                Citation(
                    source_id=c.document_id,
                    title=title,
                    section=c.section,
                    page_number=c.page_number,
                    quote=quote,
                    source_pages=source_pages,
                    entity_key=entity_key,
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
        has_substantive_content = any(
            kw in answer_lower
            for kw in [
                "triệu",
                "học phí",
                "điểm chuẩn",
                "điểm trúng tuyển",
                "chỉ tiêu",
                "phương thức",
                "quy định",
                "điều ",
                "khoản ",
                "tín chỉ",
                "chương trình",
            ]
        )
        if not has_substantive_content and any(msg in answer_lower for msg in [
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

    def audit_claim_citations(
        self,
        answer: str,
        citations: list[Citation],
        facts_used: list[dict] | None = None,
    ) -> dict:
        """Audit claim-evidence grounding alignment between generated answer and citations/facts."""
        if not answer.strip():
            return {
                "is_grounded": False,
                "citation_coverage": 0.0,
                "has_citations": False,
                "facts_count": 0,
                "issues": ["Câu trả lời rỗng."],
            }

        # Safe refusal is 100% compliant with No-Answer policy
        answer_lower = answer.lower()
        if any(msg in answer_lower for msg in [
            "thông tin này hiện chưa có",
            "chưa có trong tài liệu chính thức",
            "chưa có dữ liệu chính thức",
            "vui lòng liên hệ hotline",
            "vui lòng liên hệ ban tư vấn",
            "vui lòng liên hệ phòng đào tạo",
            "hiện không đào tạo",
        ]):
            return {
                "is_grounded": True,
                "citation_coverage": 1.0,
                "has_citations": len(citations) > 0,
                "is_refusal": True,
                "facts_count": len(facts_used or []),
                "issues": [],
            }

        # Check citations presence
        has_citations = len(citations) > 0
        has_facts = bool(facts_used and len(facts_used) > 0)

        issues: list[str] = []
        if not has_citations and not has_facts:
            issues.append("Câu trả lời chứa dữ liệu thực tế nhưng không có bất kỳ trích dẫn hoặc bảng facts nào đính kèm.")

        # Check if citations have source_pages
        citations_with_pages = [c for c in citations if c.source_pages or c.page_number]
        page_coverage = len(citations_with_pages) / len(citations) if citations else (1.0 if has_facts else 0.0)

        is_grounded = (has_citations or has_facts) and len(issues) == 0

        return {
            "is_grounded": is_grounded,
            "citation_coverage": round(page_coverage, 2),
            "has_citations": has_citations,
            "citations_count": len(citations),
            "facts_count": len(facts_used or []),
            "issues": issues,
        }


citation_guard = CitationGuard()
