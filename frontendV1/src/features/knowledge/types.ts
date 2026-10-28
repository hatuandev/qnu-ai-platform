/**
 * TypeScript types for Knowledge domain (Collections, Sources, Revisions).
 * Matches backend schemas in backendV1/qnu/domains/knowledge.
 */

export interface KBCollection {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  source_count: number;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface KBSource {
  id: string;
  workspace_id: string;
  collection_id: string;
  folder_id?: string | null;
  title: string;
  status: string;
  revision_count: number;
  current_revision_no: number;
  /** Missing on older responses stays unknown; never infer from latest. */
  serving_revision_no?: number;
  file_name: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface KBFolder {
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
}

export interface FolderBreadcrumbItem {
  id: string;
  name: string;
}

export interface KBFolderDetail extends KBFolder {
  breadcrumbs: FolderBreadcrumbItem[];
}

export interface FolderImpact {
  folder_id: string;
  folder_name: string;
  subfolder_count: number;
  source_count: number;
  descendant_folder_ids: string[];
}

export interface FolderCreateInput {
  name: string;
  parent_id?: string | null;
}

export interface FolderUpdateInput {
  name: string;
}

export interface FolderMoveInput {
  target_parent_id?: string | null;
}

export interface SourceMoveInput {
  target_folder_id?: string | null;
}

export interface SourceRenameInput {
  title: string;
}

export interface SourceListParams extends PageParams {
  folderId?: string | null;
  allFolders?: boolean;
}

export interface KBRevision {
  id: string;
  source_id: string;
  revision_no: number;
  file_name: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  created_by: string;
  created_at: string;
}

export interface SourceUploadResult {
  source: KBSource;
  revision: KBRevision;
}

export interface PageMeta {
  page: number;
  page_size: number;
  total: number;
}

export interface PageResponse<T> {
  items: T[];
  meta: PageMeta;
}

export interface PageParams {
  page?: number;
  pageSize?: number;
}

export interface CollectionCreateInput {
  name: string;
  description?: string | null;
}

export interface CollectionUpdateInput {
  name?: string;
  description?: string | null;
}

export interface SourceUploadInput {
  file: File;
  title?: string;
  folder_id?: string | null;
}

export interface RevisionUploadInput {
  file: File;
  staged?: boolean;
}
