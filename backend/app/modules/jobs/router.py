"""FastAPI Router for Background Job Management — Thin Controller Pattern."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.jobs.schemas import JobEnqueueRequest, JobResponse, JobStatsResponse
from app.modules.jobs.service import jobs_service

router = APIRouter(prefix="/jobs", tags=["Background Jobs"])


@router.post("", response_model=JobResponse, summary="Tạo Job nền mới (ingestion/reindex/export)")
async def enqueue_job(
    body: JobEnqueueRequest,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    job = await jobs_service.enqueue_job(
        db,
        job_type=body.job_type,
        collection_id=body.collection_id,
        document_id=body.document_id,
        params=body.params,
    )
    return JobResponse.model_validate(job)


@router.get("", response_model=list[JobResponse], summary="Danh sách Jobs nền")
async def list_jobs(
    status: str | None = Query(None, description="Lọc theo trạng thái"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[JobResponse]:
    jobs = await jobs_service.list_jobs(db, status=status, limit=limit)
    return [JobResponse.model_validate(j) for j in jobs]


@router.get("/stats", response_model=JobStatsResponse, summary="Thống kê Jobs theo trạng thái")
async def job_stats(db: AsyncSession = Depends(get_db)) -> JobStatsResponse:
    return JobStatsResponse.model_validate(await jobs_service.get_stats(db))


@router.get("/{job_id}", response_model=JobResponse, summary="Chi tiết Job")
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    job = await jobs_service.get_job(db, job_id)
    return JobResponse.model_validate(job)


@router.post("/{job_id}/cancel", response_model=JobResponse, summary="Hủy Job (cooperative)")
async def cancel_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    job = await jobs_service.cancel_job(db, job_id)
    return JobResponse.model_validate(job)


@router.post("/{job_id}/retry", response_model=JobResponse, summary="Chạy lại Job failed/cancelled")
async def retry_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    job = await jobs_service.retry_job(db, job_id)
    return JobResponse.model_validate(job)


@router.delete("/cleanup", summary="Dọn dẹp các Jobs đã kết thúc (completed/cancelled/failed)")
async def cleanup_jobs(
    collection_id: str | None = Query(None, description="Lọc theo collection_id"),
    statuses: str = Query(
        "completed,cancelled,failed",
        description="Danh sách trạng thái cần dọn dẹp, phân tách bằng dấu phẩy",
    ),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    status_list = [s.strip() for s in statuses.split(",") if s.strip()]
    count = await jobs_service.cleanup_jobs(db, collection_id=collection_id, statuses=status_list)
    return {"success": True, "deleted_count": count}


@router.delete("/{job_id}", summary="Xóa vĩnh viễn Job khỏi danh sách")
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await jobs_service.delete_job(db, job_id)
    return {"success": True, "deleted_id": job_id}

