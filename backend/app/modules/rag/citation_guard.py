"""Citation Guard & Groundedness Policy — Strict Source Verification & Hallucination Prevention."""

from __future__ import annotations

import logging
import re

from app.core.stopwords import get_vietnamese_stopwords
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.schemas import Citation

logger = logging.getLogger(__name__)

NO_ANSWER_MESSAGES = {
    "general": (
        "Mình chưa xác minh được thông tin đủ phù hợp để trả lời câu hỏi này từ các nguồn đang xuất bản. "
        "Bạn có thể nói rõ thêm phạm vi hoặc năm cần tra cứu."
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

# Vietnamese academic & general stopwords loaded dynamically from configs/stopwords_vi.txt
ACADEMIC_STOPWORDS: frozenset[str] = get_vietnamese_stopwords()


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

            meta = c.metadata or {}
            doc_name = (
                meta.get("document_title")
                or meta.get("file_name")
                or meta.get("title")
                or meta.get("collection_name")
            )
            title = doc_name or c.section or f"Tài liệu tuyển sinh ({c.document_id[:8]})"
            if title.startswith("doc_"):
                title = f"Tài liệu ({title})"
            source_quote = meta.get("citation_quote")
            quoted = source_quote if isinstance(source_quote, str) and source_quote.strip() else c.content
            quote = quoted[:1500].strip() + ("..." if len(quoted) > 1500 else "")
            source_pages = meta.get("source_pages")
            if not source_pages and c.page_number:
                source_pages = [c.page_number]
            entity_key = meta.get("entity_key")

            binding_id = c.binding_id or meta.get("binding_id")
            index_revision_id = c.index_revision_id or meta.get("index_revision_id")
            source_revision_id = meta.get("source_revision_id")
            revision_no = c.document_revision or meta.get("document_revision") or meta.get("revision_no")

            citations.append(
                Citation(
                    source_id=c.document_id,
                    title=title,
                    section=c.section,
                    page_number=c.page_number,
                    quote=quote,
                    source_pages=source_pages,
                    entity_key=entity_key,
                    binding_id=str(binding_id) if binding_id else None,
                    index_revision_id=str(index_revision_id) if index_revision_id else None,
                    source_revision_id=str(source_revision_id) if source_revision_id else None,
                    revision_no=int(revision_no) if revision_no is not None else None,
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
        query: str | None = None,
        system_context: str | None = None,
        candidate_texts: list[str] | None = None,
    ) -> tuple[bool, list[str]]:
        """Compare complete numeric values against evidence, not prompts or substrings.

        This is a numeric presence gate, not proof of metric/year entailment.
        query/system_context remain compatibility arguments, never evidence.
        """
        from app.modules.rag.evidence_validation import number_values

        if not (answer or "").strip():
            return True, []
        evidence_parts: list[str] = []
        if candidate_texts:
            for text in candidate_texts:
                if text and text.strip():
                    evidence_parts.append(text)
        for cite in citations or []:
            if cite.quote:
                evidence_parts.append(cite.quote)
        for fact in facts_used or []:
            if isinstance(fact, dict):
                for key in ("val", "entity", "attr"):
                    if fact.get(key):
                        evidence_parts.append(str(fact[key]))

        def values(text: str) -> set:
            # All-zero decimal spellings are the same number, not a new fact.
            return number_values(re.sub(r"(?<![\w.,])0[.,]0+\b", "0", text))

        evidence_numbers = set().union(*(values(part) for part in evidence_parts))
        # Preserve the existing multi-digit gate boundary: small list ordinals
        # and word-to-digit counts are not proof of a new numeric measurement.
        targets = {value for value in values(answer) if len(re.sub(r"\D", "", str(value))) >= 2}
        ungrounded = sorted(str(value) for value in targets - evidence_numbers)
        return (not ungrounded), ungrounded

    def get_no_answer_response(
        self,
        module_code: str = "general",
        assistant_name: str | None = None,
    ) -> str:
        """Report verification limits, not source absence or unsourced contacts."""
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
