"""Typed contracts for QNU AI Assistant administration and chat."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class AssistantPersonaScope(BaseModel):
    persona: str = Field(
        "Trợ lý AI chính thức của Trường Đại học Quy Nhơn.",
        min_length=10,
        max_length=2000,
    )
    allowed_topics: list[str] = Field(default_factory=list)
    out_of_scope_policy: str = Field(
        "Từ chối lịch sự và hướng dẫn người dùng đến đơn vị phụ trách.",
        min_length=10,
        max_length=1000,
    )


class AssistantKnowledgePolicy(BaseModel):
    chunking_strategy: Literal["ClauseBasedChunker", "SemanticChunker"] = "SemanticChunker"
    require_structured_facts: bool = False
    retrieval_limit: int = Field(10, ge=1, le=50)


class AssistantModelPolicy(BaseModel):
    primary_model: str = Field("gpt-4o-mini", min_length=2, max_length=100)
    fallback_model: str = Field("gemini-1.5-flash", min_length=2, max_length=100)
    temperature: float = Field(0.2, ge=0, le=2)
    max_tokens: int = Field(1200, ge=128, le=32000)
    thinking_budget: int = Field(0, ge=0, le=4096, description="Ngân sách token suy nghĩ ngầm (0 = tắt)")


class AssistantGuardrailPolicy(BaseModel):
    block_prompt_injection: bool = True
    mask_pii: bool = True
    require_grounded_answer: bool = True
    protect_system_prompt: bool = True
    no_answer_message: str = Field(
        "Thông tin này chưa có trong nguồn chính thức. Vui lòng liên hệ đơn vị phụ trách để được hỗ trợ.",
        min_length=10,
        max_length=2000,
    )


class AssistantToolPolicy(BaseModel):
    enabled_tools: list[str] = Field(default_factory=list)
    human_approval_required: bool = True


class AssistantOutputPolicy(BaseModel):
    formats: list[Literal["markdown", "table", "checklist", "timeline"]] = Field(
        default_factory=lambda: ["markdown"]
    )
    require_citations: bool = True
    citation_format: str = Field("Tên văn bản, Điều/Khoản, Trang", max_length=200)


class AssistantEvaluationPolicy(BaseModel):
    faithfulness_threshold: float = Field(0.9, ge=0, le=1)
    answer_relevance_threshold: float = Field(0.85, ge=0, le=1)
    context_precision_threshold: float = Field(0.8, ge=0, le=1)


class AssistantLifecycleConfig(BaseModel):
    """Seven-layer enterprise lifecycle configuration for one assistant."""

    sample_questions: list[str] = Field(default_factory=list)
    persona_scope: AssistantPersonaScope = Field(default_factory=AssistantPersonaScope)
    knowledge_policy: AssistantKnowledgePolicy = Field(default_factory=AssistantKnowledgePolicy)
    model_policy: AssistantModelPolicy = Field(default_factory=AssistantModelPolicy)
    guardrails: AssistantGuardrailPolicy = Field(default_factory=AssistantGuardrailPolicy)
    tools: AssistantToolPolicy = Field(default_factory=AssistantToolPolicy)
    output_policy: AssistantOutputPolicy = Field(default_factory=AssistantOutputPolicy)
    evaluation_policy: AssistantEvaluationPolicy = Field(default_factory=AssistantEvaluationPolicy)


class AssistantRuntimeProfile(BaseModel):
    """Immutable assistant policy snapshot attached to one workflow execution."""

    assistant_id: str
    assistant_code: str
    assistant_revision: str
    tenant_id: str
    system_prompt: str
    collection_id: str
    persona_scope: AssistantPersonaScope
    knowledge_policy: AssistantKnowledgePolicy
    model_policy: AssistantModelPolicy
    guardrails: AssistantGuardrailPolicy
    tools: AssistantToolPolicy
    output_policy: AssistantOutputPolicy
    evaluation_policy: AssistantEvaluationPolicy


class AssistantCreateRequest(BaseModel):
    code: str = Field(
        ...,
        min_length=2,
        max_length=50,
        pattern=r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$",
    )
    name: str = Field(..., min_length=2, max_length=150)
    description: str = Field(..., min_length=10, max_length=500)
    avatar_url: str | None = Field(None, max_length=300)
    category: str = Field("academic", min_length=2, max_length=50)
    system_prompt: str = Field(..., min_length=20, max_length=12000)
    workflow_id: str = Field(..., min_length=2, max_length=100)
    published_workflow_version_id: str | None = Field(None, max_length=36)
    workflow_ownership: str = Field("private", max_length=20)
    collection_id: str = Field(..., min_length=2, max_length=100)
    is_active: bool = True
    tenant_id: str = Field("tenant_qnu", min_length=2, max_length=100)
    config: AssistantLifecycleConfig = Field(default_factory=AssistantLifecycleConfig)

    @field_validator(
        "code",
        "name",
        "description",
        "avatar_url",
        "category",
        "system_prompt",
        "workflow_id",
        "workflow_ownership",
        "collection_id",
        "tenant_id",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class AssistantUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=150)
    description: str | None = Field(None, min_length=10, max_length=500)
    avatar_url: str | None = Field(None, max_length=300)
    category: str | None = Field(None, min_length=2, max_length=50)
    system_prompt: str | None = Field(None, min_length=20, max_length=12000)
    workflow_id: str | None = Field(None, min_length=2, max_length=100)
    published_workflow_version_id: str | None = Field(None, max_length=36)
    workflow_ownership: str | None = Field(None, max_length=20)
    collection_id: str | None = Field(None, min_length=2, max_length=100)
    is_active: bool | None = None
    config: AssistantLifecycleConfig | None = None

    @field_validator(
        "name",
        "description",
        "avatar_url",
        "category",
        "system_prompt",
        "workflow_id",
        "workflow_ownership",
        "collection_id",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class AssistantResponse(BaseModel):
    id: str
    code: str
    name: str
    description: str
    avatar_url: str | None = None
    category: str
    system_prompt: str
    workflow_id: str
    published_workflow_version_id: str | None = None
    workflow_ownership: str = "private"
    collection_id: str
    is_active: bool
    tenant_id: str
    sample_questions: list[str] = Field(default_factory=list)
    config: AssistantLifecycleConfig
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssistantForkWorkflowResponse(BaseModel):
    assistant_code: str
    assistant_name: str
    previous_workflow_id: str
    new_workflow_id: str
    workflow_ownership: str
    message: str


class AssistantTemplateResponse(BaseModel):
    code: str
    name: str
    description: str
    category: str
    workflow_id: str
    collection_id: str
    system_prompt: str
    config: AssistantLifecycleConfig


class AssistantSeedResponse(BaseModel):
    assistants_added: int
    assistants_skipped: int
    workflows_added: int
    workflows_skipped: int
    total_assistants: int


class AssistantBundleWorkflow(BaseModel):
    id: str
    name: str
    display_name: str
    description: str | None = None
    module_code: str
    version: str = "1.0.0"
    dag_spec: dict[str, Any]


class AssistantBundle(BaseModel):
    format_version: Literal["qnu.assistant.bundle/v1"] = "qnu.assistant.bundle/v1"
    exported_at: datetime
    assistant: AssistantCreateRequest
    workflow: AssistantBundleWorkflow | None = None


class AssistantChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    conversation_id: str | None = Field(None, max_length=128)
    tenant_id: str = Field("tenant_qnu", min_length=2, max_length=100)
    stream: bool = False
    is_approved: bool = False
    attachments: list[dict[str, Any]] = Field(default_factory=list)


class AssistantChatResponse(BaseModel):
    assistant_code: str
    assistant_name: str
    answer: str
    status: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    execution_id: str | None = None
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    conversation_id: str | None = None


class AssistantGenerateRequest(BaseModel):
    """Input payload for generating an assistant specification using AI."""

    idea: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Mô tả ý tưởng hoặc mong muốn tự nhiên của cán bộ",
    )
    category_hint: str | None = Field(None, max_length=50)


class AssistantGenerateResponse(BaseModel):
    """Complete generated assistant specification ready for preview or creation."""

    name: str = Field(..., min_length=2, max_length=150)
    description: str = Field(..., min_length=10, max_length=500)
    category: str = Field("academic", min_length=2, max_length=50)
    system_prompt: str = Field(..., min_length=20, max_length=12000)
    sample_questions: list[str] = Field(default_factory=list)
    temperature: float = Field(0.2, ge=0.0, le=1.0)
    no_answer_message: str = Field(
        "Thông tin này chưa có trong nguồn chính thức của Nhà trường. Vui lòng liên hệ đơn vị phụ trách để được hỗ trợ."
    )
    suggested_workflow_id: str = "regulations-assistant"
    suggested_collection_code: str | None = None


class ReadinessCheckItem(BaseModel):
    category: str = Field(..., description="knowledge, model, tools, guardrails, evaluation")
    name: str = Field(..., description="Tên tiêu chí kiểm định")
    status: Literal["passed", "failed", "warning"] = Field(..., description="Trạng thái đạt hay chưa")
    score: int = Field(..., ge=0, le=100, description="Điểm số đạt được (0-100)")
    message: str = Field(..., description="Chi tiết giải thích kết quả")
    details: dict[str, Any] = Field(default_factory=dict)


class AssistantReadinessResponse(BaseModel):
    assistant_code: str
    assistant_name: str
    is_ready_for_publish: bool
    overall_readiness_score: int = Field(..., ge=0, le=100)
    checks: list[ReadinessCheckItem]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AssistantCloneRequest(BaseModel):
    new_code: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-z0-9_-]+$")
    new_name: str = Field(..., min_length=2, max_length=150)
    new_description: str | None = Field(None, max_length=500)
    target_collection_id: str | None = Field(None, max_length=64)


class AssistantPublishResponse(BaseModel):
    assistant_code: str
    assistant_name: str
    is_active: bool
    readiness_score: int
    published_at: datetime
    message: str


class AssistantVersionResponse(BaseModel):
    id: str
    assistant_id: str
    assistant_code: str
    version_number: str
    change_summary: str
    snapshot_data: dict[str, Any] = Field(default_factory=dict)
    created_by: str
    created_at: datetime


class AssistantRollbackResponse(BaseModel):
    assistant_code: str
    assistant_name: str
    restored_version: str
    current_version: str
    message: str
    restored_at: datetime


