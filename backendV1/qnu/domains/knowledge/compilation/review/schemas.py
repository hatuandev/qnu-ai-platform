"""Exhaustive assessment contracts; the server supplies every quoted excerpt."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    provider_id: str | None = Field(None, min_length=1, max_length=64)
    max_output_tokens: int | None = Field(None, gt=0)
    structured_output: bool = False


class SourceAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    source_id: str = Field(min_length=1, max_length=200)
    status: Literal["covered", "omitted", "out_of_scope", "uncertain"]
    draft_ids: list[str] = Field(max_length=1000)
    explanation: str = Field(min_length=1, max_length=4000)
    suggested_action: str = Field(max_length=4000)

    @field_validator("explanation")
    @classmethod
    def explanation_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Cần giải thích nhận xét.")
        return value


class DraftAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    draft_id: str = Field(min_length=1, max_length=200)
    status: Literal["supported", "contradicted", "unsupported", "uncertain"]
    source_ids: list[str] = Field(max_length=1000)
    explanation: str = Field(min_length=1, max_length=4000)
    suggested_action: str = Field(max_length=4000)

    @field_validator("explanation")
    @classmethod
    def explanation_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Cần giải thích nhận xét.")
        return value


class ReviewContent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    source_assessments: list[SourceAssessment]
    draft_assessments: list[DraftAssessment]


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    compilation_run_id: str
    workspace_id: str
    collection_id: str
    status: str
    verdict: str | None
    provider_id: str
    input_sha256: str
    draft_sha256: str
    bundle_sha256: str
    created_by: str
    created_at: datetime
    finished_at: datetime | None
    error_code: str | None
    usage_id: str | None
    usage_tokens: int | None
    trace: dict
