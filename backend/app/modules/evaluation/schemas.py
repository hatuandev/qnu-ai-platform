"""Pydantic Schemas for Continuous Evaluation (Ragas TM-08 Standard)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EvaluationRunRequest(BaseModel):
    assistant_code: str = Field(..., description="Mã trợ lý cần đánh giá (ví dụ: admissions hoặc regulations)")
    dataset_id: str = Field("qnu_admissions_benchmark", description="Mã tập benchmark")
    sample_size: int | None = Field(None, description="Số câu hỏi muốn chạy mẫu (None = chạy tất cả)", ge=1)


class EvaluationResultItemResponse(BaseModel):
    id: str
    test_case_id: str
    query: str
    generated_answer: str
    contexts: list[str] = Field(default_factory=list)
    faithfulness_score: float = Field(..., description="Độ trung thực bám sát ngữ cảnh (Grounding)")
    answer_relevance_score: float = Field(..., description="Độ liên quan với câu hỏi người dùng")
    context_precision_score: float = Field(..., description="Độ chính xác của ngữ cảnh RAG")
    is_hallucinated: bool = Field(..., description="Phát hiện bịa đặt dữ liệu ngoài ngữ cảnh")
    passed_all_criteria: bool

    model_config = {"from_attributes": True}


class EvaluationRunResponse(BaseModel):
    id: str
    dataset_id: str
    assistant_code: str
    status: str
    total_cases: int
    passed_cases: int
    pass_rate: float
    faithfulness_avg: float = Field(..., description="Điểm trung bình Faithfulness (chuẩn >= 0.90)")
    answer_relevance_avg: float = Field(..., description="Điểm trung bình Answer Relevance (chuẩn >= 0.85)")
    context_precision_avg: float = Field(..., description="Điểm trung bình Context Precision (chuẩn >= 0.80)")
    meets_tm08_standard: bool = Field(..., description="Đạt chuẩn kiểm định Ragas TM-08")
    metadata_info: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class TestCaseResponse(BaseModel):
    id: str
    dataset_id: str
    question: str
    ground_truth: str
    expected_source: str
    keywords: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class DatasetResponse(BaseModel):
    id: str
    name: str
    description: str
    assistant_code: str
    total_test_cases: int

    model_config = {"from_attributes": True}
