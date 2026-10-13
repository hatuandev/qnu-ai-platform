"""Strict contracts for query constraints, quotes and independent verification."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QueryPlan(StrictContract):
    query: str = Field(min_length=1, max_length=2000)
    years: list[int] = Field(default_factory=list, max_length=10)
    requires_year: bool = False
    uses_history: bool = False
    coverage: Literal["focused", "enumeration", "comparison"] = "focused"
    enumeration_subject: str | None = None
    entity: str | None = None
    target_institution: str | None = None
    exam_organizer: str | None = None
    intent: str | None = None
    attribute: str | None = None
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
    text: str
    start: int
    end: int
    canonical_hash: str = ""
    origin: Literal["canonical", "reviewed_fact"] = "canonical"
    fact_id: str | None = None
    fact_context: dict = Field(default_factory=dict)
    scope_years: list[int] = Field(default_factory=list)


class QuoteReference(StrictContract):
    block_id: str
    quote: str = Field(min_length=3, max_length=4000)


class EvidenceClaim(StrictContract):
    id: str
    text: str = Field(min_length=3, max_length=2000)
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
    verdicts: list[ClaimVerdict] = Field(default_factory=list, max_length=12)
    complete: bool
    conflict: bool = False
    missing_constraints: list[str] = Field(default_factory=list, max_length=10)
