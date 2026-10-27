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
}

export interface RevisionUploadInput {
  file: File;
  staged?: boolean;
}
