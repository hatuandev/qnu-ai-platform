"""Operations reveal identifiers and observed progress, never prompts or credentials."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

JobKind = Literal["ocr", "compiler", "index", "auto_review", "review", "spelling", "turn", "backup"]


class JobView(BaseModel):
    kind: JobKind
    id: str
    workspace_id: str
    collection_id: str | None
    source_id: str | None = None
    revision_id: str | None = None
    compilation_run_id: str | None = None
    status: str
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    lease_expires_at: datetime | None = None
    error_code: str | None = None
    attempts: int | None = None
    progress_done: int | None = None
    progress_total: int | None = None
    usage_tokens: int | None = None
    provider_id: str | None = None
    recovery_allowed: bool = False
    recovery_reason: str


class RecoveryPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    reason: str = Field(min_length=1, max_length=2000)


class ActionAccept(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    preview_id: str = Field(min_length=1, max_length=64)
    preview_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class ActionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workspace_id: str
    kind: str
    job_id: str
    action: str
    reason: str
    preview_sha256: str
    status: str
    expires_at: datetime
    dispatched_at: datetime | None


class BackupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    retention_days: int | None = Field(None, ge=1, le=36500)


class BackupView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workspace_id: str
    status: str
    created_at: datetime
    finished_at: datetime | None
    retain_until: datetime | None
    sha256: str | None
    size_bytes: int | None
    error_code: str | None


class SystemResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    confirm_phrase: str = Field(..., description="Phải nhập chính xác 'RESET_AND_SEED'")
    seed_workspace: bool = Field(default=True, description="Tự động nạp workspace SHL mặc định")
    seed_modelops: bool = Field(default=True, description="Tự động nạp cấu hình ModelOps mặc định")
    seed_assistant: bool = Field(default=True, description="Tự động tạo Trợ lý Tuyển sinh 2026 mẫu")


class SystemResetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    success: bool
    message: str
    workspace_id: str | None = None
    assistant_id: str | None = None
    stats: dict[str, object] = Field(default_factory=dict)

