"""Unit Tests for Continuous Quality Evaluation (Ragas TM-08 Standard)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import NotFoundException
from app.main import app
from app.modules.evaluation.evaluator import RagasTM08Evaluator
from app.modules.evaluation.schemas import EvaluationRunRequest
from app.modules.evaluation.service import EvaluationService


def test_ragas_evaluator_faithfulness():
    evaluator = RagasTM08Evaluator()
    contexts = [
        "Mã cơ sở đào tạo của Trường Đại học Quy Nhơn trong kỳ thi tuyển sinh đại học chính quy là DQN.",
        "Trường có trụ sở chính đặt tại thành phố Quy Nhơn.",
    ]

    # Grounded answer
    answer_grounded = "Mã cơ sở đào tạo của Trường Đại học Quy Nhơn là DQN."
    faith_score = evaluator.compute_faithfulness(answer_grounded, contexts)
    assert faith_score >= 0.90

    # No-Answer policy compliant answer
    answer_no_answer = "Hiện tại chưa có thông tin chính thức trong tài liệu, vui lòng liên hệ hotline 0256.3846.156."
    faith_no_answer = evaluator.compute_faithfulness(answer_no_answer, [])
    assert faith_no_answer == 1.0

    # Empty answer
    assert evaluator.compute_faithfulness("", contexts) == 0.0


def test_ragas_evaluator_answer_relevance():
    evaluator = RagasTM08Evaluator()
    query = "Mã cơ sở đào tạo của Trường Đại học Quy Nhơn là gì?"
    answer = "Mã cơ sở đào tạo chính thức của Trường Đại học Quy Nhơn trong kỳ tuyển sinh là DQN."

    relevance = evaluator.compute_answer_relevance(query, answer)
    assert relevance >= 0.85

    # Completely off-topic answer
    relevance_offtopic = evaluator.compute_answer_relevance(query, "Hôm nay thời tiết đẹp trời nhiều mây.")
    assert relevance_offtopic < 0.60


def test_ragas_evaluator_context_precision():
    evaluator = RagasTM08Evaluator()
    ground_truth = "Mã cơ sở đào tạo của Trường Đại học Quy Nhơn là DQN."
    contexts = [
        "Trường Đại học Quy Nhơn công bố mã cơ sở đào tạo DQN.",
        "Danh sách học bổng học kỳ I dành cho sinh viên xuất sắc.",
    ]

    precision = evaluator.compute_context_precision(ground_truth, contexts)
    assert precision >= 0.50


def test_ragas_evaluator_hallucination_detection():
    evaluator = RagasTM08Evaluator()
    contexts = ["Điểm chuẩn trúng tuyển ngành Công nghệ thông tin là 24.5 điểm."]

    # Non-hallucinated
    assert evaluator.detect_hallucination("Điểm chuẩn là 24.5 điểm.", contexts) is False

    # Hallucinated new unsupported number
    assert evaluator.detect_hallucination("Điểm chuẩn là 29.85 điểm.", contexts) is True


def test_evaluation_service_datasets():
    service = EvaluationService()
    datasets = service.list_datasets()
    assert len(datasets) >= 2

    admissions_ds = next(d for d in datasets if d.id == "qnu_admissions_benchmark")
    assert admissions_ds.assistant_code == "admissions_assistant"
    assert admissions_ds.total_test_cases >= 5

    cases = service.get_dataset_test_cases("qnu_admissions_benchmark")
    assert len(cases) >= 5
    assert cases[0].question != ""

    with pytest.raises(NotFoundException):
        service.get_dataset_test_cases("non_existent_dataset")


@pytest.mark.asyncio
async def test_evaluation_service_run():
    service = EvaluationService()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    req = EvaluationRunRequest(
        assistant_code="admissions_assistant",
        dataset_id="qnu_admissions_benchmark",
        sample_size=2,
    )
    res = await service.run_evaluation(mock_session, req)

    assert res.status == "completed"
    assert res.total_cases == 2
    assert res.faithfulness_avg >= 0.90
    assert res.answer_relevance_avg >= 0.85
    assert res.meets_tm08_standard is True


@pytest.mark.asyncio
async def test_api_evaluation_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp_ds = await client.get("/platform/v1alpha1/evaluation/datasets")
        assert resp_ds.status_code == 200
        data_ds = resp_ds.json()
        assert len(data_ds) >= 2

        resp_cases = await client.get("/platform/v1alpha1/evaluation/datasets/qnu_admissions_benchmark/cases")
        assert resp_cases.status_code == 200
        assert len(resp_cases.json()) >= 5
