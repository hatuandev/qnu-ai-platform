/**
 * TypeScript types for QNU AI Workspace domain.
 * Mirrors `backendV1/qnu/domains/workspaces/schemas.py`.
 */

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

export type WorkspaceResolveRouteResponse = {
  workspace_id: string;
  code: string;
  collection_id: string | null;
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

/**
 * Payload for POST /workspaces.
 * Backend requires `code` matching `^[a-z0-9]+(?:[-_][a-z0-9]+)*$` and `name`.
 * Backend forbids extra fields (`ConfigDict(extra="forbid")`).
 */
export type WorkspaceCreateInput = {
  code: string;
  name: string;
  description?: string | null;
};

/**
 * Payload for PATCH /workspaces/{workspace_id}.
 * Backend forbids updating `code` and forbids extra fields.
 */
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

export type PageParams = {
  page: number;
  pageSize: number;
};

export type QuotaResponse = {
  workspace_id: string;
  month_period: string;
  monthly_token_limit: number | null;
  tokens_used: number;
  tokens_reserved: number;
  is_blocked: boolean;
  configured: boolean;
};

/**
 * Aligned with `backendV1/qnu/domains/modelops/schemas.py:UsageResponse`.
 */
export type UsageResponse = {
  id: string;
  workspace_id: string;
  provider_id: string;
  request_id: string;
  capability: string;
  model_name: string;
  status: string;
  reserved_tokens: number;
  total_tokens: number | null;
  cost_usd: number | string | null;
  created_at: string;
};
