from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Task = Literal[
    "chat", "answer", "followup", "compiler", "compiler_review", "ocr_review", "ocr", "rerank"
]
TASK_CAPABILITIES = {
    task: "chat"
    for task in ("chat", "answer", "followup", "compiler", "compiler_review", "ocr_review")
} | {"ocr": "ocr", "rerank": "rerank"}


class ResiliencePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    key_pool_enabled: bool = False
    retry_owner: Literal["qnu", "gateway"] = "qnu"
    max_key_attempts: int = Field(1, ge=1, le=3)
    auth_cooldown_seconds: int = Field(300, ge=1, le=86400)
    rate_cooldown_seconds: int = Field(30, ge=1, le=86400)
    fallbacks: dict[Task, list[str]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def bounded(self):
        if self.retry_owner == "gateway" and self.max_key_attempts != 1:
            raise ValueError("Gateway quản lý retry: QNU chỉ được gửi một lần.")
        if not self.key_pool_enabled and self.max_key_attempts != 1:
            raise ValueError("Bật nhóm khóa trước khi tăng số lần gọi.")
        for ids in self.fallbacks.values():
            if len(ids) > 3 or len(ids) != len(set(ids)):
                raise ValueError("Mỗi tác vụ tối đa ba model dự phòng, không trùng.")
            if any(not item or len(item) > 64 for item in ids):
                raise ValueError("Mã provider không hợp lệ.")
        return self


class PolicyResponse(BaseModel):
    provider_id: str
    status: Literal["default", "configured", "stale"]
    policy: ResiliencePolicy
    routing_phase: Literal["before_dispatch"] = "before_dispatch"
    explicit_provider_is_pinned: bool = True
    embedding_model_fallback: bool = False


class ExecutionObservation(BaseModel):
    id: str
    created_at: datetime
    call_id: str
    usage_id: str | None = None
    capability: str
    model_name: str
    key_id: str | None
    code: str
    upstream_status: int | None
    attempt: int
    latency_ms: int | None
    total_tokens: int | None
