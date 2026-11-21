from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from qnu.domains.assistants.guardrail_policy import GuardrailPolicy
from qnu.domains.rag.policy import RagPolicy


class AssistantRagPolicy(RagPolicy):
    """RAG policy plus assistant-only behavior; stored in the existing JSONB column."""

    guardrail_policy: GuardrailPolicy = Field(default_factory=GuardrailPolicy)
    suggested_prompts: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("suggested_prompts")
    @classmethod
    def clean_suggested_prompts(cls, values: list[str]) -> list[str]:
        cleaned = [v.strip() for v in values if isinstance(v, str) and v.strip()]
        return cleaned[:10]


class AssistantConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=160)
    description: str = Field("", max_length=2000)
    persona: str = Field("", max_length=4000)
    # Mirrors ``collection_ids[0]`` for older readers; None means no binding yet.
    collection_id: str | None = Field(None, max_length=64)
    chat_provider_id: str | None = Field(None, min_length=1, max_length=64)
    top_k: int = Field(5, strict=True, ge=1, le=20)
    history_turns: int = Field(3, strict=True, ge=0, le=10)
    max_output_tokens: int | None = Field(None, strict=True, gt=0)
    is_active: bool = True
    rag_policy: AssistantRagPolicy = Field(default_factory=AssistantRagPolicy)

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


class NewAssistantRagPolicy(AssistantRagPolicy):
    scope_resolution: Literal["explicit", "catalog"] = "catalog"
    context_window: int = Field(1, strict=True, ge=0, le=5)


ReadinessStatus = Literal[
    "empty", "syncing", "ready", "outdated", "not_indexed", "failed", "uncertain"
]


def _normalize_collection_ids(value: list[str] | None) -> list[str] | None:
    if value is None:
        return None
    unique = list(dict.fromkeys(value))
    if any(not item or len(item) > 64 for item in unique):
        raise ValueError("Danh sách kho tri thức chứa mã không hợp lệ.")
    return unique


class AssistantCreate(AssistantConfig):
    rag_policy: NewAssistantRagPolicy = Field(default_factory=NewAssistantRagPolicy)
    # Single source of truth when present; ``collection_id`` then mirrors the first
    # entry. Older clients that send only ``collection_id`` stay on one collection.
    collection_ids: list[str] | None = Field(None, max_length=20)

    _collection_ids = field_validator("collection_ids")(_normalize_collection_ids)


class AssistantUpdate(AssistantConfig):
    expected_revision: int = Field(strict=True, ge=1)
    collection_ids: list[str] | None = Field(None, max_length=20)

    _collection_ids = field_validator("collection_ids")(_normalize_collection_ids)


class AssistantResponse(AssistantConfig):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workspace_id: str
    revision: int
    collection_ids: list[str] = Field(default_factory=list)
    created_by: str
    created_at: datetime
    updated_at: datetime


class AssistantCollectionReadiness(BaseModel):
    collection_id: str
    collection_name: str
    status: ReadinessStatus
    published_document_count: int
    served_document_count: int
    index_run_id: str | None = None
    index_generation: int | None = None
    sync_status: str
    sync_error_code: str | None = None


class AssistantReadiness(BaseModel):
    """Scalar fields describe the first collection; ``collections`` covers all.

    A saved-but-unbound assistant has no first collection: ``collection_id`` is
    None and ``status`` is ``empty``.
    """

    assistant_id: str
    collection_id: str | None = None
    collection_name: str = ""
    status: ReadinessStatus
    published_document_count: int
    served_document_count: int
    index_run_id: str | None = None
    index_generation: int | None = None
    sync_status: str
    sync_error_code: str | None = None
    collections: list[AssistantCollectionReadiness] = Field(default_factory=list)
    checked_at: datetime


class PersonaCraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str = Field(min_length=2, max_length=500, description="Mô tả mục đích hoặc chủ đề của trợ lý")
    name: str | None = Field(default=None, max_length=160, description="Tên gợi ý ban đầu nếu có")
    target_audience: str | None = Field(default=None, max_length=200, description="Đối tượng phục vụ")
    tone: str | None = Field(default=None, max_length=100, description="Phong cách/văn phong")
    provider_id: str | None = Field(default=None, max_length=64, description="Mã nhà cung cấp mô hình AI")


class PersonaCraftResponse(BaseModel):
    name: str = Field(description="Tên trợ lý được gợi ý")
    description: str = Field(description="Mô tả ngắn gọn về trợ lý")
    persona: str = Field(description="Chỉ dẫn đầy đủ cho trợ lý (Persona)")
    suggested_prompts: list[str] = Field(default_factory=list, description="Danh sách các câu hỏi gợi ý mở đầu")
