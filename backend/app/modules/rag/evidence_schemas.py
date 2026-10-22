"""Strict contracts for query constraints, quotes and independent verification."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.knowledge.normalization.retrieval_models import TemporalScope


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QueryPlan(StrictContract):
    query: str = Field(min_length=1, max_length=2000)
    years: list[int] = Field(default_factory=list, max_length=10)
    document_years: list[int] = Field(default_factory=list, max_length=10)
    event_years: list[int] = Field(default_factory=list, max_length=10)
    requires_year: bool = False
    question_scope: Literal["source_content", "applicability"] = "applicability"
    uses_history: bool = False
    historical_reference_allowed: bool = True
    coverage: Literal["focused", "enumeration", "comparison"] = "focused"
    enumeration_subject: str | None = None
    entity: str | None = None
    target_institution: str | None = None
    exam_organizer: str | None = None
    intent: str | None = None
    attribute: str | None = None
    education_level: str | None = None
    requested_topics: list[str] = Field(default_factory=list, max_length=6)
    method: str | None = None
    round: str | None = None
    event: str | None = None
    search_queries: list[str] = Field(default_factory=list, max_length=3)


class EvidenceBlock(BaseModel):
    id: str
    binding_id: str
    index_revision_id: str
    source_revision_id: str
    title: str
    page_number: int | None = None
    section: str = ""
    header_context: str = ""
    source_context: str = ""
    text: str
    start: int
    end: int
    canonical_hash: str = ""
    origin: Literal["canonical", "reviewed_fact"] = "canonical"
    fact_id: str | None = None
    fact_context: dict = Field(default_factory=dict)
    scope_years: list[int] = Field(default_factory=list)
    temporal_scope: TemporalScope = Field(default_factory=TemporalScope)
    unit_id: str | None = None
    parent_id: str | None = None
    unit_manifest_hash: str | None = None
    is_container: bool = False
    record_label: str | None = None
    record_heading_id: str | None = None
    record_path: list[str] = Field(default_factory=list)


class QuoteReference(StrictContract):
    block_id: str
    quote: str = Field(min_length=3, max_length=4000)


class EvidenceClaim(StrictContract):
    id: str
    text: str = Field(min_length=3, max_length=4000)
    references: list[QuoteReference] = Field(min_length=1, max_length=4)


class AnswerProposal(StrictContract):
    status: Literal["supported", "partial", "missing", "conflict", "clarify"]
    claims: list[EvidenceClaim] = Field(default_factory=list, max_length=12)
    missing_constraints: list[str] = Field(default_factory=list, max_length=10)


class ClaimVerdict(StrictContract):
    claim_id: str
    entailed: bool
    relevant: bool
    scope_compatible: bool
    reason: str = Field(max_length=500)
    superseded_by: list[QuoteReference] = Field(default_factory=list, max_length=4)


class VerificationResult(StrictContract):
    verdicts: list[ClaimVerdict] = Field(default_factory=list, max_length=48)
    complete: bool
    conflict: bool = False
    missing_constraints: list[str] = Field(default_factory=list, max_length=10)
    topic_coverage: dict[str, bool] = Field(default_factory=dict)
