"""Pydantic Schemas for ModelOps — LLM Requests, Provider Catalog Presets, Key Pool & Quotas."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"] = Field(
        ..., description="Vai trò: system, user, hoặc assistant"
    )
    content: str = Field(..., min_length=1, description="Nội dung tin nhắn")


class LLMGenerateRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1, description="Danh sách ngữ cảnh tin nhắn")
    tenant_id: str = Field("qnu-default", description="Mã định danh đơn vị / khoa phòng")
    assistant_code: str | None = Field(
        None, description="Mã trợ lý: admissions, regulations, library..."
    )
    conversation_id: str | None = Field(None, description="Mã phiên hội thoại")
    temperature: float = Field(0.2, ge=0.0, le=2.0, description="Độ sáng tạo")
    max_tokens: int = Field(2000, ge=50, le=8192, description="Giới hạn số token đầu ra")
    stream: bool = Field(False, description="Bật chế độ Streaming SSE")
    preferred_provider_id: str | None = Field(
        None, description="Mã nhà cung cấp được Trợ lý AI ưu tiên chỉ định"
    )
    preferred_model_name: str | None = Field(
        None, description="Tên mô hình chính (primary model) được Trợ lý AI chỉ định"
    )
    fallback_model_name: str | None = Field(
        None, description="Tên mô hình dự phòng (fallback model) được Trợ lý AI chỉ định"
    )


class LLMGenerateResponse(BaseModel):
    content: str = Field(..., description="Văn bản sinh ra từ mô hình")
    provider: str = Field(..., description="Nhà cung cấp đã phục vụ: openai, gemini, local_vllm")
    model: str = Field(..., description="Tên mô hình cụ thể")
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    is_fallback: bool = Field(
        False, description="True nếu phải chuyển sang nhà cung cấp dự phòng"
    )
    active_key_id: str | None = Field(None, description="ID của API Key đã phục vụ yêu cầu")


# ---------------- Key Pool Schemas ----------------


class ProviderKeyItem(BaseModel):
    id: str
    name: str
    api_key_masked: str
    account_id: str | None = None
    priority: int = 1
    is_active: bool = True
    status: Literal["active", "rate_limited", "exhausted", "inactive"] = "active"
    quota_limit: int | None = None
    usage_tokens: int = 0
    cooldown_until: str | None = None
    last_used_at: str | None = None
    created_at: str | None = None


class ProviderKeyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Tên nhãn gợi nhớ (VD: Key Khoa CNTT 1)")
    api_key: str = Field(..., min_length=4, description="Mã khóa API bí mật (Secret Key)")
    account_id: str | None = Field(None, description="Cloudflare Account ID (cho nhà cung cấp Cloudflare)")
    priority: int = Field(1, ge=1, le=99, description="Mức độ ưu tiên (1 = ưu tiên dùng trước)")
    quota_limit: int | None = Field(None, ge=1000, description="Hạn mức token cho key này (None = không giới hạn)")


class ProviderKeyUpdate(BaseModel):
    name: str | None = None
    account_id: str | None = None
    priority: int | None = Field(None, ge=1, le=99)
    is_active: bool | None = None
    status: Literal["active", "rate_limited", "exhausted", "inactive"] | None = None
    quota_limit: int | None = None


class SimulateKeyRotationRequest(BaseModel):
    tokens_consumed: int = Field(5000, ge=0, description="Số lượng token giả định tiêu thụ")
    trigger_rate_limit: bool = Field(True, description="Kích hoạt lỗi Rate Limit 429 để kiểm tra cơ chế nhảy key")
    cooldown_seconds: int = Field(60, ge=5, le=3600, description="Thời gian cooldown của key bị 429")


class SimulateKeyRotationResponse(BaseModel):
    success: bool
    previous_key_id: str
    previous_key_name: str
    next_key_id: str | None = None
    next_key_name: str | None = None
    tokens_consumed: int
    rate_limit_triggered: bool
    rotated: bool
    message: str


class ProviderKeyTestResponse(BaseModel):
    success: bool
    latency_ms: float
    message: str


# ---------------- Provider Config Schemas ----------------


class ProviderConfigCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    provider_type: str = Field(
        ..., description="openai, gemini, claude, local_vllm, ollama, deepseek, groq, openrouter, mistral, cloudflare, nvidia, custom"
    )
    model_name: str | None = Field(None, max_length=100)
    models: list[str] = Field(default_factory=list, description="Danh sách các mô hình khả dụng")
    api_base_url: str | None = None
    api_key: str | None = None
    account_id: str | None = None
    priority: int = Field(1, ge=1, le=10, description="1 là ưu tiên cao nhất")
    timeout_seconds: int = Field(15, ge=5, le=120)
    is_active: bool = True
    extra_config: dict[str, Any] = Field(default_factory=dict)


class ProviderConfigUpdate(BaseModel):
    name: str | None = None
    provider_type: str | None = None
    model_name: str | None = None
    models: list[str] | None = None
    api_base_url: str | None = None
    api_key: str | None = None
    account_id: str | None = None
    priority: int | None = None
    is_active: bool | None = None
    timeout_seconds: int | None = None
    extra_config: dict[str, Any] | None = None


class ProviderConfigResponse(BaseModel):
    id: str
    name: str
    code: str | None = None
    provider_type: str
    model_name: str | None = None
    models: list[str] = Field(default_factory=list)
    api_base_url: str | None = None
    api_key_masked: str | None = None
    account_id: str | None = None
    priority: int = 1
    is_active: bool = True
    timeout_seconds: int = 15
    circuit_breaker_status: str = "CLOSED"
    latency_ms: float = 0.0
    failure_rate: float = 0.0
    keys_count: int = 0
    api_keys: list[ProviderKeyItem] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ProviderTestResponse(BaseModel):
    success: bool
    latency_ms: float
    message: str


class TenantQuotaResponse(BaseModel):
    tenant_id: str
    month_period: str
    monthly_token_limit: int
    monthly_cost_limit_usd: float
    tokens_used: int
    cost_used_usd: float
    is_blocked: bool
    usage_percent: float = Field(..., description="Phần trăm hạn ngạch token đã sử dụng")

    model_config = {"from_attributes": True}


# ---------------- Predefined Provider Catalog Presets ----------------


class ProviderPresetItem(BaseModel):
    code: str
    name: str
    category: Literal["cloud", "local", "custom"]
    icon: str
    description: str
    default_base_url: str | None = None
    placeholder_key: str
    help_text: str
    requires_account_id: bool = False


PROVIDER_PRESETS: list[ProviderPresetItem] = [
    ProviderPresetItem(
        code="openai",
        name="OpenAI",
        category="cloud",
        icon="cpu",
        description="Hệ thống mô hình flagship toàn cầu từ OpenAI (GPT-4o, GPT-4o-mini).",
        default_base_url="https://api.openai.com/v1",
        placeholder_key="sk-proj-...",
        help_text="Lấy từ platform.openai.com/api-keys.",
    ),
    ProviderPresetItem(
        code="gemini",
        name="Google Gemini",
        category="cloud",
        icon="sparkles",
        description="Mô hình đa phương thức tốc độ cao với cửa sổ ngữ cảnh khổng lồ từ Google AI Studio.",
        default_base_url="https://generativelanguage.googleapis.com/v1beta",
        placeholder_key="AIzaSy...",
        help_text="Lấy từ aistudio.google.com/app/apikey.",
    ),
    ProviderPresetItem(
        code="claude",
        name="Anthropic Claude",
        category="cloud",
        icon="server",
        description="Hệ mô hình Claude thông minh về coding, phân tích dữ liệu và an toàn từ Anthropic.",
        default_base_url="https://api.anthropic.com/v1",
        placeholder_key="sk-ant-api03-...",
        help_text="Lấy từ console.anthropic.com/settings/keys.",
    ),
    ProviderPresetItem(
        code="deepseek",
        name="DeepSeek AI",
        category="cloud",
        icon="cpu",
        description="Mô hình lý luận và lập trình mã nguồn mở hiệu năng cao với chi phí tối ưu hàng đầu.",
        default_base_url="https://api.deepseek.com/v1",
        placeholder_key="sk-...",
        help_text="Lấy từ platform.deepseek.com/api_keys.",
    ),
    ProviderPresetItem(
        code="groq",
        name="Groq Cloud (LPU)",
        category="cloud",
        icon="cpu",
        description="Nền tảng vi xử lý suy luận LPU siêu tốc đạt tốc độ trên 300 tokens/giây.",
        default_base_url="https://api.groq.com/openai/v1",
        placeholder_key="gsk_...",
        help_text="Lấy từ console.groq.com/keys.",
    ),
    ProviderPresetItem(
        code="openrouter",
        name="OpenRouter AI Gateway",
        category="cloud",
        icon="globe",
        description="Cổng định tuyến AI Gateway toàn cầu tập hợp hơn 200+ mô hình với nhiều mô hình miễn phí (:free).",
        default_base_url="https://openrouter.ai/api/v1",
        placeholder_key="sk-or-v1-...",
        help_text="Lấy từ openrouter.ai/keys.",
    ),
    ProviderPresetItem(
        code="mistral",
        name="Mistral AI",
        category="cloud",
        icon="cpu",
        description="Nền tảng mô hình mã nguồn mở và thương mại hàng đầu châu Âu tối ưu cho lập trình và OCR.",
        default_base_url="https://api.mistral.ai/v1",
        placeholder_key="Nhập API Key từ console.mistral.ai...",
        help_text="Lấy từ console.mistral.ai/api-keys.",
    ),
    ProviderPresetItem(
        code="cloudflare",
        name="Cloudflare Workers AI",
        category="cloud",
        icon="cloud",
        description="Serverless AI model gateway chạy trên mạng Edge của Cloudflare. Yêu cầu Account ID.",
        default_base_url="https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run",
        placeholder_key="cf-workers-ai-token-...",
        help_text="Lấy từ Cloudflare Dashboard > Workers & Pages > Overview và My Profile > API Tokens.",
        requires_account_id=True,
    ),
    ProviderPresetItem(
        code="nvidia",
        name="NVIDIA NIM",
        category="cloud",
        icon="cpu",
        description="Tăng tốc suy luận GPU qua NVIDIA NIM Cloud Functions hoặc on-prem container.",
        default_base_url="https://integrate.api.nvidia.com/v1",
        placeholder_key="nvapi-...",
        help_text="Lấy từ build.nvidia.com.",
    ),
    ProviderPresetItem(
        code="ollama",
        name="Ollama (Local / On-Premise)",
        category="local",
        icon="server",
        description="Máy chủ GPU nội bộ phục vụ suy luận riêng tư, bảo mật dữ liệu tuyệt đối của Trường ĐH Quy Nhơn.",
        default_base_url="http://localhost:11434/v1",
        placeholder_key="Để trống nếu không bật auth",
        help_text="Địa chỉ API tương thích OpenAI của server Ollama nội bộ.",
    ),
    ProviderPresetItem(
        code="local_vllm",
        name="Local vLLM Server",
        category="local",
        icon="server",
        description="Engine suy luận GPU vLLM tối ưu throughput cao chạy trực tiếp trong hạ tầng mạng trường QNU.",
        default_base_url="http://localhost:8000/v1",
        placeholder_key="Để trống nếu không yêu cầu key",
        help_text="Địa chỉ vLLM endpoint tương thích OpenAI.",
    ),
    ProviderPresetItem(
        code="sentence_transformers",
        name="Local SentenceTransformers (PyTorch)",
        category="local",
        icon="server",
        description="Mô hình nhúng vector BAAI/bge-m3 1024D chạy cục bộ trên máy chủ QNU, không tốn chi phí và bảo mật tuyệt đối.",
        default_base_url="",
        placeholder_key="Không yêu cầu API Key",
        help_text="Chạy in-process qua PyTorch và HuggingFace weights.",
    ),
    ProviderPresetItem(
        code="docling",
        name="Docling Local (IBM Research)",
        category="local",
        icon="server",
        description="Bộ bóc tách bố cục tài liệu và bảng biểu chuyên sâu TableFormer chạy offline nội bộ của IBM Research.",
        default_base_url="",
        placeholder_key="Không yêu cầu API Key",
        help_text="Bóc tách PDF/DOCX/XLSX đa cột thành Markdown có cấu trúc.",
    ),
    ProviderPresetItem(
        code="custom",
        name="Tùy Chỉnh (OpenAI Compatible)",
        category="custom",
        icon="cpu",
        description="Kết nối tới bất kỳ máy chủ mô hình nào hỗ trợ chuẩn OpenAI API (FastChat, LocalAI, Private Proxy...).",
        default_base_url="https://api.your-provider.com/v1",
        placeholder_key="sk-...",
        help_text="Địa chỉ endpoint và API Key của hệ thống riêng.",
    ),
]


# ---------------- System Model Routing Defaults Schemas ----------------


class ModelOption(BaseModel):
    provider_id: str
    provider_name: str
    provider_type: str
    model_name: str
    category: str = "cloud"  # "cloud" | "local" | "custom"
    description: str | None = None


class SystemModelDefaults(BaseModel):
    default_embedding_provider_id: str = "prov_cloudflare"
    default_embedding_model: str = "@cf/baai/bge-m3"
    default_reranker_provider_id: str = "prov_cloudflare"
    default_reranker_model: str = "@cf/baai/bge-reranker-base"
    default_ocr_provider_id: str = "prov_mistral"
    default_ocr_model: str = "mistral-ocr-latest"


class SystemModelDefaultsUpdate(BaseModel):
    default_embedding_provider_id: str | None = None
    default_embedding_model: str | None = None
    default_reranker_provider_id: str | None = None
    default_reranker_model: str | None = None
    default_ocr_provider_id: str | None = None
    default_ocr_model: str | None = None


class SystemModelDefaultsResponse(BaseModel):
    defaults: SystemModelDefaults
    available_embeddings: list[ModelOption] = Field(default_factory=list)
    available_rerankers: list[ModelOption] = Field(default_factory=list)
    available_ocrs: list[ModelOption] = Field(default_factory=list)


class SetDefaultModelRequest(BaseModel):
    role: Literal["embedding", "reranker", "ocr"] = Field(
        ..., description="Vai trò mặc định cần gán: embedding, reranker, hoặc ocr"
    )
    model_name: str = Field(..., min_length=1, description="Tên mô hình cần gán làm mặc định")


# ---------------- Model Validity Testing Schemas ----------------


class SingleModelTestResult(BaseModel):
    model_name: str
    success: bool
    status: Literal["available", "unavailable", "rate_limited", "error"]
    latency_ms: float = 0.0
    message: str
    tested_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ProviderModelsTestRequest(BaseModel):
    model_name: str | None = Field(
        default=None,
        description="Tên mô hình cụ thể cần kiểm tra. Nếu để trống, hệ thống sẽ kiểm tra tất cả mô hình của Provider.",
    )


class ProviderModelsTestResponse(BaseModel):
    provider_id: str
    total_models: int
    available_models: int
    unavailable_models: int
    results: list[SingleModelTestResult] = Field(default_factory=list)


# ---------------- Real-time Usage & Cost Tracking Schemas ----------------


class ModelUsageBreakdownItem(BaseModel):
    model_name: str
    provider: str
    total_requests: int
    total_tokens: int
    total_cost_usd: float
    avg_latency_ms: float


class DailyUsageItem(BaseModel):
    date: str  # YYYY-MM-DD
    requests: int
    total_tokens: int
    cost_usd: float


class UsageStatsResponse(BaseModel):
    total_requests: int
    total_tokens: int
    total_cost_usd: float
    avg_latency_ms: float
    models_breakdown: list[ModelUsageBreakdownItem] = Field(default_factory=list)
    daily_usage: list[DailyUsageItem] = Field(default_factory=list)


# ---------------- Provider Import & Export Schemas ----------------


class ProviderKeyExportItem(BaseModel):
    name: str
    api_key: str | None = None
    account_id: str | None = None
    priority: int = 1
    is_active: bool = True
    quota_limit: int | None = None


class ProviderExportItem(BaseModel):
    id: str | None = None
    name: str
    code: str | None = None
    provider_type: str
    model_name: str | None = None
    models: list[str] = Field(default_factory=list)
    api_base_url: str | None = None
    api_key: str | None = None
    account_id: str | None = None
    priority: int = 1
    timeout_seconds: int = 15
    is_active: bool = True
    extra_config: dict[str, Any] = Field(default_factory=dict)
    api_keys: list[ProviderKeyExportItem] = Field(default_factory=list)


class ProviderSingleExportResponse(BaseModel):
    version: str = "1.0"
    export_type: Literal["single_provider"] = "single_provider"
    exported_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    provider: ProviderExportItem


class ProviderBulkExportResponse(BaseModel):
    version: str = "1.0"
    export_type: Literal["all_providers"] = "all_providers"
    exported_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    total_providers: int
    providers: list[ProviderExportItem]


class ProviderImportRequest(BaseModel):
    data: Any = Field(..., description="Cấu hình JSON của 1 provider hoặc toàn bộ danh sách providers")
    conflict_strategy: Literal["overwrite", "skip", "create_new"] = Field(
        "overwrite",
        description="Chiến lược khi trùng provider: overwrite (ghi đè), skip (bỏ qua), create_new (tạo mới với tên mới)",
    )


class ProviderImportResponse(BaseModel):
    success: bool
    total_processed: int
    imported: int
    updated: int
    skipped: int
    errors: list[str] = Field(default_factory=list)
    message: str




