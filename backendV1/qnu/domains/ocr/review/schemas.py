"""Readable text, exact changes and model suggestions are separate contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TextUnit(BaseModel):
    evidence_id: str
    page: int
    kind: str
    text: str
    original_text: str
    bbox: dict
    row: int | None = None
    column: int | None = None


class ReviewDocument(BaseModel):
    run_id: str
    version: int
    version_id: str | None
    canonical_sha256: str
    original_sha256: str
    markdown_sha256: str
    units: list[TextUnit]
    saved_at: datetime | None = None
    image_ocr_failures: list[dict] = Field(default_factory=list)
    image_ocr_acknowledged: bool = False


class SpellingEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    replacement: str = Field(min_length=1, max_length=100000)


class TextChange(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    evidence_id: str = Field(min_length=1, max_length=128)
    before: str = Field(max_length=100000)
    after: str = Field(max_length=100000)
    spelling_edits: list[SpellingEdit] | None = Field(None, min_length=1, max_length=500)


class SaveReview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_version: int = Field(ge=0)
    expected_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    changes: list[TextChange] = Field(default_factory=list, max_length=1000)
    # Completing a spelling review links the approval to the resulting text.
    review_check_id: str | None = Field(None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def unique_changes(self):
        if len({c.evidence_id for c in self.changes}) != len(self.changes):
            raise ValueError("Mỗi đoạn hoặc ô chỉ được sửa một lần trong yêu cầu.")
        if self.review_check_id is None and any(c.spelling_edits for c in self.changes):
            raise ValueError("Cần chỉ định lượt soát chính tả cho các vị trí đã sửa.")
        return self


class RerunReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    version: int = Field(ge=0)
    retry: bool = False


class RerunReviewResponse(BaseModel):
    run_id: str
    version: int
    status: str


class TextVersionSummary(BaseModel):
    version: int
    version_id: str | None
    saved_at: datetime | None
    change_count: int
    is_current: bool


class DetectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    # Explicit immutable snapshot for read-only historical checks; None checks latest.
    source_version: int | None = Field(None, ge=0)
    expected_version: int = Field(ge=0)
    expected_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_ids: list[str] = Field(min_length=1, max_length=100)
    provider_id: str | None = Field(None, min_length=1, max_length=64)
    max_output_tokens: int | None = Field(None, gt=0)

    @model_validator(mode="after")
    def unique_units(self):
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Không lặp đoạn kiểm tra.")
        return self


class Suggestion(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    evidence_id: str = Field(min_length=1, max_length=128)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    original: str = Field(min_length=1, max_length=2000)
    replacement: str = Field(min_length=1, max_length=2000)
    reason: str = Field(min_length=1, max_length=1000)
    context_before: str | None = Field(None, max_length=6000)
    context_after: str | None = Field(None, max_length=6000)
    review_reason: str | None = None


class ContextSuggestion(Suggestion):
    context_before: str = Field(min_length=1, max_length=6000)
    context_after: str = Field(min_length=1, max_length=6000)


class ContextSuggestedText(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    suggestions: list[ContextSuggestion] = Field(max_length=500)


class RejectedSuggestion(BaseModel):
    """Reason-only record: no model prose or source text is retained here."""

    model_config = ConfigDict(extra="forbid", strict=True)
    evidence_id: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=64)
    start: int | None = Field(None, ge=0)
    end: int | None = Field(None, ge=0)


class IgnoredSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    evidence_id: str = Field(min_length=1, max_length=128)
    start: int = Field(ge=0)
    end: int = Field(gt=0)


class SpellingDispositionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    evidence_id: str = Field(min_length=1, max_length=128)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    ignored: bool

    @model_validator(mode="after")
    def valid_span(self):
        if self.end <= self.start:
            raise ValueError("Vị trí gợi ý không hợp lệ.")
        return self


class SpellingDispositionBatch(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    suggestions: list[IgnoredSuggestion] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def unique_suggestions(self):
        keys = {(s.evidence_id, s.start, s.end) for s in self.suggestions}
        if len(keys) != len(self.suggestions):
            raise ValueError("Mỗi gợi ý chỉ được gửi một lần.")
        return self


class DetectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    version: int
    canonical_sha256: str
    suggestions: list[Suggestion]
    withheld_suggestions: list[Suggestion] = Field(default_factory=list)
    rejected_suggestions: list[RejectedSuggestion] = Field(default_factory=list)
    ignored_suggestions: list[IgnoredSuggestion] = Field(default_factory=list)
    checked_evidence_ids: list[str]
    total_evidence_count: int | None = None
    error_code: str | None
    usage_id: str | None
    created_at: datetime
    reviewed_at: datetime | None = None
    reviewed_version: int | None = None
    reviewed_sha256: str | None = None
    reviewed_by: str | None = None
