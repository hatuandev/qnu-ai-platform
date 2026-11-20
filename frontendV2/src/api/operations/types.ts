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
