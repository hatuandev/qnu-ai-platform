"""DTOs for OCR processing runs and their evidence."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from qnu.domains.ocr.models import ACTIVE_RUN_STATUSES, OcrProcessingRun


class ProcessingRunRequest(BaseModel):
    """Optional provider and rendering density; effective limits stay server-side."""

    model_config = ConfigDict(extra="forbid")

    provider_id: str | None = Field(None, min_length=1, max_length=64)
    strategy: Literal["ocr", "auto"] = "ocr"
    render_dpi: int | None = Field(None, ge=72, le=300)
    force: bool = Field(
        False,
        description=(
            "Tạo thế hệ xử lý mới kể cả khi đã có kết quả hoàn tất tương thích. "
            "Mặc định tái sử dụng kết quả cũ để không gọi lại provider vô ích."
        ),
    )


class ProcessingRunResponse(BaseModel):
    id: str
    workspace_id: str
    collection_id: str
    source_id: str
    revision_id: str
    revision_no: int
    generation: int
    status: str
    provider_id: str | None = None
    pages_total: int | None = None
    pages_done: int = 0
    pages_failed: int = 0
    attempt_count: int = 0
    max_attempts: int = 2
    error_code: str | None = None
    error_detail: str | None = None
    requested_by: str
    requested_at: datetime
    dispatched_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    usage_tokens: int | None = None
    config_fingerprint: str
    dispatch_pending: bool = False
    strategy: str = "ocr"
    results_ready: bool = False

    @classmethod
    def from_run(cls, run: OcrProcessingRun) -> ProcessingRunResponse:
        return cls(
            id=run.id,
            workspace_id=run.workspace_id,
            collection_id=run.collection_id,
            source_id=run.source_id,
            revision_id=run.revision_id,
            revision_no=run.revision_no,
            generation=run.generation,
            status=run.status,
            provider_id=run.provider_id,
            pages_total=run.pages_total,
            pages_done=run.pages_done,
            pages_failed=run.pages_failed,
            attempt_count=run.attempt_count,
            max_attempts=run.max_attempts,
            error_code=run.error_code,
            error_detail=run.error_detail,
            requested_by=run.requested_by,
            requested_at=run.requested_at,
            dispatched_at=run.dispatched_at,
            started_at=run.started_at,
            finished_at=run.finished_at,
            usage_tokens=run.usage_tokens,
            config_fingerprint=run.config_fingerprint,
            dispatch_pending=run.status in ACTIVE_RUN_STATUSES and run.dispatched_at is None,
            strategy=(run.config or {}).get("extraction", {}).get("strategy", "ocr"),
            results_ready=run.status == "completed",
        )


class ProcessingRunCreatedResponse(BaseModel):
    run: ProcessingRunResponse
    created: bool
    dispatched: bool


class PageStatusResponse(BaseModel):
    page_number: int
    status: str
    used_ocr: bool = False
    image_sha256: str | None = None
    blocks_count: int = 0
    has_tables: bool = False
    error_code: str | None = None
    usage_tokens: int | None = None


class ProcessingRunDetailResponse(ProcessingRunResponse):
    pages: list[PageStatusResponse] = Field(default_factory=list)


class EvidenceSnapshotResponse(BaseModel):
    """Read-only, pinned evidence bundle for a later Compiler."""

    run_id: str
    generation: int
    status: str
    identity: dict[str, Any]
    processing: dict[str, Any]
    canonical_sha256: str
    manifest_sha256: str | None = None
    checks: dict[str, Any]
    validation: dict[str, Any]
    artifacts: list[dict[str, Any]]
    pages: list[dict[str, Any]]
    evidence: dict[str, Any]
