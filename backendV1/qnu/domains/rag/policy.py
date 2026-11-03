"""Explicit, snapshot-compatible RAG policy shared by assistants and answer requests."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from qnu.domains.knowledge.metadata import MetadataFilter


class RagPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    retrieval_mode: Literal["dense", "hybrid", "hybrid_rerank"] = "dense"
    candidate_k: int = Field(30, strict=True, ge=1, le=100)
    rrf_k: int = Field(60, strict=True, ge=1, le=1000)
    rerank_provider_id: str | None = Field(None, min_length=1, max_length=64)
    metadata_filter: MetadataFilter = Field(default_factory=MetadataFilter)
    scope_resolution: Literal["explicit", "catalog"] = "explicit"
    context_window: int = Field(0, strict=True, ge=0, le=5)
    context_max_bytes: int = Field(16000, strict=True, ge=256, le=128000)
    verification_mode: Literal["off", "observe", "enforce"] = "off"
    verification_provider_id: str | None = Field(None, min_length=1, max_length=64)
    verification_max_output_tokens: int | None = Field(None, strict=True, gt=0)

    @model_validator(mode="after")
    def compatible(self):
        if self.rerank_provider_id and self.retrieval_mode != "hybrid_rerank":
            raise ValueError("Provider rerank chỉ dùng với hybrid_rerank.")
        if self.verification_provider_id and self.verification_mode == "off":
            raise ValueError("Cần bật kiểm chứng trước khi chọn provider kiểm chứng.")
        return self
