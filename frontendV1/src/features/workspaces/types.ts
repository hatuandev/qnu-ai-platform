/** Shapes returned by backendV1 workspace endpoints (`qnu/domains/workspaces/schemas.py`). */

export type PageMeta = {
  page: number;
  page_size: number;
  total: number;
};

export type Page<T> = {
  items: T[];
  meta: PageMeta;
};

export type WorkspaceStatus = "active" | "suspended";
export type WorkspaceRole = "admin" | "editor" | "reviewer" | "member";
export type MemberStatus = "active" | "pending" | "revoked";

export type Workspace = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  status: WorkspaceStatus;
  member_count: number;
  created_at: string;
  updated_at: string;
};

export type WorkspaceMember = {
  id: string;
  workspace_id: string;
  actor_ref: string;
  display_name: string | null;
  role: WorkspaceRole;
  status: MemberStatus;
  invited_by: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkspaceEvent = {
  id: string;
  workspace_id: string;
  actor_ref: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  detail: Record<string, unknown>;
  created_at: string;
};

export type WorkspaceCreateInput = {
  code: string;
  name: string;
  description?: string | null;
};

/** `code` is intentionally absent: PATCH does not accept it. */
export type WorkspaceUpdateInput = {
  name?: string;
  description?: string | null;
  status?: WorkspaceStatus;
};

export type MemberCreateInput = {
  actor_ref: string;
  role: WorkspaceRole;
  display_name?: string | null;
};

export type MemberUpdateInput = {
  role?: WorkspaceRole;
  status?: MemberStatus;
};

export type PageParams = { page: number; pageSize: number };

/** Capability keys accepted by the model allowlist contract. */
export type Capability = "chat" | "embedding" | "rerank" | "ocr";

export const CAPABILITIES: readonly Capability[] = [
  "chat",
  "embedding",
  "rerank",
  "ocr",
];

export type AllowedProviderItem = {
  provider_id: string;
  name: string;
  capabilities: string[];
  is_active: boolean;
  is_default: boolean;
  default_capabilities: Capability[];
};

export type AllowlistResponse = {
  workspace_id: string;
  providers: AllowedProviderItem[];
};

export type AllowlistUpdateInput = {
  provider_ids: string[];
  defaults: Partial<Record<Capability, string>>;
};

export type WorkspaceDefaultsInput = {
  defaults: Partial<Record<Capability, string>>;
};

export type Quota = {
  workspace_id: string;
  month_period: string;
  monthly_token_limit: number | null;
  tokens_used: number;
  tokens_reserved: number;
  is_blocked: boolean;
  /** False means "chưa cấu hình", which is not the same as "không giới hạn". */
  configured: boolean;
};

export type UsageRecord = {
  id: string;
  workspace_id: string;
  provider_id: string;
  request_id: string;
  capability: string;
  model_name: string;
  status: string;
  reserved_tokens: number;
  total_tokens: number | null;
  /** Pydantic serialises Decimal as a string; null means unknown, not zero. */
  cost_usd: string | number | null;
  created_at: string;
};
