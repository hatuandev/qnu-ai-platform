"""Explicit snapshot and annotation provenance for comparative retrieval and answer measurements."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from qnu.domains.evaluation.answer_eval import AnswerExpectation


class EvaluationQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=100)
    query: str = Field(min_length=1, max_length=8000)
    gold_chunk_ids: list[str] = Field(default_factory=list, max_length=100)
    document_ids: list[str] | None = Field(None, min_length=1, max_length=100)
    group: str = Field("unspecified", max_length=100)
    expected_answer: AnswerExpectation | None = None
    history: list[dict] | None = None
    calculation: dict | None = None
    fact_query: dict | None = None

    @model_validator(mode="after")
    def unique_gold(self):
        if len(set(self.gold_chunk_ids)) != len(self.gold_chunk_ids):
            raise ValueError("Gold IDs bị trùng.")
        return self


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index_run_id: str = Field(min_length=1, max_length=64)
    manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    label_version: str = Field(min_length=1, max_length=100)
    label_status: Literal["draft_needs_human_check", "human_reviewed"] = "draft_needs_human_check"
    label_author: str = Field(min_length=1, max_length=200)
    queries: list[EvaluationQuery] = Field(min_length=1, max_length=20)
    top_k: int = Field(5, strict=True, ge=1, le=50)
    candidate_k: int = Field(30, strict=True, ge=1, le=50)
    include_rerank: bool = False
    include_answer_evaluation: bool = False
    rerank_provider_id: str | None = Field(None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def unique_queries(self):
        if len({q.id for q in self.queries}) != len(self.queries) or self.candidate_k < self.top_k:
            raise ValueError("Query IDs/budget không hợp lệ.")
        return self
