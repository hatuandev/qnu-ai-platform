/** Types for Central Document Repository (Kho Tài Liệu Tập Trung) */

export interface AttachedCollectionInfo {
  collection_id: string;
  collection_name: string;
  document_id: string;
  index_status: string;
  created_at: string;
}

export interface DocumentGroupMinimalItem {
  id: string;
  name: string;
}

export interface RepositoryDocumentListItem {
  id: string;
  title: string;
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  file_hash: string;
  current_revision_id?: string | null;
  document_type_code?: string | null;
  document_type_name?: string | null;
  document_number?: string | null;
  issuing_authority?: string | null;
  issued_date?: string | null;
  effective_date?: string | null;
  signer?: string | null;
  parse_status: "pending" | "parsing" | "parsed" | "failed";
  ocr_engine?: string | null;
  attached_collections_count: number;
  groups?: DocumentGroupMinimalItem[];
  created_at: string;
  updated_at: string;
}

export interface RepositoryDocument extends RepositoryDocumentListItem {
  storage_path: string;
  parsed_markdown?: string | null;
  doc_metadata: {
    page_count?: number;
    table_count?: number;
    preview_pages?: string[];
    sections_count?: number;
    parse_error?: string | null;
    [key: string]: unknown;
  };
  is_active: boolean;
  attached_collections: AttachedCollectionInfo[];
}

export interface DocumentStats {
  total_documents: number;
  parsed_documents: number;
  pending_documents: number;
  failed_documents: number;
  total_size_bytes: number;
  document_types_count: number;
  attached_usages_count: number;
}

export interface RepositoryDocumentFilter {
  search?: string;
  document_type_code?: string;
  file_type?: string;
  parse_status?: string;
  group_id?: string;
  exclude_group_id?: string;
  skip?: number;
  limit?: number;
}

export interface DocumentGroup {
  id: string;
  tenant_id: string;
  workspace_id: string;
  name: string;
  description?: string | null;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
  lock_version: number;
  total_documents: number;
  ready_documents: number;
  processing_documents: number;
  error_documents: number;
}

export type DocumentGroupListItem = DocumentGroup;

export interface DocumentGroupListResponse {
  items: DocumentGroupListItem[];
  total: number;
}

export interface DocumentGroupCreateRequest {
  name: string;
  description?: string;
}

export interface DocumentGroupUpdateRequest {
  name?: string;
  description?: string;
  expected_lock_version?: number;
}

export interface AddGroupDocumentsRequest {
  document_ids: string[];
}

export interface AddGroupDocumentsResultItem {
  document_id: string;
  status: "added" | "skipped_existing" | "failed";
  message?: string | null;
}

export interface AddGroupDocumentsResponse {
  group_id: string;
  added_count: number;
  skipped_existing_count: number;
  failed_count: number;
  items: AddGroupDocumentsResultItem[];
}

export interface GroupDocumentItem {
  id: string;
  title: string;
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  file_hash: string;
  document_type_code?: string | null;
  document_number?: string | null;
  issuing_authority?: string | null;
  issued_date?: string | null;
  parse_status: string;
  current_revision_id?: string | null;
  latest_revision_no: number;
  revision_status?: string | null;
  added_at: string;
  added_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface GroupDocumentsResponse {
  group_id: string;
  items: GroupDocumentItem[];
  total: number;
}

export interface RepositoryDocumentUpdate {
  title?: string;
  document_type_code?: string;
  document_number?: string;
  issuing_authority?: string;
  issued_date?: string;
  effective_date?: string;
  doc_metadata?: Record<string, unknown>;
}

export interface AttachDocumentsRequest {
  document_ids: string[];
  chunk_strategy?: string;
  auto_approve?: boolean;
}

export interface QualityReportCheck {
  passed: boolean;
  detail: string;
  score?: number;
}

export interface QualityReport {
  overall_status: "passed" | "warning" | "failed";
  overall_score?: number;
  text_density?: number;
  table_count?: number;
  mojibake_clean?: boolean;
  checks?: Record<string, QualityReportCheck>;
  [key: string]: unknown;
}

export interface DocumentRevisionListItem {
  id: string;
  document_id: string;
  revision_no: number;
  based_on_revision_id?: string | null;
  source_file_name: string;
  source_file_type: string;
  source_size_bytes: number;
  source_hash: string;
  canonical_hash?: string | null;
  status:
    | "queued"
    | "processing"
    | "validating"
    | "review_required"
    | "ready"
    | "failed"
    | "cancelled";
  failure_code?: string | null;
  failure_detail?: string | null;
  quality_report?: QualityReport | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentRevision extends DocumentRevisionListItem {
  source_storage_path: string;
  canonical_markdown?: string | null;
  page_manifest?: Array<Record<string, unknown>> | null;
  citation_metadata?: Record<string, unknown> | null;
  parse_provenance?: Record<string, unknown> | null;
  idempotency_key?: string | null;
  lock_version: number;
  review_notes?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  created_by?: string | null;
}

export interface AsyncUploadDocumentResponse {
  message: string;
  document_id: string;
  revision_id: string;
  status: string;
  job_id?: string | null;
  deduplicated?: boolean;
}
