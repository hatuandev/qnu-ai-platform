/** Types for ModelOps: Providers, Keys, Presets, Defaults, Quotas */

export interface ProviderApiKey {
  id: string;
  name: string;
  api_key_masked: string;
  account_id?: string | null;
  priority: number;
  is_active: boolean;
  status: "active" | "rate_limited" | "exhausted" | "inactive";
  quota_limit?: number | null;
  usage_tokens: number;
  cooldown_until?: string | null;
  last_used_at?: string | null;
  created_at?: string | null;
}

export interface SingleModelTestResult {
  model_name: string;
  success: boolean;
  status: "available" | "unavailable" | "rate_limited" | "error";
  latency_ms: number;
  message: string;
  tested_at: string;
}

export interface ProviderModelsTestResponse {
  provider_id: string;
  total_models: number;
  available_models: number;
  unavailable_models: number;
  results: SingleModelTestResult[];
}

export interface ProviderPreset {
  code: string;
  name: string;
  category: "cloud" | "local" | "custom";
  icon: string;
  description: string;
  default_base_url?: string | null;
  placeholder_key: string;
  help_text: string;
  requires_account_id?: boolean;
  suggested_models?: string[];
}

export interface ModelProvider {
  id: string;
  name: string;
  code: string;
  type:
    | "openai"
    | "gemini"
    | "claude"
    | "local"
    | "local_vllm"
    | "ollama"
    | "deepseek"
    | "groq"
    | "openrouter"
    | "mistral"
    | "cloudflare"
    | "nvidia"
    | "sentence_transformers"
    | "docling"
    | "custom";
  is_active: boolean;
  circuit_breaker_status: "CLOSED" | "OPEN" | "HALF_OPEN";
  models: string[];
  model_name?: string;
  api_base_url?: string;
  api_key_masked?: string;
  account_id?: string;
  latency_ms: number;
  failure_rate: number;
  priority?: number;
  timeout_seconds?: number;
  keys_count?: number;
  api_keys?: ProviderApiKey[];
}

export interface ModelOption {
  provider_id: string;
  provider_name: string;
  provider_type: string;
  model_name: string;
  category: "cloud" | "local" | "custom";
  description?: string;
}

export interface OCRComboItem {
  provider_id: string;
  provider_name: string;
  model_name: string;
  provider_type?: string;
  is_active?: boolean;
  description?: string;
}

export type ModelComboTaskType = "ocr" | "embedding" | "reranker" | "chat";

export interface ModelComboItem {
  id: string;
  name: string;
  task_type?: ModelComboTaskType;
  strategy: "fallback" | "round_robin" | "fusion";
  models: OCRComboItem[];
  is_default?: boolean;
  description?: string;
}

export interface VisionAdapterConfig {
  enabled: boolean;
  strategy: "fallback" | "round_robin";
  models: OCRComboItem[];
}

export interface SystemModelDefaults {
  // Embedding
  default_embedding_provider_id: string;
  default_embedding_model: string;
  default_embedding_mode?: "combo" | "single";
  default_embedding_combo_id?: string | null;
  embedding_combo_chain?: OCRComboItem[];

  // Reranker
  default_reranker_provider_id: string;
  default_reranker_model: string;
  default_reranker_mode?: "combo" | "single";
  default_reranker_combo_id?: string | null;
  reranker_combo_chain?: OCRComboItem[];

  // Vision OCR
  default_ocr_provider_id: string;
  default_ocr_model: string;
  default_ocr_mode?: "combo" | "single";
  default_ocr_combo_id?: string | null;
  ocr_combo_chain?: OCRComboItem[];

  // Chat & Reasoning
  default_chat_provider_id?: string;
  default_chat_model?: string;
  default_chat_mode?: "combo" | "single";
  default_chat_combo_id?: string | null;
  chat_combo_chain?: OCRComboItem[];

  // Hub combos & Vision adapter
  model_combos?: ModelComboItem[];
  vision_adapter?: VisionAdapterConfig;
}

export interface SystemModelDefaultsResponse {
  defaults: SystemModelDefaults;
  available_embeddings: ModelOption[];
  available_rerankers: ModelOption[];
  available_ocrs: ModelOption[];
}

export interface TokenQuota {
  tenant_id: string;
  total_tokens: number;
  limit_tokens: number;
  usd_cost: number;
  reset_date: string;
  provider_breakdown: {
    openai_tokens: number;
    gemini_tokens: number;
    local_tokens: number;
  };
}

export interface ModelUsageBreakdownItem {
  model_name: string;
  provider: string;
  total_requests: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
}

export interface DailyUsageItem {
  date: string;
  requests: number;
  total_tokens: number;
  cost_usd: number;
}

export interface UsageStatsResponse {
  total_requests: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  models_breakdown: ModelUsageBreakdownItem[];
  daily_usage: DailyUsageItem[];
}

export type ConflictStrategy = "overwrite" | "skip" | "create_new";

export interface ProviderExportItem {
  id?: string;
  name: string;
  code?: string;
  provider_type: string;
  model_name?: string;
  models: string[];
  api_base_url?: string;
  api_key?: string;
  account_id?: string;
  priority: number;
  timeout_seconds: number;
  is_active: boolean;
  extra_config: Record<string, unknown>;
  api_keys: Array<{
    name: string;
    api_key?: string;
    account_id?: string;
    priority: number;
    is_active: boolean;
    quota_limit?: number | null;
  }>;
}

export interface ProviderSingleExportResponse {
  version: string;
  export_type: "single_provider";
  exported_at: string;
  provider: ProviderExportItem;
}

export interface ProviderBulkExportResponse {
  version: string;
  export_type: "all_providers";
  exported_at: string;
  total_providers: number;
  providers: ProviderExportItem[];
}

export interface ProviderImportResponse {
  success: boolean;
  total_processed: number;
  imported: number;
  updated: number;
  skipped: number;
  errors: string[];
  message: string;
}
