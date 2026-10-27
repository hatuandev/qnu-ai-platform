"""Editable text excludes protected source tables, scope and model output metadata."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from qnu.domains.knowledge.compilation.schemas import DraftContent


class EditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_bundle_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reason: str = Field(min_length=1, max_length=2000)
    content: DraftContent
    review_id: str | None = Field(None, min_length=1, max_length=64)


class AcceptEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    preview_id: str = Field(min_length=1, max_length=64)
    preview_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class AutoReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    compilation_run_id: str
    status: str
    review_id: str | None
    error_code: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
