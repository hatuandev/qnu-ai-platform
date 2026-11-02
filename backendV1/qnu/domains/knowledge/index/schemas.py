"""Dense indexing and source-bearing search API contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from qnu.domains.knowledge.metadata import MetadataFilter


class IndexRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider_id: str | None = Field(None, min_length=1, max_length=64)
    contextual_search: bool = Field(False, strict=True)


class IndexResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workspace_id: str
    collection_id: str
    generation: int
    status: str
    is_active: bool
    provider_id: str
    dimension: int
    input_sha256: str
    requested_at: datetime
    dispatched_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    attempt_count: int
    error_code: str | None
    chunks_total: int
    manifest_sha256: str | None


class IndexReadiness(BaseModel):
    status: Literal["ready", "not_indexed", "outdated", "unavailable"]
    index_run_id: str | None = None
    generation: int | None = None
    version_id: str | None = None
    publication_decision_id: str | None = None
    bundle_sha256: str | None = None
    version_state: int | None = None


class IndexCreated(BaseModel):
    run: IndexResponse
    created: bool
    dispatched: bool


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=8000)
    top_k: int = Field(5, strict=True, ge=1, le=50)
    document_ids: list[str] | None = Field(None, min_length=1, max_length=100)
    mode: Literal["dense", "hybrid", "hybrid_rerank"] = "dense"
    candidate_k: int = Field(30, strict=True, ge=1, le=100)
    rrf_k: int = Field(60, strict=True, ge=1, le=1000)
    rerank_provider_id: str | None = Field(None, min_length=1, max_length=64)
    metadata_filter: MetadataFilter = Field(default_factory=MetadataFilter)
    scope_resolution: Literal["explicit", "catalog"] = "explicit"

    @model_validator(mode="after")
    def candidate_budget(self):
        if self.mode != "dense" and self.candidate_k < self.top_k:
            raise ValueError("candidate_k phải lớn hơn hoặc bằng top_k.")
        if self.rerank_provider_id and self.mode != "hybrid_rerank":
            raise ValueError("Chỉ chọn provider rerank khi dùng hybrid_rerank.")
        return self

    @field_validator("query", mode="before")
    @classmethod
    def trim_query(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("document_ids")
    @classmethod
    def unique_documents(cls, values):
        if values is not None and (
            len(set(values)) != len(values) or any(not v or len(v) > 64 for v in values)
        ):
            raise ValueError("Document IDs không hợp lệ hoặc bị trùng.")
        return values


class SearchHit(BaseModel):
    chunk_id: str
    document_id: str
    version_id: str
    publication_decision_id: str
    score: float
    kind: str
    text: str
    citations: dict
    structure: dict | None


class SearchResponse(BaseModel):
    index_run_id: str
    generation: int
    status: str
    hits: list[SearchHit]
    eligible_documents: int
    skipped_documents: list[dict] = Field(default_factory=list)
    trace: dict = Field(default_factory=dict)
