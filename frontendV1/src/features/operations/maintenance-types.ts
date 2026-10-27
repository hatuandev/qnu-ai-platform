export type Backup = {
  id: string;
  workspace_id: string;
  status: string;
  created_at: string;
  finished_at: string | null;
  retain_until: string | null;
  sha256: string | null;
  size_bytes: number | null;
  error_code: string | null;
};
export type BackupPage = {
  items: Backup[];
  total: number;
  limit: number;
  offset: number;
};
export type Retention = {
  original_and_raw_evidence: string;
  backup_default: string;
  automatic_delete: boolean;
  eligible_backup_ids: string[];
  requires_preview_and_acceptance: boolean;
};
export type BackupVerification = {
  verified: boolean;
  workspace_id: string;
  objects: number;
  snapshot_sha256: string;
  snapshot_tables: Record<string, number>;
  database_restore_supported: false;
};
export type CleanupAction = {
  id: string;
  status: string;
  preview_sha256: string;
  expires_at: string;
  files: { id: string; bytes: number; modified_at: string }[];
  total_bytes: number;
  result: {
    files: { id: string; outcome: string }[];
    originals_and_raw_retained: boolean;
  } | null;
};
