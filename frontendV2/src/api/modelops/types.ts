/**
 * Type definitions for ModelOps & AI Provider domain.
 */

export type ConnectionFamily =
  | "openai"
  | "gemini"
  | "qnu"
  | "custom"
  | "anthropic";

export type Capability = "chat" | "embedding" | "rerank" | "ocr";

export type TokenLimits = {
  context_window_tokens?: number | null;
  max_output_tokens?: number | null;
};

export type Connection = {
  id: string;
  name: string;
  family: ConnectionFamily;
  base_url: string;
  timeout_seconds: number;
  is_active: boolean;
  is_connection: boolean;
  prefix?: string | null;
  api_type?: string | null;
  model_count: number;
  active_model_count: number;
  active_keys_count: number;
  total_keys_count: number;
  last_probe_status:
    | "success"
    | "failed"
    | "unsupported"
    | "untested"
    | "stale";
  last_probe_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type ConnectionInput = {
  name: string;
  family: ConnectionFamily;
  base_url: string;
  timeout_seconds: number;
  prefix?: string | null;
  api_type?: string | null;
  is_active?: boolean;
};

export type ConnectionUpdateInput = Partial<ConnectionInput>;

export type ConnectionTestRequest = {
  key_id?: string;
  api_key?: string;
  model_name?: string;
};

export type DiscoveredModel = {
  id: string;
  context_window_tokens: number | null;
  max_output_tokens: number | null;
  embedding_dimension: number | null;
};

export type ConnectionTestResult = {
  ok: boolean;
  key_id?: string | null;
  check_id?: string | null;
  code?: string;
  http_status?: number | null;
  tested_at?: string | null;
  latency_ms?: number | null;
  detail: string;
  models?: string[];
  model_metadata?: DiscoveredModel[];
};

export type ModelProvider = {
  id: string;
  parent_id?: string | null;
  name: string;
  provider_type: string;
  model_name: string;
  capabilities: Capability[];
  base_url: string;
  timeout_seconds: number;
  is_active: boolean;
  is_connection?: boolean;
  token_limits?: TokenLimits | null;
  embedding_dimension?: number | null;
  capacity_status?: string;
  created_at: string;
  updated_at: string;
};

export type ConnectionModelCreateInput = {
  model_name: string;
  capabilities: Capability[];
  token_limits?: TokenLimits | null;
  embedding_dimension?: number | null;
  discovery_check_id?: string | null;
};

export type ProviderKey = {
  id: string;
  provider_id: string;
  name: string;
  masked_hint: string;
  status: "active" | "revoked" | "cooldown";
  priority: number;
  created_at: string;
  updated_at: string;
};

export type KeyCreateRequest = {
  name: string;
  secret: string;
  priority?: number;
};

export type DiagnosticCheck = {
  id: string;
  key_id?: string | null;
  kind: "discovery" | Capability;
  outcome: "ok" | "failed" | "unsupported";
  configuration_status: "current" | "stale";
  tested_at: string;
  latency_ms: number | null;
  code: string;
  detail: string;
  http_status?: number | null;
  retry_after?: string | null;
  requested_model?: string;
  observed_model?: string | null;
  observed_dimension?: number | null;
  total_tokens?: number | null;
  models?: string[];
  model_metadata?: DiscoveredModel[];
};

export type ProviderDiagnostics = {
  provider_id: string;
  configured_active: boolean;
  checks: DiagnosticCheck[];
  observed_output_limits: ObservedOutputLimit[];
};

export type ObservedOutputLimit = {
  endpoint: string;
  model_name: string;
  max_output_tokens: number;
  observed_at: string;
  expires_at: string;
  source: "observed";
  configuration_status: "current" | "stale";
};

export type ModelDefaults = {
  chat_provider_id: string | null;
  chat_model: string | null;
  embedding_provider_id: string | null;
  embedding_model: string | null;
  rerank_provider_id: string | null;
  rerank_model: string | null;
  ocr_provider_id: string | null;
  ocr_model: string | null;
  updated_by?: string | null;
  updated_at?: string | null;
  extra?: Record<string, unknown>;
};

export type DefaultsUpdateRequest = {
  chat_provider_id?: string | null;
  chat_model?: string | null;
  embedding_provider_id?: string | null;
  embedding_model?: string | null;
  rerank_provider_id?: string | null;
  rerank_model?: string | null;
  ocr_provider_id?: string | null;
  ocr_model?: string | null;
};

export type CatalogItem = {
  id: string;
  name: string;
  model_name: string;
  provider_type?: string | null;
  capabilities: Capability[];
  default_capabilities: Capability[];
  token_limits?: Record<string, unknown> | null;
  capacity_status?: "unknown" | "configured" | "stale";
  capacity_basis?: "operator_configured" | "server_reported" | null;
  embedding_dimension?: number | null;
  embedding_dimension_status?: "unknown" | "configured" | "stale";
};
