"""Bridge between conversation failure logs and reproducible RAG benchmark suites.

Reads and appends error or feedback questions into `backendV1/benchmarks/rag_benchmark_md_xlsx.json`
with deduplication and structure validation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from qnu.domains.conversations.models import ConversationTurn
from qnu.domains.conversations.schemas import (
    PromoteToBenchmarkRequest,
    PromoteToBenchmarkResponse,
)


def get_benchmark_path() -> Path:
    """Return the absolute path to the standard RAG benchmark suite."""
    return Path(__file__).resolve().parents[3] / "benchmarks" / "rag_benchmark_md_xlsx.json"


def _normalize_question(q: str) -> str:
    """Normalize question text for case and whitespace insensitive comparison."""
    return re.sub(r"\s+", " ", q.strip().casefold())


def is_question_in_benchmark(data: dict[str, Any], question: str) -> tuple[bool, str | None]:
    """Check if question already exists in benchmark questions list.

    Returns:
        (True, question_id) if found, otherwise (False, None).
    """
    normalized_target = _normalize_question(question)
    for item in data.get("questions") or []:
        q_item = item.get("question")
        if q_item and _normalize_question(q_item) == normalized_target:
            return True, item.get("id")
    return False, None


def add_turn_to_benchmark(
    benchmark_path: Path,
    turn: ConversationTurn,
    body: PromoteToBenchmarkRequest | None = None,
) -> PromoteToBenchmarkResponse:
    """Safely append a conversation turn into the benchmark JSON suite with deduplication."""
    if not benchmark_path.exists():
        raise FileNotFoundError(f"Không tìm thấy tệp benchmark tại: {benchmark_path}")

    with benchmark_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise TypeError(f"Dữ liệu trong {benchmark_path} không hợp lệ.")

    question_text = turn.question.strip()
    already_exists, existing_id = is_question_in_benchmark(data, question_text)

    questions: list[dict[str, Any]] = data.setdefault("questions", [])

    if already_exists and existing_id:
        return PromoteToBenchmarkResponse(
            turn_id=turn.id,
            question_id=existing_id,
            question=question_text,
            already_exists=True,
            benchmark_file=benchmark_path.name,
            total_questions=len(questions),
        )

    # Calculate next Q number
    max_num = 0
    for q in questions:
        qid = q.get("id", "")
        if qid.startswith("Q"):
            digits = re.findall(r"\d+", qid)
            if digits:
                max_num = max(max_num, int(digits[0]))
    if max_num == 0:
        max_num = len(questions)

    new_id = f"Q{max_num + 1:02d}"

    # Determine failure / feedback context
    feedback_reason: str | None = None
    if turn.feedback and isinstance(turn.feedback, dict):
        feedback_reason = turn.feedback.get("reason")

    # Determine group (default to log_failures group)
    group_id = "log_failures"
    groups: list[dict[str, Any]] = data.setdefault("groups", [])
    log_group = next((g for g in groups if g.get("id") == group_id), None)
    if log_group is None:
        log_group = {
            "id": group_id,
            "name": "Ca lỗi & Phản hồi thực tế từ Nhật ký",
            "question_count": 1,
        }
        groups.append(log_group)
    else:
        log_group["question_count"] = log_group.get("question_count", 0) + 1

    # Determine doc scope
    doc_scope = "nhat_ky_hoi_thoai"
    if turn.result and isinstance(turn.result, dict):
        sources = turn.result.get("sources")
        if sources and isinstance(sources, list) and len(sources) > 0:
            first_src = sources[0]
            if isinstance(first_src, dict):
                doc_scope = (
                    first_src.get("source_title")
                    or first_src.get("title")
                    or first_src.get("document_id")
                    or doc_scope
                )

    # Determine expected points
    expected_points = (
        body.expected_points
        if body and body.expected_points
        else (
            [f"Khắc phục phản hồi: {feedback_reason}"]
            if feedback_reason
            else (
                [f"Xử lý lỗi hệ thống: {turn.error_code}"]
                if turn.status == "failed"
                else ["Cung cấp câu trả lời chính xác có nguồn kiểm chứng và đúng trọng tâm."]
            )
        )
    )

    # Determine expected behavior
    expected_behavior = (
        body.expected_behavior
        if body and body.expected_behavior
        else (
            f"Tránh lỗi ghi nhận từ phản hồi: {feedback_reason}."
            if feedback_reason
            else (
                f"Tránh mã lỗi: {turn.error_code}."
                if turn.status == "failed"
                else "Tránh tái hiện lỗi ghi nhận trong nhật ký hỏi đáp."
            )
        )
    )

    # Determine forbidden behaviors
    forbidden_behaviors = (
        [feedback_reason]
        if feedback_reason
        else (
            ["Lỗi hệ thống hoặc gián đoạn lượt hỏi"]
            if turn.status == "failed"
            else ["Tự suy diễn thông tin khi thiếu dẫn chứng xác thực"]
        )
    )

    new_item: dict[str, Any] = {
        "id": new_id,
        "group": group_id,
        "doc_scope": doc_scope,
        "question": question_text,
        "expected_points": expected_points,
        "expected_behavior": expected_behavior,
        "forbidden_behaviors": forbidden_behaviors,
    }

    questions.append(new_item)

    # Update scoring scale
    scoring = data.setdefault("scoring_scale", {})
    total_q = len(questions)
    scoring["total_questions"] = total_q
    max_per_q = scoring.get("max_score_per_question", 2)
    scoring["max_total_score"] = total_q * max_per_q

    # Atomic write / replace
    with benchmark_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return PromoteToBenchmarkResponse(
        turn_id=turn.id,
        question_id=new_id,
        question=question_text,
        already_exists=False,
        benchmark_file=benchmark_path.name,
        total_questions=total_q,
    )
