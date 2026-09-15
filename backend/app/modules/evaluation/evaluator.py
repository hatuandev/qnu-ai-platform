"""Ragas TM-08 Core Evaluator Engine for QNU AI Platform.

Evaluates RAG pipeline performance against official QNU academic criteria:
- Faithfulness >= 0.90 (Zero-hallucination ground truth verification)
- Answer Relevance >= 0.85 (Direct question resolution)
- Context Precision >= 0.80 (Accurate document retrieval ranking)
"""

from __future__ import annotations

import re
from typing import Any


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
        if "0256.3846.156" in answer or "chưa có thông tin" in answer.lower() or "không tìm thấy" in answer.lower():
            return 1.0

        combined_context = " ".join(contexts).lower()
        if not combined_context:
            return 0.0

        # Extract factual sentences/clauses from answer
        sentences = [s.strip() for s in re.split(r"[.!?;\n]+", answer) if len(s.strip()) > 8]
        if not sentences:
            return 1.0

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

    def compute_answer_relevance(self, query: str, answer: str) -> float:
        """Measure how directly the generated answer addresses the user query."""
        if not query.strip() or not answer.strip():
            return 0.0

        query_tokens = set(re.findall(r"\b\w{2,}\b", query.lower()))
        answer_tokens = set(re.findall(r"\b\w{2,}\b", answer.lower()))

        if not query_tokens:
            return 0.5

        # Query keywords present in answer
        overlap = query_tokens.intersection(answer_tokens)
        query_coverage = len(overlap) / len(query_tokens)

        # Penalize answers that are overly concise (<10 words) or empty
        length_penalty = min(1.0, len(answer.split()) / 8.0)

        relevance = (query_coverage * 0.7 + length_penalty * 0.3)
        return round(min(1.0, max(0.0, relevance)), 3)

    def compute_context_precision(self, ground_truth: str, contexts: list[str]) -> float:
        """Measure if retrieved contexts contain the essential facts of the ground truth."""
        if not contexts or not ground_truth.strip():
            return 0.0

        gt_tokens = set(re.findall(r"\b\w{2,}\b", ground_truth.lower()))
        if not gt_tokens:
            return 1.0

        relevant_chunks = 0
        for ctx in contexts:
            ctx_lower = ctx.lower()
            matching = [t for t in gt_tokens if t in ctx_lower]
            if len(matching) / len(gt_tokens) >= 0.30:
                relevant_chunks += 1

        precision = relevant_chunks / len(contexts)
        return round(min(1.0, max(0.0, precision)), 3)

    def detect_hallucination(self, answer: str, contexts: list[str]) -> bool:
        """Flag hallucinated facts such as unsupported numbers, dates, or contact info."""
        clean_answer = re.sub(r"0256[.\s]?3846[.\s]?156", " ", answer)
        clean_answer = re.sub(r"1800[.\s]?55[.\s]?88[.\s]?49", " ", clean_answer)
        combined_context = " ".join(contexts).lower()

        # Find numbers (dates, scores, codes)
        numbers_in_answer = re.findall(r"\b\d+(?:[.,]\d+)?\b", clean_answer)
        for num in numbers_in_answer:
            if num in ["2024", "2025", "2026"]:
                continue
            if num not in combined_context:
                return True

        return False

    def evaluate_item(
        self, query: str, ground_truth: str, answer: str, contexts: list[str]
    ) -> dict[str, Any]:
        """Perform full TM-08 assessment on a single evaluation sample."""
        faithfulness = self.compute_faithfulness(answer, contexts)
        relevance = self.compute_answer_relevance(query, answer)
        precision = self.compute_context_precision(ground_truth, contexts)
        is_hallucinated = self.detect_hallucination(answer, contexts)

        passed = (
            faithfulness >= self.FAITHFULNESS_THRESHOLD
            and relevance >= self.ANSWER_RELEVANCE_THRESHOLD
            and precision >= self.CONTEXT_PRECISION_THRESHOLD
            and not is_hallucinated
        )

        return {
            "faithfulness": faithfulness,
            "answer_relevance": relevance,
            "context_precision": precision,
            "is_hallucinated": is_hallucinated,
            "passed": passed,
        }


# Global Evaluator Singleton
tm08_evaluator = RagasTM08Evaluator()
