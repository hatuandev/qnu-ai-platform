from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ResourceKind = Literal[
    "collection", "source", "document", "assistant", "conversation", "job", "index"
]
LifecycleOperation = Literal[
    "archive", "delete", "restore", "pause", "resume", "cancel", "cleanup", "replace"
]


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    kind: ResourceKind
    resource_id: str = Field(min_length=1, max_length=64)
    action: LifecycleOperation
    reason: str = Field(min_length=1, max_length=2000)
    job_kind: (
        Literal["ocr", "compiler", "index", "auto_review", "review", "spelling", "turn"] | None
    ) = None
    replacement_version_id: str | None = Field(None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def matching_parameters(self) -> Self:
        if (self.kind == "job") != (self.job_kind is not None):
            raise ValueError("job_kind chỉ dùng và bắt buộc cho tác vụ.")
        if (self.action == "replace") != (self.replacement_version_id is not None):
            raise ValueError("Phiên bản thay thế chỉ dùng và bắt buộc khi thay văn bản.")
        return self

    @field_validator("reason")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Cần lý do thao tác.")
        return value.strip()


class AcceptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    preview_id: str = Field(min_length=1, max_length=64)
    preview_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class ActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    kind: str
    resource_id: str
    action: str
    reason: str
    impact: dict
    preview_sha256: str
    status: str
    result: dict | None
    error_code: str | None
    expires_at: datetime
    accepted_at: datetime | None
    finished_at: datetime | None
