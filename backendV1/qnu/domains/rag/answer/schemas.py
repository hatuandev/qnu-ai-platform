"""Source-bound question answering contracts; model output never supplies source locations."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from qnu.domains.knowledge.index.schemas import SearchHit, SearchRequest
from qnu.domains.rag.answer.coverage import CoverageReport, Requirement
from qnu.domains.rag.policy import RagPolicy


class AnswerRequest(RagPolicy):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=8000)
    top_k: int = Field(5, strict=True, ge=1, le=20)
    document_ids: list[str] | None = Field(None, min_length=1, max_length=100)
    provider_id: str | None = Field(None, min_length=1, max_length=64)
    max_output_tokens: int | None = Field(None, strict=True, gt=0)
    fact_query: dict | None = Field(default=None)
    history: list[dict] | None = Field(default=None)
    calculation: dict | None = Field(default=None)

    @model_validator(mode="after")
    def retrieval_contract(self) -> "AnswerRequest":
        SearchRequest(
            query=self.question,
            top_k=self.top_k,
            document_ids=self.document_ids,
            mode=self.retrieval_mode,
            candidate_k=self.candidate_k,
            rerank_provider_id=self.rerank_provider_id,
            metadata_filter=self.metadata_filter,
            scope_resolution=self.scope_resolution,
            rrf_k=self.rrf_k,
        )
        return self

    @field_validator("question", mode="before")
    @classmethod
    def trim_question(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("document_ids")
    @classmethod
    def validate_documents(cls, values: list[str] | None) -> list[str] | None:
        return SearchRequest.unique_documents(values)


class Statement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(strict=True, min_length=1, max_length=12000)
    evidence_ids: list[str] = Field(min_length=1, max_length=20)

    @field_validator("text")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip() or re.search(
            r"\[[Ee]\d+\]|\[[^\]]*\]\([^)]+\)|<[/!A-Za-z][^>]*>", value
        ):
            raise ValueError("Statement phải là text thuần; citation do BE gắn.")
        return value


class CellSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cell_id: str = Field(pattern=r"^E[1-9]\d*:r\d+:k\d+$", max_length=80)


class ModelAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["answered", "insufficient_evidence"]
    statements: list[Statement] = Field(max_length=20)
    lookups: list[CellSelection] = Field(default_factory=list, max_length=20)
    assessment: list[Requirement] = Field(default_factory=list, max_length=20)
    message: str | None = Field(default=None, max_length=2000)

    @field_validator("message")
    @classmethod
    def plain_message(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip() or re.search(
            r"\[[Ee]\d+\]|\[[^\]]*\]\([^)]+\)|<[/!A-Za-z][^>]*>", value
        ):
            raise ValueError("Message phải là text thuần, không citation hay HTML.")
        return value.strip()

    @model_validator(mode="after")
    def consistent_status(self) -> "ModelAnswer":
        if bool(self.statements or self.lookups) != (self.status == "answered"):
            raise ValueError("Status và statements không khớp.")
        return self


class EvidenceSource(SearchHit):
    evidence_id: str
    source_passages: list[dict[str, str]] = Field(default_factory=list)
    source_title: str | None = Field(default=None, exclude=True)


class AnswerTrace(BaseModel):
    retrieval: dict = Field(default_factory=dict)
    prompt_version: str
    evidence_sha256: str | None = None
    provider_id: str | None = None
    model_name: str | None = None
    configuration_hash: str | None = None
    inference_configuration_hash: str | None = None
    reasoning: dict = Field(default_factory=dict)
    usage_id: str | None = None
    routing: list[dict] = Field(default_factory=list)
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    stage_ms: dict[str, float] = Field(default_factory=dict)
    context: dict = Field(default_factory=dict)
    grounding: dict = Field(default_factory=dict)
    contract: dict = Field(default_factory=dict)
    verification: dict = Field(default_factory=lambda: {"mode": "off", "status": "not_run"})
    coverage: dict = Field(default_factory=dict)
    cache: dict = Field(default_factory=dict)
    fallback: dict = Field(default_factory=dict)
    appeal: dict = Field(default_factory=dict)
    rewriting: dict = Field(default_factory=dict)
    calculator: dict = Field(default_factory=dict)
    tools: list[dict] = Field(default_factory=list)
    semantic_cache: dict = Field(default_factory=dict)


class AnswerResponse(BaseModel):
    id: str
    status: Literal["answered", "insufficient_evidence"]
    reason: (
        Literal[
            "no_eligible_content",
            "no_match",
            "model_abstained",
            "answer_not_supported",
            "answer_verification_uncertain",
        ]
        | None
    ) = None
    answer: str | None = None
    message: str | None = None
    statements: list[Statement] = Field(default_factory=list)
    sources: list[EvidenceSource] = Field(default_factory=list)
    index_run_id: str
    generation: int
    trace: AnswerTrace
    coverage: CoverageReport | None = None
