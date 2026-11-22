/**
 * TypeScript definitions for External Integrations & API Keys.
 * Mirrors `backendV1/qnu/domains/integration/schemas.py`.
 */

export type IntegrationConfig = {
  base_url: string;
  openai_endpoint: string;
  supported_protocols: string[];
  capabilities: string[];
  version: string;
};

export type AppClient = {
  id: string;
  workspace_id: string;
  name: string;
  description: string;
  status: string;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type AppClientCreate = {
  name: string;
  description?: string;
};

export type AppApiKeyStatus = "active" | "suspended" | "revoked";

export type AppApiKey = {
  id: string;
  app_id: string;
  app_name: string;
  workspace_id: string;
  name: string;
  key_prefix: string;
  status: AppApiKeyStatus;
  allowed_assistant_ids: string[];
  rate_limit_rpm: number | null;
  rate_limit_rpd: number | null;
  expires_at: string | null;
  last_used_at: string | null;
  rotated_from_key_id: string | null;
  revoked_at: string | null;
  revoked_reason: string | null;
  created_by: string;
  created_at: string;
};

export type AppApiKeySecret = AppApiKey & {
  secret_key: string;
};

export type AppApiKeyCreate = {
  name: string;
  app_id?: string;
  app_name?: string;
  allowed_assistant_ids: string[];
  allow_all_assistants: boolean;
  rate_limit_rpm?: number | null;
  rate_limit_rpd?: number | null;
  expires_in_days?: number | null;
  idempotency_key?: string | null;
};

export type AppApiKeyStatusUpdate = {
  status: "active" | "suspended";
  reason?: string;
};

export type AppApiKeyRotateRequest = {
  expires_in_days?: number | null;
  idempotency_key?: string | null;
};

export type AppApiKeyRevokeRequest = {
  reason: string;
};

export type AppRequestLog = {
  id: string;
  app_id: string;
  key_id: string;
  workspace_id: string;
  assistant_id: string;
  endpoint: string;
  status_code: number;
  latency_ms: number;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  error_code: string | null;
  created_at: string;
};
