"""Durable backup catalogue, deliberately outside the database being protected."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class BackupOperation(BaseModel):
    timestamp: datetime
    operation: Literal["create", "verify", "drill", "import", "copy"]
    status: Literal["queued", "running", "completed", "failed", "unverified"]
    actor_id: str
    correlation_id: str
    error: str | None = None


class BackupRecord(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    actor_id: str
    correlation_id: str
    operation: Literal["create", "verify", "drill", "import", "copy"] = "create"
    status: Literal["queued", "running", "completed", "failed", "unverified"] = "queued"
    stage: str = "Chờ tiến trình sao lưu"
    progress: int = Field(default=0, ge=0, le=100)
    size_bytes: int = 0
    sha256: str | None = None
    verified_at: datetime | None = None
    drill_at: datetime | None = None
    error: str | None = None
    pid: int | None = None
    components: dict = Field(default_factory=dict)
    history: list[BackupOperation] = Field(default_factory=list)
    pinned: bool = False
    origin: Literal["manual", "schedule", "import"] = "manual"
    remote_status: Literal["not_configured", "pending", "copying", "verified", "failed"] = (
        "not_configured"
    )
    remote_error: str | None = None
    remote_verified_at: datetime | None = None
    remote_location: str | None = None
    remote_sha256: str | None = None
    remote_version_id: str | None = None
    error_code: str | None = None
    stage_started_at: datetime | None = None
    processed_bytes: int = 0
    total_bytes: int = 0
