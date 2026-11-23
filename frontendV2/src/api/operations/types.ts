export interface SystemResetRequest {
  confirm_phrase: string;
  seed_workspace?: boolean;
  seed_modelops?: boolean;
  seed_assistant?: boolean;
}

export interface SystemResetResponse {
  success: boolean;
  message: string;
  workspace_id?: string | null;
  assistant_id?: string | null;
  stats: {
    tables_truncated?: number;
    qdrant_collections_deleted?: number;
    blob_objects_purged?: number;
    redis_keys_cleared?: number;
    workspace_code?: string;
    workspace_name?: string;
    collection_id?: string;
    assistant_id?: string;
    publication_slug?: string;
    modelops_defaults?: Record<string, string>;
    [key: string]: unknown;
  };
}

export interface OperationJobItem {
  id: string;
  kind: "ocr" | "index" | "compiler" | "spelling" | "backup" | string;
  workspace_id: string;
  collection_id?: string | null;
  source_id?: string | null;
  revision_id?: string | null;
  compilation_run_id?: string | null;
  status: "queued" | "running" | "completed" | "failed" | string;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  lease_expires_at?: string | null;
  progress_done?: number | null;
  progress_total?: number | null;
  usage_tokens?: number | null;
  error_code?: string | null;
  recovery_allowed?: boolean;
  recovery_reason?: string;
}

export interface OperationJobListResponse {
  items: OperationJobItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface WorkspaceBackupItem {
  id: string;
  workspace_id: string;
  status: "queued" | "running" | "completed" | "failed" | string;
  created_at: string;
  finished_at?: string | null;
  retain_until?: string | null;
  sha256?: string | null;
  size_bytes?: number | null;
  error_code?: string | null;
}

export interface WorkspaceBackupListResponse {
  items: WorkspaceBackupItem[];
  total: number;
  limit: number;
  offset: number;
}
