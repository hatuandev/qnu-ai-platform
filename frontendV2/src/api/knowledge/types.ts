/**
 * TypeScript types for Knowledge domain (Collections, Folders, Sources, Revisions).
 * Matches backend schemas in `backendV1/qnu/domains/knowledge/`.
 */

import type { PageParams } from "../workspaces/types";

// ==========================================
// Collections
// ==========================================

export type CollectionResponse = {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  source_count: number;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

export type CollectionCreateRequest = {
  name: string;
  description?: string | null;
};

export type CollectionUpdateRequest = {
  name?: string;
  description?: string | null;
};

// ==========================================
// Folders
// ==========================================

export type FolderResponse = {
  id: string;
  workspace_id: string;
  collection_id: string;
  parent_id: string | null;
  name: string;
  source_count: number;
  subfolder_count: number;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type FolderBreadcrumbItem = {
  id: string;
  name: string;
};

export type FolderDetailResponse = FolderResponse & {
  breadcrumbs: FolderBreadcrumbItem[];
};

export type FolderImpactResponse = {
  folder_id: string;
  folder_name: string;
  subfolder_count: number;
  source_count: number;
  descendant_folder_ids: string[];
};

export type FolderCreateRequest = {
  name: string;
  parent_id?: string | null;
};

export type FolderUpdateRequest = {
  name: string;
};

export type FolderMoveRequest = {
  target_parent_id?: string | null;
};

// ==========================================
// Sources & Revisions
// ==========================================

export type ProcessingRunResponse = {
  id: string;
  source_id: string;
  revision_id: string;
  status: "queued" | "running" | "completed" | "failed";
  progress?: number | null;
  error_code?: string | null;
  created_at: string;
  finished_at?: string | null;
};

export type RevisionResponse = {
  id: string;
  source_id: string;
  revision_no: number;
  file_name: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  created_by: string;
  created_at: string;
};

export type SourceResponse = {
  id: string;
  workspace_id: string;
  collection_id: string;
  folder_id: string | null;
  title: string;
  status: string;
  revision_count: number;
  current_revision_no: number;
  serving_revision_no: number;
  file_name: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  processing?: ProcessingRunResponse | null;
};

export type SourceUploadResponse = {
  source: SourceResponse;
  revision: RevisionResponse;
};

export type SourceMoveRequest = {
  target_folder_id: string | null;
};

export type SourceRenameRequest = {
  title: string;
};

export type SourceListParams = PageParams & {
  folderId?: string | null;
  allFolders?: boolean;
};

// ==========================================
// Source Summary & Serving
// ==========================================

export type SourceServingState = {
  served_revision_no?: number | null;
  preparing_revision_no?: number | null;
  published_revision_no?: number | null;
  served_version_id?: string | null;
  served_document_id?: string | null;
};

export type SourceActionPermissions = {
  can_stop: boolean;
  can_withdraw: boolean;
  can_update: boolean;
  can_delete: boolean;
};

export type SourcePreparationSummary = {
  intent_id: string;
  status: string;
  step: string;
  error_code?: string | null;
};

export type SourceVersionRef = {
  version_id: string;
  version_no: number;
  state_version: number;
  status: string;
  bundle_sha256: string;
  document_id: string;
  document_title: string;
};

export type SourceDerivation = {
  compilation_run_id: string;
  compilation_generation: number;
  compilation_status: string;
  origin: string;
  ocr_run_id: string;
  ocr_generation: number;
  version?: SourceVersionRef | null;
  readiness?: {
    status: string;
    missing_items?: string[];
  } | null;
  is_serving: boolean;
};

export type SourceSummaryResponse = {
  capabilities: {
    can_prepare: boolean;
    can_register: boolean;
    can_approve: boolean;
    can_publish: boolean;
  };
  observed_at: string;
  source_id: string;
  title: string;
  latest_revision_no: number;
  serving_revision_no: number;
  revision: RevisionResponse;
  processing_runs: ProcessingRunResponse[];
  runs_truncated: boolean;
  active_run_id: string | null;
  derivations: SourceDerivation[];
  derivations_truncated: boolean;
  serving: SourceServingState;
  actions: SourceActionPermissions;
  preparation?: SourcePreparationSummary | null;
};
