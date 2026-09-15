"""API Router for Continuous Quality Evaluation (Ragas TM-08 Standard)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.evaluation.schemas import (
    DatasetResponse,
    EvaluationRunRequest,
    EvaluationRunResponse,
    TestCaseResponse,
)
from app.modules.evaluation.service import EvaluationService

router = APIRouter(prefix="/evaluation", tags=["Continuous Evaluation (Ragas TM-08)"])
service = EvaluationService()


@router.get("/datasets", response_model=list[DatasetResponse])
async def list_datasets() -> list[DatasetResponse]:
    """Danh sách các bộ dữ liệu kiểm định chuẩn RAG (Tuyển sinh, Quy chế học vụ)."""
    return service.list_datasets()


@router.get("/datasets/{dataset_id}/cases", response_model=list[TestCaseResponse])
async def get_dataset_cases(dataset_id: str) -> list[TestCaseResponse]:
    """Xem danh sách các câu hỏi kiểm định và kết quả kỳ vọng trong tập dữ liệu."""
    return service.get_dataset_test_cases(dataset_id)


@router.post("/evaluate", response_model=EvaluationRunResponse)
async def run_evaluation(
    request: EvaluationRunRequest,
    session: AsyncSession = Depends(get_db),
) -> EvaluationRunResponse:
    """Kích hoạt phiên kiểm định chất lượng Ragas TM-08 (Faithfulness, Relevance, Precision)."""
    return await service.run_evaluation(session=session, request=request)


@router.get("/runs", response_model=list[EvaluationRunResponse])
async def list_evaluation_runs(
    assistant_code: str | None = Query(None, description="Lọc theo mã trợ lý"),
    session: AsyncSession = Depends(get_db),
) -> list[EvaluationRunResponse]:
    """Xem lịch sử các lần kiểm định chất lượng định kỳ và sự suy giảm độ chính xác (Drift)."""
    return await service.list_runs(session=session, assistant_code=assistant_code)
