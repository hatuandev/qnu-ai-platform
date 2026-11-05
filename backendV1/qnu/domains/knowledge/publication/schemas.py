"""Publication commands do not accept actor, scope, status, permission or source overrides."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from qnu.domains.knowledge.metadata import MetadataValues, RetrievalAnnotation

Action = Literal["approve", "publish", "withdraw"]


class FindingResolution(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    finding_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: Literal["accepted_risk", "not_an_issue"]
    reason: str = Field(min_length=10, max_length=2000)


class ReviewAcknowledgement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    review_id: str = Field(min_length=1, max_length=64)
    report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    confirmed_reviewed: Literal[True]
    resolutions: list[FindingResolution] = Field(default_factory=list, max_length=10000)
    retrieval_metadata_sha256: str | None = Field(None, pattern=r"^[0-9a-f]{64}$")


class ReviewSkipAcknowledgement(BaseModel):
    """An explicit human choice, never a claim that a review took place."""

    model_config = ConfigDict(extra="forbid")
    confirmed_skip: Literal[True]
    version_id: str = Field(min_length=1, max_length=64)
    bundle_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    retrieval_metadata_sha256: str | None = Field(None, pattern=r"^[0-9a-f]{64}$")


class MetadataProposalEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    values: MetadataValues
    quote: str = Field(min_length=1, max_length=2000)


class RegisterVersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    compilation_run_id: str = Field(min_length=1, max_length=64)
    retrieval_metadata: list[RetrievalAnnotation] = Field(default_factory=list, max_length=10000)
    metadata_proposal_ids: list[Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]] = Field(
        default_factory=list, max_length=10000
    )

    metadata_proposal_edits: dict[
        Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")], MetadataProposalEdit
    ] = Field(default_factory=dict, max_length=10000)


class CreateDocumentRequest(RegisterVersionRequest):
    document_key: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    title: str = Field(min_length=1, max_length=255)

    @field_validator("title", mode="before")
    @classmethod
    def trim_title(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Action
    reason: str = Field(min_length=1, max_length=1000)
    review_ack: ReviewAcknowledgement | None = None
    review_skip: ReviewSkipAcknowledgement | None = None

    @model_validator(mode="after")
    def explicit_skip(self):
        if self.review_skip is not None:
            if self.action != "approve" or self.review_ack is not None:
                raise ValueError("Chỉ chọn một cách duyệt cho hành động approve.")
            if len(self.reason.strip()) < 10:
                raise ValueError("Cần lý do bỏ qua review ít nhất 10 ký tự.")
        return self

    @field_validator("reason", mode="before")
    @classmethod
    def trim_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class CommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preview_id: str = Field(min_length=1, max_length=64)
    preview_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workspace_id: str
    collection_id: str
    document_key: str
    title: str
    change_sequence: int
    created_by: str
    created_at: datetime


class VersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    document_id: str
    workspace_id: str
    collection_id: str
    compilation_run_id: str
    version_no: int
    status: str
    state_version: int
    input_sha256: str
    draft_sha256: str
    markdown_sha256: str
    bundle_sha256: str
    provenance: dict
    retrieval_metadata: list[RetrievalAnnotation] = Field(default_factory=list)
    created_by: str
    created_at: datetime

    @computed_field
    @property
    def retrieval_metadata_sha256(self) -> str:
        from qnu.domains.knowledge.publication.evidence import digest

        return digest(
            [a.model_dump(mode="json", exclude_none=True) for a in self.retrieval_metadata]
        )


class RegistrationResponse(BaseModel):
    document: DocumentResponse
    version: VersionResponse
    created: bool


class PreviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    version_id: str
    document_id: str
    actor_ref: str
    action: Action
    reason: str
    expected_document_sequence: int
    expected_version_sequence: int
    expected_active_version_id: str | None
    bundle_sha256: str
    preview_sha256: str
    expires_at: datetime
    review_ack: dict | None = None


class DecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    preview_id: str
    version_id: str
    document_id: str
    actor_ref: str
    action: Action
    reason: str
    document_sequence: int
    bundle_sha256: str
    before: dict
    after: dict
    created_at: datetime


class PublishedResponse(BaseModel):
    document: DocumentResponse
    version: VersionResponse
    decision: DecisionResponse
    content: dict
