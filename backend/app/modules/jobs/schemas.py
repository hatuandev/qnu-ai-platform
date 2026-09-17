"""Pydantic Schemas & DTOs for Background Job Management."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class JobEnqueueRequest(BaseModel):
    job_type: str = Field(..., description="Loại job: ingestion, reindex, export")
    collection_id: str | None = Field(None, max_length=64)
    document_id: str | None = Field(None, max_length=64)
    params: dict[str, Any] = Field(default_factory=dict)


class JobResponse(BaseModel):
    id: str
    job_type: str
    status: str
    collection_id: str | None = None
    document_id: str | None = None
    arq_job_id: str | None = None
    progress: float
    payload: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobStatsResponse(BaseModel):
    total: int
    queued: int
    running: int
    completed: int
    failed: int
    cancelled: int
