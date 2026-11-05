from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from qnu.domains.rag.policy import RagPolicy


class AssistantConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=160)
    description: str = Field("", max_length=2000)
    persona: str = Field("", max_length=4000)
    collection_id: str = Field(min_length=1, max_length=64)
    chat_provider_id: str | None = Field(None, min_length=1, max_length=64)
    top_k: int = Field(5, strict=True, ge=1, le=20)
    history_turns: int = Field(3, strict=True, ge=0, le=10)
    max_output_tokens: int | None = Field(None, strict=True, gt=0)
    is_active: bool = True
    rag_policy: RagPolicy = Field(default_factory=RagPolicy)

    @model_validator(mode="after")
    def candidate_budget(self):
        if self.rag_policy.retrieval_mode != "dense" and self.rag_policy.candidate_k < self.top_k:
            raise ValueError("candidate_k phải lớn hơn hoặc bằng top_k.")
        return self

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Tên trợ lý không được rỗng.")
        return value.strip()


class NewAssistantRagPolicy(RagPolicy):
    scope_resolution: Literal["explicit", "catalog"] = "catalog"
    context_window: int = Field(1, strict=True, ge=0, le=5)


class AssistantCreate(AssistantConfig):
    rag_policy: NewAssistantRagPolicy = Field(default_factory=NewAssistantRagPolicy)


class AssistantUpdate(AssistantConfig):
    expected_revision: int = Field(strict=True, ge=1)


class AssistantResponse(AssistantConfig):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workspace_id: str
    revision: int
    created_by: str
    created_at: datetime
    updated_at: datetime
