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
        "- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ\n"
        "- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo\n"
        "- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường\n\n"
        "Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!"
    ),
    "regulations": (
        "Chào bạn! Nội dung này hiện chưa được quy định cụ thể trong các văn bản Quy chế đào tạo của Trường ĐH Quy Nhơn có trong hệ thống.\n\n"
        "Bạn có thể thử tra cứu các chủ đề như:\n"
        "- **Tín chỉ & Học phần**: Đăng ký học phần, số tín chỉ tối đa, rút bớt học phần\n"
        "- **Xử lý học vụ**: Cảnh báo học tập, buộc thôi học, cách tính điểm tích lũy GPA\n"
        "- **Chuẩn đầu ra & Tốt nghiệp**: Chứng chỉ ngoại ngữ VSTEP, tin học và điều kiện xét tốt nghiệp\n\n"
        "Nếu cần giải quyết trường hợp cụ thể, bạn vui lòng liên hệ trực tiếp **Phòng Đào tạo** (Bàn tiếp sinh viên) để được hướng dẫn chi tiết nhé!"
    ),
    "library": (
        "Chào bạn! Hiện tại chưa tìm thấy giáo trình hoặc tài liệu này trong cơ sở dữ liệu Thư viện số Trường ĐH Quy Nhơn.\n\n"
        "Bạn có thể thử tra cứu:\n"
        "- **Giáo trình & Sách chuyên khảo**: Tìm kiếm theo tên học phần, tác giả hoặc chuyên ngành\n"
        "- **Cơ sở dữ liệu số**: Hướng dẫn truy cập tài liệu quốc tế (ScienceDirect, IEEE Xplore, Springer)\n"
        "- **Mượn trả & Lưu chiểu**: Thời hạn mượn sách, quy trình nộp khóa luận tốt nghiệp bản điện tử\n\n"
        "Bạn vui lòng liên hệ **Trung tâm Thông tin - Thư viện QNU** qua Hotline: **0256.3846.888** hoặc Email: **thuvien@qnu.edu.vn** để được hỗ trợ bạn đọc nhé!"
    ),
    "drafting": (
        "Chào Thầy/Cô! Hiện tại hệ thống chưa tìm thấy biểu mẫu hoặc căn cứ pháp lý phù hợp trong kho văn bản hành chính của Trường ĐH Quy Nhơn.\n\n"
        "Thầy/Cô có thể yêu cầu soạn thảo các thể thức văn bản theo Nghị định 30/2020/NĐ-CP như:\n"
        "- **Tờ trình**: Xin phê duyệt kinh phí, mua sắm trang thiết bị, tổ chức hội nghị khoa học\n"
        "- **Thông báo & Kế hoạch**: Kế hoạch công tác năm học, thông báo triển khai nhiệm vụ\n"
        "- **Quyết định & Giấy mời**: Kiện toàn ban tổ chức, giấy mời đại biểu dự lễ khai giảng\n\n"
        "Nếu cần cung cấp thêm biểu mẫu đặc thù, Thầy/Cô vui lòng liên hệ **Phòng Hành chính - Tổng hợp** để được hỗ trợ."
    ),
    "question_bank": (
        "Chào Thầy/Cô! Hiện chưa đủ dữ liệu chuẩn đầu ra (CLO/PLO) hoặc nội dung học phần để thiết kế câu hỏi hoặc ma trận đề thi này.\n\n"
        "Thầy/Cô có thể cung cấp thêm đề cương chi tiết học phần hoặc thử các yêu cầu như:\n"
        "- **Thiết kế ma trận đề thi**: Phân bổ 4 mức độ nhận thức Bloom (Nhận biết, Thông hiểu, Vận dụng, Vận dụng cao)\n"
        "- **Soạn câu hỏi trắc nghiệm / tự luận**: Kèm đáp án, biểu điểm và hướng dẫn chấm chi tiết\n"
        "- **Xuất file ma trận đề**: Định dạng bảng tính Excel chuẩn khảo thí ĐH Quy Nhơn\n\n"
        "Để được hướng dẫn chuẩn hóa ngân hàng câu hỏi, Thầy/Cô vui lòng liên hệ **Phòng Khảo thí & Đảm bảo chất lượng giáo dục**."
    ),
    "general": (
        "Thông tin bạn yêu cầu hiện không có trong cơ sở dữ liệu tri thức của Trường Đại học Quy Nhơn. "
        "Vui lòng liên hệ bộ phận phụ trách để được giải đáp chính xác nhất."
    ),
}

# Generic evidence keywords reusable across all assistants.
# Replaces the old admissions-only heuristic so new domains are not misclassified.
EVIDENCE_KEYWORDS = (
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
    "giáo trình",
    "tài liệu",
    "thư viện",
    "luận văn",
    "quyết định",
    "công văn",
    "nghị định",
    "thông tư",
    "tờ trình",
    "đề thi",
    "câu hỏi",
    "ma trận",
    "chuẩn đầu ra",
    "ký túc xá",
    "học bổng",
    "%",
    "năm 202",
    "năm 199",
)

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
        has_substantive_content = any(kw in answer_lower for kw in EVIDENCE_KEYWORDS)
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

    def verify_numeric_grounding(
        self,
        answer: str,
        citations: list[Citation],
        facts_used: list[dict] | None = None,
    ) -> tuple[bool, list[str]]:
        """Check that multi-digit figures in the answer exist in evidence text.

        Single digits are skipped (too noisy: list indices, counts). Comparison is
        separator-insensitive so "112,3" matches "112.3". Returns (grounded, ungrounded).
        """
        if not (answer or "").strip():
            return True, []
        targets = {
            re.sub(r"\D", "", n)
            for n in re.findall(r"\d+(?:[.,]\d+)*", answer)
        }
        targets = {t for t in targets if len(t) >= 2}
        if not targets:
            return True, []

        evidence_parts: list[str] = []
        for cite in citations or []:
            if cite.quote:
                evidence_parts.append(cite.quote)
        for fact in facts_used or []:
            if isinstance(fact, dict):
                for key in ("val", "entity", "attr"):
                    if fact.get(key):
                        evidence_parts.append(str(fact[key]))
        evidence_numbers = {
            re.sub(r"\D", "", n)
            for n in re.findall(r"\d+(?:[.,]\d+)*", " ".join(evidence_parts))
        }

        ungrounded = sorted(t for t in targets if t not in evidence_numbers)
        return (not ungrounded), ungrounded

    def get_no_answer_response(
        self,
        module_code: str = "general",
        assistant_name: str | None = None,
    ) -> str:
        """Return friendly rejection response when context is insufficient.

        Reusable for any new assistant: known modules use curated templates,
        unknown modules fall back to a generic template optionally naming
        the assistant.
        """
        normalized = (module_code or "general").strip().lower()
        if normalized in NO_ANSWER_MESSAGES:
            return NO_ANSWER_MESSAGES[normalized]
        if assistant_name and assistant_name.strip():
            return (
                f"Chào bạn! Thông tin này hiện chưa có trong kho tri thức của "
                f"Trợ lý {assistant_name.strip()} (Trường Đại học Quy Nhơn).\n"
                "Bạn vui lòng thử diễn đạt lại câu hỏi cụ thể hơn hoặc liên hệ "
                "bộ phận phụ trách để được hỗ trợ chính xác nhất."
            )
        return NO_ANSWER_MESSAGES["general"]

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
