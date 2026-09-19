"""Unit tests for truthful continuous evaluation (TM-08 standard)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.assistants.readiness import AssistantReadinessEngine
from app.modules.evaluation.evaluator import (
    HeuristicTM08Evaluator,
    LLMJudgeTM08Evaluator,
    get_evaluator,
)
from app.modules.evaluation.models import EvaluationResultItem, EvaluationRun
from app.modules.evaluation.schemas import EvaluationRunRequest
from app.modules.evaluation.service import EvaluationService
from app.modules.modelops.schemas import LLMGenerateResponse


@pytest.mark.asyncio
async def test_run_evaluation_persists_result_items_to_database() -> None:
    """Test run_evaluation saves both EvaluationRun and EvaluationResultItem records."""
    service = EvaluationService()

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    request = EvaluationRunRequest(
        assistant_code="admissions",
        dataset_id="qnu_admissions_benchmark",
        sample_size=2,
        evaluation_method="heuristic",
    )

    with patch("app.modules.assistants.service.assistant_service.chat", new_callable=AsyncMock) as mock_chat:
        mock_chat_res = MagicMock()
        mock_chat_res.answer = "Điểm chuẩn ngành Sư phạm Toán năm 2024 là 26.5 điểm."
        mock_chat_res.citations = [{"quote": "Điểm chuẩn Sư phạm Toán năm 2024: 26.5 điểm."}]
        mock_chat.return_value = mock_chat_res

        res = await service.run_evaluation(mock_session, request)

        assert res.total_cases == 2
        assert res.evaluation_method == "heuristic"
        assert res.status == "completed"

        # Verify items and run were added to session
        added_objects = [call.args[0] for call in mock_session.add.call_args_list]
        runs_added = [obj for obj in added_objects if isinstance(obj, EvaluationRun)]
        items_added = [obj for obj in added_objects if isinstance(obj, EvaluationResultItem)]

        assert len(runs_added) == 1
        assert len(items_added) == 2
        assert items_added[0].run_id == res.id
        assert items_added[0].execution_path == "assistant_workflow"
        assert items_added[0].faithfulness_score >= 0.90
        assert mock_session.commit.called


@pytest.mark.asyncio
async def test_get_run_detail_and_items() -> None:
    """Test querying run detail including full list of question evaluation items."""
    service = EvaluationService()
    mock_session = AsyncMock()

    from datetime import UTC, datetime

    mock_run = EvaluationRun(
        id="run_123",
        dataset_id="qnu_admissions_benchmark",
        assistant_code="admissions",
        status="completed",
        total_cases=1,
        passed_cases=1,
        pass_rate=1.0,
        faithfulness_avg=0.95,
        answer_relevance_avg=0.90,
        context_precision_avg=0.85,
        meets_tm08_standard=True,
        evaluation_method="heuristic",
        metadata_info={},
        created_at=datetime.now(UTC).replace(tzinfo=None),
        completed_at=datetime.now(UTC).replace(tzinfo=None),
    )

    mock_item = EvaluationResultItem(
        id="item_001",
        run_id="run_123",
        test_case_id="tc_1",
        query="Điểm chuẩn sư phạm toán?",
        generated_answer="26.5 điểm",
        contexts=["Sư phạm toán: 26.5"],
        faithfulness_score=0.95,
        answer_relevance_score=0.90,
        context_precision_score=0.85,
        is_hallucinated=False,
        is_refusal=False,
        passed_all_criteria=True,
        execution_path="assistant_workflow",
        reasoning="Đạt chuẩn TM-08.",
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )

    # Mock scalars().all() and scalar_one_or_none()
    run_exec_result = MagicMock()
    run_exec_result.scalar_one_or_none.return_value = mock_run

    items_exec_result = MagicMock()
    items_exec_result.scalars.return_value.all.return_value = [mock_item]

    mock_session.execute.side_effect = [run_exec_result, items_exec_result]

    detail = await service.get_run_detail(mock_session, "run_123")
    assert detail.id == "run_123"
    assert len(detail.items) == 1
    assert detail.items[0].query == "Điểm chuẩn sư phạm toán?"
    assert detail.items[0].faithfulness_score == 0.95


def test_evaluator_penalizes_relevance_on_refusal_when_ground_truth_exists() -> None:
    """Test that safety refusal gets 100% faithfulness but is penalized in relevance when answerable."""
    evaluator = HeuristicTM08Evaluator()

    query = "Học phí ngành Công nghệ thông tin là bao nhiêu?"
    ground_truth = "Học phí ngành Công nghệ thông tin là 18.500.000 VNĐ mỗi năm học theo quy định."
    refusal_answer = "Xin lỗi, hiện tại tôi chưa có thông tin về nội dung này. Vui lòng liên hệ phòng Đào tạo qua hotline 0256.3846.156."
    contexts = ["Khoa CNTT ĐH Quy Nhơn đào tạo kỹ sư công nghệ."]

    res = evaluator.evaluate_item(
        query=query,
        ground_truth=ground_truth,
        answer=refusal_answer,
        contexts=contexts,
    )

    assert res["is_refusal"] is True
    assert res["faithfulness"] == 1.0  # Not a hallucination
    assert res["answer_relevance"] <= 0.20  # Penalized because question had factual answer
    assert res["passed"] is False
    assert "Từ chối trả lời" in res["reasoning"]


def test_evaluator_passes_when_refusal_is_expected() -> None:
    """Test that refusal gets high relevance when ground truth is also a refusal/unsupported."""
    evaluator = HeuristicTM08Evaluator()

    query = "Năm 2030 trường có mở ngành hàng không không?"
    ground_truth = "Hiện tại chưa có thông tin quy định về ngành này trong đề án."
    answer = "Xin lỗi, hiện tại chưa có thông tin về nội dung này."
    contexts: list[str] = []

    res = evaluator.evaluate_item(
        query=query,
        ground_truth=ground_truth,
        answer=answer,
        contexts=contexts,
    )

    assert res["is_refusal"] is True
    assert res["faithfulness"] == 1.0
    assert res["answer_relevance"] >= 0.80


@pytest.mark.asyncio
async def test_llm_judge_evaluator_scores_with_reasoning() -> None:
    """Test LLMJudgeTM08Evaluator calls ModelOps and extracts JSON rubric scoring."""
    evaluator = LLMJudgeTM08Evaluator()
    mock_session = AsyncMock()

    mock_llm_json = json.dumps({
        "faithfulness": 0.96,
        "answer_relevance": 0.92,
        "context_precision": 0.88,
        "is_hallucinated": False,
        "is_refusal": False,
        "reasoning": "Câu trả lời trích dẫn chính xác điểm số từ Quyết định tuyển sinh.",
    })

    with patch("app.modules.modelops.service.modelops_service.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = LLMGenerateResponse(
            content=f"```json\n{mock_llm_json}\n```",
            provider="openai",
            model="gpt-4o-mini",
            prompt_tokens=150,
            completion_tokens=60,
            total_tokens=210,
        )

        res = await evaluator.evaluate_item_async(
            session=mock_session,
            query="Điểm chuẩn Sư phạm Toán 2024?",
            ground_truth="26.5 điểm",
            answer="Điểm chuẩn năm 2024 là 26.5 điểm.",
            contexts=["Sư phạm Toán: 26.5 điểm"],
        )

        assert res["faithfulness"] == 0.96
        assert res["answer_relevance"] == 0.92
        assert res["context_precision"] == 0.88
        assert res["passed"] is True
        assert "[LLM-Judge]" in res["reasoning"]


@pytest.mark.asyncio
async def test_publish_gate_evaluates_latest_run_properly() -> None:
    """Test Publish Gate engine checks latest evaluation run metrics accurately."""
    engine = AssistantReadinessEngine()
    mock_session = AsyncMock()

    mock_run = EvaluationRun(
        id="run_pass_001",
        dataset_id="qnu_admissions_benchmark",
        assistant_code="admissions",
        status="completed",
        total_cases=10,
        passed_cases=9,
        pass_rate=0.90,
        faithfulness_avg=0.94,
        answer_relevance_avg=0.89,
        context_precision_avg=0.85,
        meets_tm08_standard=True,
        evaluation_method="heuristic",
    )

    exec_res = MagicMock()
    exec_res.scalar_one_or_none.return_value = mock_run
    mock_session.execute.return_value = exec_res

    item, blocker, _warning = await engine._check_evaluation(mock_session, "admissions")
    assert item.status == "passed"
    assert item.score == 100
    assert blocker is None
    assert _warning is None
    assert "Đạt chuẩn TM-08" in item.message
    assert item.details["evaluation_method"] == "heuristic"
    assert item.details["passed_cases"] == 9


def test_factory_returns_correct_evaluator() -> None:
    """Test get_evaluator factory returns expected instance."""
    assert isinstance(get_evaluator("heuristic"), HeuristicTM08Evaluator)
    assert isinstance(get_evaluator("llm_judge"), LLMJudgeTM08Evaluator)
    assert isinstance(get_evaluator("unknown"), HeuristicTM08Evaluator)
