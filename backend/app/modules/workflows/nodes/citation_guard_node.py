"""Citation Policy Guardrail Node Handler — Enforces Anti-Hallucination & Groundedness."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec

logger = logging.getLogger(__name__)

# Syntactic pattern for introductory adverbial phrases, source attributions, and polite framing
_SYNTACTIC_FRAMING_PATTERN = re.compile(
    r"^\s*(?:căn\s+cứ|theo|dựa\s+trên|kính\s+gửi|xin\s+(?:phép|gửi|giải|chào)|chào\s+|nguồn\s*:|trích\s+dẫn)\b",
    re.IGNORECASE,
)


def _is_benign_structural_number(num_str: str) -> bool:
    """Mathematical invariant to distinguish benign structural indices/years from substantive metrics.

    Invariants:
    1. Calendar year pattern: 4-digit years '19xx' or '20xx' (e.g. 2024, 2026, 2030).
    2. Small ordinal / bullet indices: Integers from 1 to 10 (or with leading zero '01' to '09').
    3. Normalization percentage: '100' (standard ratio / completeness marker).
    Substantive quantitative metrics (decimals like 24.5, large numbers >= 11 like quotas, tuition, scores)
    are NOT benign and MUST be substantiated by context.
    """
    if not num_str:
        return True

    # Decimal numbers (e.g. 24.5, 28.75) are always quantitative metrics
    if "." in num_str or "," in num_str:
        return False

    # Calendar year structure: 1900-2099
    if re.fullmatch(r"(?:19|20)\d{2}", num_str):
        return True

    # Small ordinal / step numbers: 1..10 or 100%
    try:
        val = int(num_str)
        if 1 <= val <= 10 or val == 100:
            return True
    except ValueError:
        pass

    return False


def _gather_combined_context(
    context: WorkflowContext, citations: list[dict[str, Any]]
) -> str:
    """Gather all ground-truth reference context text from citations, facts and node_data."""
    context_parts: list[str] = []

    # 1. Direct contexts list from retriever
    raw_ctxs = context.node_data.get("contexts") or context.outputs.get("contexts")
    if raw_ctxs and isinstance(raw_ctxs, list):
        context_parts.extend(str(c) for c in raw_ctxs if c)

    # 2. Citation quotes, snippets, titles, and sections
    for cit in citations:
        if isinstance(cit, dict):
            for field_name in ("quote", "content", "snippet", "title", "section"):
                val = cit.get(field_name)
                if val and isinstance(val, str) and val.strip():
                    context_parts.append(val.strip())

    # 3. Fact layer data or guidance context
    fact_md = context.node_data.get("fact_markdown") or context.node_data.get(
        "guidance_context"
    )
    if fact_md and isinstance(fact_md, str):
        context_parts.append(fact_md)

    return " ".join(context_parts).lower()


def _detect_number_hallucinations(answer: str, combined_context: str) -> list[str]:
    """Extract substantive numbers from generated answer and check if they are grounded in context."""
    if not combined_context:
        return []

    # Strip official university hotlines so their digits don't get flagged as fake numbers
    clean_answer = re.sub(r"0256[.\s]?3846[.\s]?156", " ", answer)
    clean_answer = re.sub(r"0256[.\s]?3846[.\s]?888", " ", clean_answer)
    clean_answer = re.sub(r"1800[.\s]?55[.\s]?88[.\s]?49", " ", clean_answer)

    # Match all integers, decimals, and thousand-separated metrics (e.g. 24.5, 26,25, 15.000.000)
    numbers_in_answer = re.findall(r"\b\d+(?:[.,]\d+)*\b", clean_answer)
    unsupported: list[str] = []
    for num in numbers_in_answer:
        if _is_benign_structural_number(num):
            continue
        # Support both dot and comma decimal notations (e.g. '24.5' vs '24,5')
        num_dot = num.replace(",", ".")
        num_comma = num.replace(".", ",")
        # Support raw digit sequence for thousand-separated numbers (e.g. '15.000.000' vs '15000000')
        raw_digits = (
            re.sub(r"[.,]", "", num)
            if (num.count(".") >= 2 or num.count(",") >= 2 or len(num) >= 7)
            else ""
        )
        if (
            num not in combined_context
            and num_dot not in combined_context
            and num_comma not in combined_context
            and (not raw_digits or raw_digits not in combined_context)
        ):
            unsupported.append(num)

    return unsupported


def _compute_sentence_groundedness_ratio(
    answer: str, combined_context: str
) -> float:
    """Measure what ratio of factual statements in the answer are grounded in context.

    Excludes introductory adverbial framing and source meta headers via syntactic parsing.
    """
    if not answer.strip() or not combined_context.strip():
        return 1.0

    raw_sentences = [
        s.strip()
        for s in re.split(r"(?<!\d)[.!?;\n]+(?!\d)", answer)
        if len(s.strip()) > 8
    ]
    if not raw_sentences:
        return 1.0

    sentences: list[str] = []
    for s in raw_sentences:
        s_lower = s.lower().strip()
        # Filter framing sentences using syntactic pattern
        if len(s.split()) <= 18 and _SYNTACTIC_FRAMING_PATTERN.search(s_lower):
            continue
        sentences.append(s)

    if not sentences:
        return 1.0

    grounded_count = 0
    for sent in sentences:
        words = [w.lower() for w in re.findall(r"\b\w{2,}\b", sent)]
        if not words:
            continue
        matching_words = [w for w in words if w in combined_context]
        overlap_ratio = len(matching_words) / len(words)
        if overlap_ratio >= 0.40:
            grounded_count += 1

    return round(grounded_count / len(sentences), 3)


class CitationGuardNodeHandler(BaseNodeHandler):
    """Verifies that generated answers contain legitimate citations from QNU official documents

    and prevents numerical hallucinations before sending responses to users.
    """

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        config = node_spec.config or {}
        profile = context.assistant_profile
        require_citation = (
            profile.output_policy.require_citations
            if profile
            else config.get("require_citation_for_answer", True)
        )
        accepted_statuses = config.get("accepted_statuses", ["answered", "success"])
        invalid_route = config.get("invalid_route", "ungrounded")

        rag_status = context.node_data.get("rag_status") or context.outputs.get(
            "status", "answered"
        )
        citations = context.node_data.get("citations") or context.outputs.get(
            "citations", []
        )
        answer_text = context.node_data.get("rag_answer") or context.outputs.get(
            "answer", ""
        )

        is_grounded = True
        failure_reasons: list[str] = []

        # Check 1: Status must be valid
        if rag_status not in accepted_statuses:
            is_grounded = False
            failure_reasons.append(f"rag_status '{rag_status}' not in accepted")

        if (
            profile
            and profile.guardrails.require_grounded_answer
            and rag_status != "answered"
        ):
            is_grounded = False
            failure_reasons.append("require_grounded_answer set and status != answered")

        # Check 2: Answer must not be empty
        if not answer_text or not answer_text.strip():
            is_grounded = False
            failure_reasons.append("answer text is empty")

        # Check 3: If citations required, verify non-empty citations
        if require_citation and len(citations) == 0:
            is_grounded = False
            failure_reasons.append("citations list is empty")

        # Check 4: If answer itself declares insufficient context, treat as ungrounded
        if (
            "chưa có trong" in answer_text.lower()
            or "không tìm thấy" in answer_text.lower()
        ) and len(citations) == 0:
            is_grounded = False
            failure_reasons.append("answer self-declares lack of context")

        # Check 5: Mathematical Number Hallucination Detection (0ms)
        combined_context = _gather_combined_context(context, citations)
        unsupported_numbers: list[str] = []
        grounded_ratio = 1.0

        if is_grounded and combined_context and answer_text:
            unsupported_numbers = _detect_number_hallucinations(
                answer_text, combined_context
            )
            if unsupported_numbers:
                is_grounded = False
                failure_reasons.append(
                    f"Unsupported numbers detected: {', '.join(unsupported_numbers)}"
                )
                logger.warning(
                    "CitationGuard [%s]: Detected number hallucination: %s",
                    node_spec.id,
                    unsupported_numbers,
                )

            # Check 6: Sentence-level lexical groundedness ratio
            grounded_ratio = _compute_sentence_groundedness_ratio(
                answer_text, combined_context
            )
            if grounded_ratio < 0.25 and len(citations) > 0:
                is_grounded = False
                failure_reasons.append(
                    f"Sentence groundedness ratio too low ({grounded_ratio} < 0.25)"
                )
                logger.warning(
                    "CitationGuard [%s]: Low groundedness ratio %.2f",
                    node_spec.id,
                    grounded_ratio,
                )

        context.node_data["is_grounded"] = is_grounded
        context.node_data["unsupported_numbers"] = unsupported_numbers
        context.node_data["grounded_ratio"] = grounded_ratio
        selected_port = "grounded" if is_grounded else invalid_route

        logger.info(
            "CitationGuard [%s]: is_grounded=%s, citations=%d, port=%s, reasons=%s",
            node_spec.id,
            is_grounded,
            len(citations),
            selected_port,
            failure_reasons or ["all checks passed"],
        )

        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={
                "is_grounded": is_grounded,
                "grounded": answer_text,
                "ungrounded": " ".join(failure_reasons) if failure_reasons else "Thiếu căn cứ dữ liệu chính thức.",
                "response": answer_text,
                "answer": answer_text,
                "citations_count": len(citations),
                "port": selected_port,
                "unsupported_numbers": unsupported_numbers,
                "grounded_ratio": grounded_ratio,
                "failure_reasons": failure_reasons,
            },
            selected_port=selected_port,
        )
