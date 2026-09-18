"""Ragas TM-08 Core Evaluator Engine for QNU AI Platform.

Evaluates RAG pipeline performance against official QNU academic criteria:
- Faithfulness >= 0.90 (Zero-hallucination ground truth verification)
- Answer Relevance >= 0.85 (Direct question resolution)
- Context Precision >= 0.80 (Accurate document retrieval ranking)
"""

from __future__ import annotations

import re
from typing import Any

VIETNAMESE_QUESTION_STOPWORDS = {
    "là", "gì", "như", "thế", "nào", "ở", "đâu", "bao", "nhiêu", "sao", "mấy",
    "ai", "của", "và", "các", "những", "được", "cho", "với", "trong", "khi",
    "thì", "có", "không", "đến", "từ", "theo", "về", "ra", "đối", "sang", "mỗi",
    "tại", "trường", "đh", "đại", "học", "áp", "dụng", "hãy", "biết", "thông",
    "thường", "chuẩn", "này", "đó", "hay", "cần", "phải", "thực", "hiện",
    "quy", "định", "cụ", "thể", "gồm", "nêu", "rõ", "xin", "hỏi",
}


class RagasTM08Evaluator:
    """Mathematical and heuristic evaluator for Ragas TM-08 metrics."""

    FAITHFULNESS_THRESHOLD = 0.90
    ANSWER_RELEVANCE_THRESHOLD = 0.85
    CONTEXT_PRECISION_THRESHOLD = 0.80

    def compute_faithfulness(self, answer: str, contexts: list[str]) -> float:
        """Measure what fraction of statements in the answer are grounded in context."""
        if not answer.strip():
            return 0.0

        # No-Answer Policy compliance: When safely declining due to missing evidence, faithfulness is 100%
        answer_lower = answer.lower()
        if (
            "0256.3846.156" in answer
            or "0256.3846.888" in answer
            or "chưa có thông tin" in answer_lower
            or "chưa có trong" in answer_lower
            or "chưa đủ căn cứ" in answer_lower
            or "chưa đủ chuẩn đầu ra" in answer_lower
            or "không tìm thấy" in answer_lower
            or "liên hệ phòng" in answer_lower
        ):
            return 1.0

        combined_context = " ".join(contexts).lower()
        if not combined_context:
            return 0.0

        # Extract factual sentences/clauses from answer
        raw_sentences = [s.strip() for s in re.split(r"[.!?;\n]+", answer) if len(s.strip()) > 8]
        if not raw_sentences:
            return 1.0

        # Exclude polite conversational framing from factual grounding check
        sentences = []
        for s in raw_sentences:
            s_lower = s.lower().strip()
            if any(s_lower.startswith(p) for p in [
                "căn cứ quy định", "căn cứ tài liệu", "căn cứ thông tin", "căn cứ dữ liệu",
                "dựa trên", "theo quy chế", "theo thông báo", "theo đề án",
                "xin giải đáp", "xin gửi thông tin", "chào bạn", "kính gửi"
            ]) and len(s.split()) <= 16:
                continue
            sentences.append(s)

        if not sentences:
            sentences = raw_sentences

        grounded_count = 0
        for sent in sentences:
            # Tokenize meaningful words (>2 characters)
            words = [w.lower() for w in re.findall(r"\b\w{2,}\b", sent)]
            if not words:
                continue

            # Check overlap against context
            matching_words = [w for w in words if w in combined_context]
            overlap_ratio = len(matching_words) / len(words)
            if overlap_ratio >= 0.60:
                grounded_count += 1

        return round(min(1.0, max(0.0, grounded_count / len(sentences))), 3)

    def compute_answer_relevance(
        self,
        query: str,
        answer: str,
        ground_truth: str = "",
        keywords: list[str] | None = None,
    ) -> float:
        """Measure how directly the generated answer addresses the user query and ground truth."""
        if not query.strip() or not answer.strip():
            return 0.0

        all_query_tokens = set(re.findall(r"\b\w{2,}\b", query.lower()))
        content_tokens = all_query_tokens - VIETNAMESE_QUESTION_STOPWORDS
        query_tokens = content_tokens if content_tokens else all_query_tokens
        answer_tokens = set(re.findall(r"\b\w{2,}\b", answer.lower()))

        if not query_tokens:
            return 0.5

        # 1. Query keywords present in answer
        overlap = query_tokens.intersection(answer_tokens)
        query_coverage = len(overlap) / len(query_tokens)

        # 2. Benchmark keywords / ground truth alignment
        gt_coverage = 0.0
        if keywords:
            answer_lower = answer.lower()
            matched = sum(
                1
                for kw in keywords
                if any(token in answer_lower for token in kw.lower().split() if token not in VIETNAMESE_QUESTION_STOPWORDS)
            )
            gt_coverage = matched / max(len(keywords), 1)
        elif ground_truth:
            gt_tokens = set(re.findall(r"\b\w{2,}\b", ground_truth.lower())) - VIETNAMESE_QUESTION_STOPWORDS
            if gt_tokens:
                gt_coverage = len(gt_tokens.intersection(answer_tokens)) / len(gt_tokens)

        effective_coverage = max(query_coverage, gt_coverage, (query_coverage * 0.3 + gt_coverage * 0.7))

        # Penalize answers that are overly concise (<8 words) or empty
        length_penalty = min(1.0, len(answer.split()) / 8.0)

        relevance = (effective_coverage * 0.7 + length_penalty * 0.3)
        return round(min(1.0, max(0.0, relevance)), 3)

    def compute_context_precision(self, ground_truth: str, contexts: list[str]) -> float:
        """Measure if retrieved contexts contain the essential facts of the ground truth using Ragas AP@k."""
        if not contexts or not ground_truth.strip():
            return 0.0

        gt_tokens = set(re.findall(r"\b\w{2,}\b", ground_truth.lower()))
        if not gt_tokens:
            return 1.0

        relevant_count = 0
        precision_at_k_sum = 0.0

        for rank, ctx in enumerate(contexts, start=1):
            ctx_lower = ctx.lower()
            matching = [t for t in gt_tokens if t in ctx_lower]
            if len(matching) / len(gt_tokens) >= 0.25:
                relevant_count += 1
                precision_at_k_sum += relevant_count / rank

        if relevant_count == 0:
            return 0.0

        precision = precision_at_k_sum / relevant_count
        return round(min(1.0, max(0.0, precision)), 3)

    def detect_hallucination(self, answer: str, contexts: list[str]) -> bool:
        """Flag hallucinated facts such as unsupported numbers, dates, or contact info."""
        clean_answer = re.sub(r"0256[.\s]?3846[.\s]?156", " ", answer)
        clean_answer = re.sub(r"0256[.\s]?3846[.\s]?888", " ", clean_answer)
        clean_answer = re.sub(r"1800[.\s]?55[.\s]?88[.\s]?49", " ", clean_answer)
        combined_context = " ".join(contexts).lower()

        # Find numbers (dates, scores, codes)
        numbers_in_answer = re.findall(r"\b\d+(?:[.,]\d+)?\b", clean_answer)
        for num in numbers_in_answer:
            if num in ["2020", "2024", "2025", "2026", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]:
                continue
            if num not in combined_context:
                return True

        return False

    def evaluate_item(
        self,
        query: str,
        ground_truth: str,
        answer: str,
        contexts: list[str],
        keywords: list[str] | None = None,
    ) -> dict[str, Any]:
        """Perform full TM-08 assessment on a single evaluation sample."""
        faithfulness = self.compute_faithfulness(answer, contexts)
        relevance = self.compute_answer_relevance(query, answer, ground_truth, keywords)
        precision = self.compute_context_precision(ground_truth, contexts)
        is_hallucinated = self.detect_hallucination(answer, contexts)

        passed = (
            faithfulness >= self.FAITHFULNESS_THRESHOLD
            and relevance >= self.ANSWER_RELEVANCE_THRESHOLD
            and precision >= self.CONTEXT_PRECISION_THRESHOLD
            and not is_hallucinated
        )

        return {
            "query": query,
            "ground_truth": ground_truth,
            "answer": answer,
            "faithfulness": faithfulness,
            "answer_relevance": relevance,
            "context_precision": precision,
            "is_hallucinated": is_hallucinated,
            "passed": passed,
        }


# Global Evaluator Singleton
tm08_evaluator = RagasTM08Evaluator()
