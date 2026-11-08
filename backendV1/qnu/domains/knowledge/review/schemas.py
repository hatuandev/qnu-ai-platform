"""Review handoff commands never accept actor, scope, status or version overrides."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

PreviewAction = Literal["submit", "request_changes", "cancel"]
SubmissionStatus = Literal["pending", "changes_requested", "resolved", "cancelled"]


class SubmissionPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    document_id: str = Field(min_length=1, max_length=64)
    version_id: str = Field(min_length=1, max_length=64)
    submission_id: str | None = Field(None, min_length=1, max_length=64)
    action: PreviewAction
    reason: str = Field("", max_length=1000)

    @model_validator(mode="after")
    def action_requirements(self):
        if self.action == "submit":
            if self.submission_id is not None:
                raise ValueError("Gửi duyệt không nhận submission_id.")
            return self
        if self.submission_id is None:
            raise ValueError("Cần chọn một yêu cầu duyệt đang mở.")
        if self.action == "request_changes" and len(self.reason) < 10:
            raise ValueError("Yêu cầu sửa cần lý do ít nhất 10 ký tự.")
        if self.action == "cancel" and len(self.reason) < 3:
            raise ValueError("Rút yêu cầu cần lý do ít nhất 3 ký tự.")
        return self

    @field_validator("reason", mode="before")
    @classmethod
    def trim_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class SubmissionCommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preview_id: str = Field(min_length=1, max_length=64)
    preview_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class SubmissionPreviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workspace_id: str
    collection_id: str
    document_id: str
    version_id: str
    submission_id: str | None
    actor_ref: str
    action: PreviewAction
    reason: str
    expected_document_sequence: int
    expected_version_sequence: int
    expected_submission_status: str | None
    expected_submission_sequence: int | None
    bundle_sha256: str
    preview_sha256: str
    expires_at: datetime


class SubmissionResponse(BaseModel):
    id: str
    workspace_id: str
    collection_id: str
    document_id: str
    document_title: str
    version_id: str
    version_no: int
    bundle_sha256: str
    status: SubmissionStatus
    state_version: int
    note: str
    submitted_by: str
    submitted_at: datetime
    document_sequence: int
    closed_by: str | None = None
    closed_at: datetime | None = None
    close_reason: str | None = None

    @computed_field
    @property
    def is_open(self) -> bool:
        return self.status in {"pending", "changes_requested"}


class SubmissionActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    submission_id: str
    action: str
    actor_ref: str
    reason: str
    publication_decision_id: str | None
    document_sequence: int
    bundle_sha256: str
    before: dict
    after: dict
    created_at: datetime


class SubmissionDetail(SubmissionResponse):
    actions: list[SubmissionActionResponse] = Field(default_factory=list)


class SubmissionOutcome(BaseModel):
    submission: SubmissionResponse
    action: str
    created: bool
