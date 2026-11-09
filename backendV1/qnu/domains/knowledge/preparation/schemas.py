"""Request and read contracts for preparation intents."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PreparationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["source", "ai", "auto"] = "source"
    revision_id: str | None = Field(None, min_length=1, max_length=64)
    ocr_run_id: str | None = Field(None, min_length=1, max_length=64)
    text_version: Annotated[int, Field(strict=True, ge=0)] = 0
    topic: str | None = Field(None, max_length=2000)
    provider_id: str | None = Field(None, min_length=1, max_length=64)
    max_output_tokens: int | None = Field(None, strict=True, gt=0)

    @field_validator("topic", mode="before")
    @classmethod
    def strip_topic(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def coherent_mode(self):
        if self.mode == "source" and (self.provider_id or self.max_output_tokens is not None):
            raise ValueError("Chế độ giữ nguyên nguồn không nhận tùy chọn sinh văn bản bằng AI.")
        if self.mode == "auto" and (self.provider_id or self.max_output_tokens is not None):
            raise ValueError("Chế độ tự động tự chọn model, không nhận tùy chọn thủ công.")
        if self.text_version > 0 and not self.ocr_run_id:
            raise ValueError("Bản văn bản đã sửa phải chỉ rõ lượt đọc nội dung đã lưu.")
        return self


class PreparationPolicyView(BaseModel):
    """Safe explanation of the pinned automatic policy; never a credential or endpoint."""

    model_config = ConfigDict(extra="ignore")
    version: str
    supplement: str
    reason: str | None = None


class PreparationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workspace_id: str
    collection_id: str
    source_id: str
    revision_id: str
    revision_no: int
    revision_sha256: str
    mode: str
    status: str
    topic: str
    text_version: int
    text_version_id: str | None
    text_canonical_sha256: str | None
    provider_id: str | None
    max_output_tokens: int | None
    ocr_run_id: str | None
    compilation_run_id: str | None
    error_code: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    policy: PreparationPolicyView | None = None
    reused: bool = False


def preparation_response(row) -> PreparationResponse:
    config = row.config or {}
    policy = config.get("policy")
    response = PreparationResponse.model_validate(row)
    return response.model_copy(
        update={
            "policy": PreparationPolicyView.model_validate(policy) if policy else None,
            "reused": bool(config.get("reused")),
        }
    )


class PreparationCreated(BaseModel):
    intent: PreparationResponse
    created: bool
    dispatched: bool
