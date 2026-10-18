"""Domain-neutral retrieval budgets; legacy behavior remains the opt-in baseline."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RetrievalPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: Literal["legacy", "configured"] = "legacy"
    dense_top_k: int | None = Field(None, ge=1, le=100, strict=True)
    lexical_top_k: int | None = Field(None, ge=1, le=100, strict=True)
    fusion_top_k: int = Field(30, ge=1, le=200, strict=True)
    context_top_k: int = Field(5, ge=1, le=20, strict=True)
    max_context_chars: int = Field(36000, ge=1000, le=64000, strict=True)

    @model_validator(mode="after")
    def validate_budgets(self) -> "RetrievalPolicy":
        if self.context_top_k > self.fusion_top_k:
            raise ValueError("context_top_k must not exceed fusion_top_k")
        return self


def configured_policy(runtime: dict) -> RetrievalPolicy | None:
    knowledge = runtime.get("knowledge_policy") or {}
    policy = RetrievalPolicy.model_validate(knowledge.get("retrieval_policy") or {})
    if policy.profile == "legacy":
        return None
    # Existing retrieval_limit is a compatibility fallback, not a second override.
    limit = knowledge.get("retrieval_limit", 10)
    return RetrievalPolicy.model_validate({**policy.model_dump(),
        "dense_top_k": policy.dense_top_k if policy.dense_top_k is not None else limit,
        "lexical_top_k": policy.lexical_top_k if policy.lexical_top_k is not None else limit})
