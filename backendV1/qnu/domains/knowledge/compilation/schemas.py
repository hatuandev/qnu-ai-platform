"""Strict request and draft contracts. Completion never implies publication."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CompilationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str = Field(min_length=1, max_length=2000)
    ocr_run_ids: list[str] = Field(min_length=1, max_length=20)
    provider_id: str | None = Field(None, min_length=1, max_length=64)
    max_output_tokens: int | None = Field(None, strict=True, gt=0)
    structured_output: bool = Field(False, strict=True)
    text_versions: dict[str, Annotated[int, Field(strict=True, ge=0)]] = Field(default_factory=dict)
    auto_review: bool = Field(True, strict=True)
    review_provider_id: str | None = Field(None, min_length=1, max_length=64)
    review_max_output_tokens: int | None = Field(None, strict=True, gt=0)
    review_structured_output: bool = Field(False, strict=True)

    @model_validator(mode="after")
    def selected_versions(self):
        if set(self.text_versions) - set(self.ocr_run_ids):
            raise ValueError("Phiên bản văn bản phải thuộc OCR đã chọn.")
        return self

    @field_validator("topic", mode="before")
    @classmethod
    def strip_topic(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("ocr_run_ids")
    @classmethod
    def unique_runs(cls, values):
        if any(not v.strip() or len(v) > 64 for v in values) or len(set(values)) != len(values):
            raise ValueError("OCR run IDs không hợp lệ hoặc bị trùng.")
        return values


class DraftParagraph(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str = Field(min_length=1, max_length=20000)
    citations: list[str] = Field(min_length=1, max_length=100)


class DraftSection(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    heading: str = Field(min_length=1, max_length=500)
    paragraphs: list[DraftParagraph] = Field(min_length=1, max_length=100)


class DraftContent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    title: str = Field(min_length=1, max_length=500)
    sections: list[DraftSection] = Field(min_length=1, max_length=100)
    unknowns: list[str] = Field(max_length=100)


class SegmentDraftContent(BaseModel):
    """A part may be context-only, hence an optional title and empty sections."""

    model_config = ConfigDict(extra="forbid", strict=True)
    title: str | None = Field(None, max_length=500)
    sections: list[DraftSection] = Field(default_factory=list, max_length=100)
    unknowns: list[str] = Field(default_factory=list, max_length=100)


class CompilationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workspace_id: str
    collection_id: str
    generation: int
    topic: str
    status: str
    provider_id: str
    requested_by: str
    requested_at: datetime
    dispatched_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    attempt_count: int
    error_code: str | None
    input_sha256: str
    usage_tokens: int | None
    parent_run_id: str | None
    origin: str


class CompilationCreated(BaseModel):
    run: CompilationResponse
    created: bool
    dispatched: bool


class CompilationSegmentProgress(BaseModel):
    """Observed state of one durable part; never an estimate of remaining work."""

    index: int
    status: str
    attempt_count: int
    usage_tokens: int | None
    error_code: str | None
    started_at: datetime | None
    finished_at: datetime | None
    duration_seconds: float | None = None


class CompilationProgress(BaseModel):
    run_id: str
    status: str
    workflow_version: str
    segmented: bool
    total: int
    completed: int
    pending: int
    running: int
    failed: int
    uncertain: int
    cancelled: int
    usage_tokens: int | None
    started_at: datetime | None
    finished_at: datetime | None
    latest_output_generation: int | None
    latest_output_partial: bool | None
    segments: list[CompilationSegmentProgress]
    # Observed scheduling facts; there is deliberately no estimated time remaining.
    received: int = 0
    concurrency: int = 1
    active_segments: list[int] = Field(default_factory=list)
    elapsed_seconds: float | None = None
    planner_version: str | None = None
    queue_timeout_seconds: int = 0
    nodes: list[dict] = Field(default_factory=list)
    refinement_timeout_seconds: int = 0
