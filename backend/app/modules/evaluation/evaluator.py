"""Ragas TM-08 Core Evaluator Engine for QNU AI Platform.

Evaluates RAG pipeline performance against official QNU academic criteria:
- Faithfulness >= 0.90 (Zero-hallucination ground truth verification)
- Answer Relevance >= 0.85 (Direct question resolution)
- Context Precision >= 0.80 (Accurate document retrieval ranking)
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

VIETNAMESE_QUESTION_STOPWORDS = {
    "là", "gì", "như", "thế", "nào", "ở", "đâu", "bao", "nhiêu", "sao", "mấy",
    "ai", "của", "và", "các", "những", "được", "cho", "với", "trong", "khi",
    "thì", "có", "không", "đến", "từ", "theo", "về", "ra", "đối", "sang", "mỗi",
    "tại", "trường", "đh", "đại", "học", "áp", "dụng", "hãy", "biết", "thông",
    "thường", "chuẩn", "này", "đó", "hay", "cần", "phải", "thực", "hiện",
    "quy", "định", "cụ", "thể", "gồm", "nêu", "rõ", "xin", "hỏi",
}

REFUSAL_PHRASES = [
    "0256.3846.156",
    "0256.3846.888",
    "1800.55.88.49",
    "chưa có thông tin",
    "chưa có trong",
    "chưa đủ căn cứ",
    "chưa đủ chuẩn đầu ra",
    "không tìm thấy",
    "liên hệ phòng",
    "chưa được quy định cụ thể",
    "không có dữ liệu",
]


class BaseTM08Evaluator(ABC):
    """Base abstract evaluator for Ragas TM-08 metrics."""

    FAITHFULNESS_THRESHOLD = 0.90
    ANSWER_RELEVANCE_THRESHOLD = 0.85
    CONTEXT_PRECISION_THRESHOLD = 0.80

    @abstractmethod
    def evaluate_item(
        self,
        query: str,
        ground_truth: str,
        answer: str,
        contexts: list[str],
        keywords: list[str] | None = None,
    ) -> dict[str, Any]:
        """Synchronous assessment on a single evaluation sample."""
        ...

    def is_refusal_answer(self, answer: str) -> bool:
        """Check whether answer invoked No-Answer / safety refusal."""
        if not answer:
            return False
        answer_lower = answer.lower()
        return any(phrase in answer_lower for phrase in REFUSAL_PHRASES)


class HeuristicTM08Evaluator(BaseTM08Evaluator):
    """Mathematical and heuristic evaluator for Ragas TM-08 metrics (Fast Precheck)."""

    def compute_faithfulness(self, answer: str, contexts: list[str]) -> float:
        """Measure what fraction of statements in the answer are grounded in context."""
        if not answer.strip():
            return 0.0

        # No-Answer Policy compliance: When safely declining due to missing evidence, faithfulness is 100%
        if self.is_refusal_answer(answer):
            return 1.0

        combined_context = " ".join(contexts).lower()
        if not combined_context:
            return 0.0

        # Extract factual sentences/clauses from answer (do not split on decimal points like 8.5 or 26.25)
        raw_sentences = [
            s.strip() for s in re.split(r"(?<!\d)[.!?;\n]+(?!\d)", answer) if len(s.strip()) > 8
        ]
        if not raw_sentences:
            return 1.0

        # Exclude polite conversational framing & citation meta notes from factual grounding check
        sentences = []
        for s in raw_sentences:
            s_lower = s.lower().strip()
            if any(s_lower.startswith(p) or p in s_lower for p in [
                "căn cứ quy định", "căn cứ tài liệu", "căn cứ thông tin", "căn cứ dữ liệu",
                "dựa trên", "theo quy chế", "theo thông báo", "theo đề án",
                "xin giải đáp", "xin gửi thông tin", "chào bạn", "kính gửi",
                "thông tin được trích dẫn", "trích dẫn từ", "nguồn:", "trích dẫn chính xác",
            ]) and len(s.split()) <= 18:
                continue
            sentences.append(s)

        if not sentences:
            sentences = raw_sentences

        grounded_count = 0
        for sent in sentences:
            words = [w.lower() for w in re.findall(r"\b\w{2,}\b", sent)]
            if not words:
                continue

            matching_words = [w for w in words if w in combined_context]
            overlap_ratio = len(matching_words) / len(words)
            if overlap_ratio >= 0.50:
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

        # Truthful handling of Refusals:
        is_refusal = self.is_refusal_answer(answer)
        gt_is_refusal = self.is_refusal_answer(ground_truth)

        if is_refusal and gt_is_refusal:
            # Both declined appropriately because the information is not present
            return 1.0

        if is_refusal and not gt_is_refusal and len(ground_truth.strip()) > 15:
            # The assistant declined an answerable benchmark question
            return 0.20

        all_query_tokens = set(re.findall(r"\b\w{2,}\b", query.lower()))
        content_tokens = all_query_tokens - VIETNAMESE_QUESTION_STOPWORDS
        query_tokens = content_tokens if content_tokens else all_query_tokens
        answer_tokens = set(re.findall(r"\b\w{2,}\b", answer.lower()))

        if not query_tokens:
            return 0.5

        overlap = query_tokens.intersection(answer_tokens)
        query_coverage = len(overlap) / len(query_tokens)

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
        length_penalty = min(1.0, len(answer.split()) / 8.0)

        relevance = (effective_coverage * 0.7 + length_penalty * 0.3)
        return round(min(1.0, max(0.0, relevance)), 3)

    def compute_context_precision(self, ground_truth: str, contexts: list[str]) -> float:
        """Measure if retrieved contexts contain the essential facts of the ground truth using Ragas AP@k."""
        # For mutual refusal (No-Answer policy compliance on ungrounded questions), precision is 100%
        if self.is_refusal_answer(ground_truth):
            return 1.0

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
        """Perform full TM-08 heuristic assessment on a single evaluation sample."""
        faithfulness = self.compute_faithfulness(answer, contexts)
        relevance = self.compute_answer_relevance(query, answer, ground_truth, keywords)
        precision = self.compute_context_precision(ground_truth, contexts)
        is_hallucinated = self.detect_hallucination(answer, contexts)
        is_refusal = self.is_refusal_answer(answer)

        passed = (
            faithfulness >= self.FAITHFULNESS_THRESHOLD
            and relevance >= self.ANSWER_RELEVANCE_THRESHOLD
            and precision >= self.CONTEXT_PRECISION_THRESHOLD
            and not is_hallucinated
        )

        reasoning = "Đạt toàn bộ tiêu chí TM-08." if passed else ""
        if not passed:
            reasons = []
            if faithfulness < self.FAITHFULNESS_THRESHOLD:
                reasons.append(f"Độ trung thực thấp ({faithfulness} < 0.90)")
            if relevance < self.ANSWER_RELEVANCE_THRESHOLD:
                if is_refusal:
                    reasons.append("Từ chối trả lời (No-Answer) trong khi câu hỏi có dữ liệu đáp án")
                else:
                    reasons.append(f"Độ liên quan thấp ({relevance} < 0.85)")
            if precision < self.CONTEXT_PRECISION_THRESHOLD:
                reasons.append(f"Độ chính xác ngữ cảnh thấp ({precision} < 0.80)")
            if is_hallucinated:
                reasons.append("Phát hiện số liệu/thông tin bịa đặt ngoài ngữ cảnh")
            reasoning = "; ".join(reasons)

        return {
            "query": query,
            "ground_truth": ground_truth,
            "answer": answer,
            "faithfulness": faithfulness,
            "answer_relevance": relevance,
            "context_precision": precision,
            "is_hallucinated": is_hallucinated,
            "is_refusal": is_refusal,
            "passed": passed,
            "reasoning": reasoning,
        }


class LLMJudgeTM08Evaluator(BaseTM08Evaluator):
    """Deep semantic LLM-as-a-Judge evaluator utilizing ModelOps and QNU TM-08 rubrics."""

    def __init__(self, fallback_evaluator: HeuristicTM08Evaluator | None = None) -> None:
        self.fallback = fallback_evaluator or HeuristicTM08Evaluator()

    def evaluate_item(
        self,
        query: str,
        ground_truth: str,
        answer: str,
        contexts: list[str],
        keywords: list[str] | None = None,
    ) -> dict[str, Any]:
        """Synchronous fallback to heuristic evaluation when no async event loop is available."""
        res = self.fallback.evaluate_item(query, ground_truth, answer, contexts, keywords)
        res["reasoning"] = f"[Heuristic Precheck] {res.get('reasoning', '')}"
        return res

    async def evaluate_item_async(
        self,
        session: Any,
        query: str,
        ground_truth: str,
        answer: str,
        contexts: list[str],
        keywords: list[str] | None = None,
    ) -> dict[str, Any]:
        """Perform LLM-as-a-Judge semantic grading based on academic TM-08 rubric."""
        # Check basic edge cases
        if not answer.strip():
            return {
                "query": query,
                "ground_truth": ground_truth,
                "answer": "",
                "faithfulness": 0.0,
                "answer_relevance": 0.0,
                "context_precision": 0.0,
                "is_hallucinated": False,
                "is_refusal": False,
                "passed": False,
                "reasoning": "Câu trả lời của Trợ lý rỗng.",
            }

        prompt = (
            "Bạn là Thẩm Định Viên Độc Lập chuẩn Ragas TM-08 của Trường Đại học Quy Nhơn.\n"
            "Nhiệm vụ: Chấm điểm định lượng chất lượng phản hồi RAG của Trợ lý AI dựa trên Câu hỏi, "
            "Câu trả lời chuẩn (Ground Truth), Câu trả lời thực tế (Generated Answer) và Ngữ cảnh trích xuất (Contexts).\n\n"
            f"CÂU HỎI:\n{query}\n\n"
            f"GROUND TRUTH (KỲ VỌNG):\n{ground_truth}\n\n"
            f"GENERATED ANSWER (THỰC TẾ):\n{answer}\n\n"
            f"CONTEXTS (NGỮ CẢNH RAG TRÍCH XUẤT):\n" + "\n---\n".join(contexts[:4]) + "\n\n"
            "TIÊU CHÍ ĐÁNH GIÁ (Thang điểm 0.00 đến 1.00):\n"
            "1. faithfulness: Các tuyên bố và số liệu trong câu trả lời có được minh chứng từ Contexts không? "
            "Nếu tự bịa đặt -> điểm thấp. Nếu là câu từ chối an toàn do context thiếu dữ liệu -> 1.0.\n"
            "2. answer_relevance: Câu trả lời có giải quyết đúng trọng tâm và sát nghĩa với Ground Truth không? "
            "ĐẶC BIỆT LƯU Ý: Nếu Ground Truth có câu trả lời rõ ràng mà Generated Answer lại từ chối "
            "('Không tìm thấy thông tin' / 'Chưa có thông tin') thì relevance tối đa 0.20.\n"
            "3. context_precision: Ngữ cảnh trích xuất có chứa căn cứ để trả lời câu hỏi không?\n"
            "4. is_hallucinated (boolean): Có bịa đặt số liệu/thông tin nằm ngoài Contexts không?\n"
            "5. is_refusal (boolean): Có phải là câu từ chối trả lời do thiếu căn cứ không?\n"
            "6. reasoning (string): Giải thích ngắn gọn căn cứ chấm điểm bằng tiếng Việt.\n\n"
            "BẮT BUỘC trả về duy nhất 1 JSON object (không bọc trong markdown hay giải thích ngoài):\n"
            '{"faithfulness": 0.95, "answer_relevance": 0.90, "context_precision": 0.85, '
            '"is_hallucinated": false, "is_refusal": false, "reasoning": "..."}'
        )

        try:
            from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
            from app.modules.modelops.service import modelops_service

            llm_req = LLMGenerateRequest(
                messages=[ChatMessage(role="user", content=prompt)],
                temperature=0.1,
                max_tokens=500,
            )
            gen_res = await modelops_service.generate(session, llm_req)
            raw_text = gen_res.content.strip()

            # Clean json fences if present
            raw_text = raw_text.removeprefix("```json")
            raw_text = raw_text.removeprefix("```")
            raw_text = raw_text.removesuffix("```")

            parsed = json.loads(raw_text.strip())
            faith = round(float(parsed.get("faithfulness", 0.0)), 3)
            rel = round(float(parsed.get("answer_relevance", 0.0)), 3)
            prec = round(float(parsed.get("context_precision", 0.0)), 3)
            hallucinated = bool(parsed.get("is_hallucinated", False))
            refusal = bool(parsed.get("is_refusal", self.is_refusal_answer(answer)))
            reasoning = str(parsed.get("reasoning", "Đánh giá bởi LLM-as-a-Judge."))

            passed = (
                faith >= self.FAITHFULNESS_THRESHOLD
                and rel >= self.ANSWER_RELEVANCE_THRESHOLD
                and prec >= self.CONTEXT_PRECISION_THRESHOLD
                and not hallucinated
            )

            return {
                "query": query,
                "ground_truth": ground_truth,
                "answer": answer,
                "faithfulness": faith,
                "answer_relevance": rel,
                "context_precision": prec,
                "is_hallucinated": hallucinated,
                "is_refusal": refusal,
                "passed": passed,
                "reasoning": f"[LLM-Judge] {reasoning}",
            }
        except Exception as judge_err:
            logger.warning("llm_judge_failed_falling_back_to_heuristic", error=str(judge_err))
            fallback_res = self.fallback.evaluate_item(query, ground_truth, answer, contexts, keywords)
            fallback_res["reasoning"] = f"[Fallback Heuristic] {fallback_res.get('reasoning', '')}"
            return fallback_res


# Global Evaluator Singletons
heuristic_evaluator = HeuristicTM08Evaluator()
llm_judge_evaluator = LLMJudgeTM08Evaluator(fallback_evaluator=heuristic_evaluator)

# Backward Compatibility Aliases
RagasTM08Evaluator = HeuristicTM08Evaluator
tm08_evaluator = heuristic_evaluator


def get_evaluator(method: str = "heuristic") -> BaseTM08Evaluator:
    """Factory helper to obtain evaluator instance by strategy name."""
    if method == "llm_judge":
        return llm_judge_evaluator
    return heuristic_evaluator
