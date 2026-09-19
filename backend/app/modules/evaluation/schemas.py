"""Pydantic Schemas for Continuous Evaluation (Ragas TM-08 Standard)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EvaluationRunRequest(BaseModel):
    assistant_code: str = Field(..., description="Mã trợ lý cần đánh giá (ví dụ: admissions hoặc regulations)")
    dataset_id: str = Field("qnu_admissions_benchmark", description="Mã tập benchmark")
    sample_size: int | None = Field(None, description="Số câu hỏi muốn chạy mẫu (None = chạy tất cả)", ge=1)
    evaluation_method: str = Field("heuristic", description="Phương pháp đánh giá: 'heuristic' hoặc 'llm_judge'")


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
    is_refusal: bool = Field(False, description="Kích hoạt No-Answer Policy / Từ chối do thiếu căn cứ")
    passed_all_criteria: bool
    execution_path: str = Field("assistant_workflow", description="Đường dẫn thực thi (assistant_workflow hoặc rag_service_fallback)")
    reasoning: str | None = Field(None, description="Nhận xét / Giải thích chi tiết điểm số")

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
    evaluation_method: str = Field("heuristic", description="Phương pháp đánh giá đã dùng")
    metadata_info: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class EvaluationRunDetailResponse(EvaluationRunResponse):
    items: list[EvaluationResultItemResponse] = Field(default_factory=list)


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


class KnowledgeGapResponse(BaseModel):
    id: str
    assistant_code: str
    collection_id: str | None = None
    question: str
    frequency: int = 1
    status: str
    resolution_notes: str | None = None
    resolved_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeGapResolveRequest(BaseModel):
    status: str = Field("resolved", description="Trạng thái mới: resolved hoặc dismissed")
    resolution_notes: str | None = Field(None, max_length=1000, description="Ghi chú về văn bản nạp bổ sung")
    resolved_by: str | None = Field("can_bo_phu_trach", max_length=100)
