/** Shapes returned by backendV1 ModelOps endpoints (`qnu/domains/modelops/schemas.py`). */

export type ProviderType =
  | "openai_compatible"
  | "gemini"
  | "local"
  | "nemotron"
  | "paddleocr";

export type Capability = "chat" | "embedding" | "rerank" | "ocr";

export const CAPABILITIES: readonly Capability[] = [
  "chat",
  "embedding",
  "rerank",
  "ocr",
];

export const CAPABILITY_LABELS: Record<Capability, string> = {
  chat: "Chat",
  embedding: "Embedding",
  rerank: "Rerank",
  ocr: "OCR",
};

export const PROVIDER_TYPE_LABELS: Record<ProviderType, string> = {
  openai_compatible: "OpenAI compatible",
  gemini: "Gemini",
  local: "Local",
  nemotron: "Nemotron",
  paddleocr: "PaddleOCR",
};

/** `unknown` means "chưa khai báo"; `stale` means the endpoint/model changed. */
export type CapacityStatus = "unknown" | "configured" | "stale";

export type OcrPageInputBudget = {
  max_image_width: number;
  max_image_height: number;
  input_tokens_upper_bound: number;
  prompt_sha256: string;
};

export type TokenLimits = {
  context_window_tokens: number | null;
  max_input_tokens: number | null;
  max_output_tokens: number | null;
  ocr_page_input: OcrPageInputBudget | null;
};

export type Provider = {
  id: string;
  name: string;
  provider_type: ProviderType;
  base_url: string;
  model_name: string;
  capabilities: string[];
  is_active: boolean;
  priority: number;
  timeout_seconds: number;
  token_limits: TokenLimits | null;
  capacity_status: CapacityStatus;
  capacity_basis: "operator_configured" | null;
  embedding_dimension: number | null;
  embedding_dimension_status: CapacityStatus;
  created_at: string;
  updated_at: string;
};

export type ProviderCreateInput = {
  name: string;
  provider_type: ProviderType;
  base_url: string;
  model_name: string;
  capabilities: Capability[];
  priority: number;
  timeout_seconds: number;
  token_limits?: TokenLimits | null;
  embedding_dimension?: number | null;
};

/** Omit a field to keep it; `null` clears a nullable declaration explicitly. */
export type ProviderUpdateInput = Partial<
  Omit<ProviderCreateInput, "provider_type">
> & { is_active?: boolean };

export type ProviderKey = {
  lease_until?: string | null;
  cooldown_until?: string | null;
  consecutive_failures?: number;
  id: string;
  provider_id: string;
  name: string;
  masked_hint: string;
  status: "active" | "revoked";
  priority: number;
  created_at: string;
  updated_at: string;
};

export type KeyAudit = {
  id: string;
  actor_ref: string | null;
  key_id: string | null;
  action: string;
  reason: string | null;
  created_at: string;
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
  updated_by: string | null;
  updated_at: string | null;
};

export type DefaultsUpdateInput = Partial<
  Record<
    | "chat_provider_id"
    | "chat_model"
    | "embedding_provider_id"
    | "embedding_model"
    | "rerank_provider_id"
    | "rerank_model"
    | "ocr_provider_id"
    | "ocr_model",
    string | null
  >
>;

export type CatalogItem = {
  id: string;
  name: string;
  model_name: string;
  capabilities: string[];
  default_capabilities: string[];
};

export type ModelOpsEvent = {
  id: string;
  actor_ref: string;
  action: string;
  provider_id: string | null;
  detail: Record<string, unknown>;
  created_at: string;
};

export type KeyCreateInput = {
  name: string;
  secret: string;
  priority: number;
};

export type KeyRotateInput = KeyCreateInput & { reason?: string | null };
export type KeyRevokeInput = { reason?: string | null };
