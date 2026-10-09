/** Types for Knowledge Collections, Documents, Chunks and Ingestion */

export interface CollectionDataProcessingConfig {
  embedding_provider_id?: string;
  embedding_model?: string;
  embedding_dimension?: number;
  ocr_mode?: "single" | "combo";
  primary_ocr_provider_id?: string;
  primary_ocr_model?: string;
  fallback_ocr_provider_id?: string | null;
  fallback_ocr_model?: string | null;
  enable_ocr_rescue?: boolean;
}

export interface KnowledgeCollection {
  data_processing?: CollectionDataProcessingConfig;
  id: string;
  name: string;
  code: string;
  description: string;
  document_count: number;
  chunk_count: number;
  chunking_strategy: "ClauseBasedChunker" | "SemanticChunker";
  ocr_profile: "PyMuPDF" | "Gemini" | "Mistral";
  embedding_model?: string;
  status?: "ready" | "indexing" | "maintenance";
  updated_at: string;
}

export interface KnowledgeDocument {
  id: string;
  collection_id: string;
  collection_name: string;
  title: string;
  filename: string;
  file_size: number;
  page_count: number;
  chunk_count: number;
  status:
    | "completed"
    | "processing"
    | "pending"
    | "review_pending"
    | "failed"
    | "approved"
    | "archived"
    | "ready";
  index_status?: "pending" | "indexing" | "indexed" | "index_failed";
  index_error?: string | null;
  ocr_method: string;
  document_type?: string;
  document_type_code?: string;
  priority_level?: "core" | "high" | "normal";
  version?: string;
  created_at: string;
}

export interface IngestionTask {
  id: string;
  task_name: string;
  collection_id: string;
  collection_code: string;
  source_file: string;
  file_size_mb: number;
  worker_name: string;
  duration_seconds: number;
  category: "ingestion" | "ocr" | "reindex";
  progress_percent: number;
  status: "completed" | "processing" | "failed" | "cancelled";
  created_at: string;
  log_output?: string;
}

export interface DocumentBoundingBox {
  id: string;
  page_number: number;
  type: "text" | "table" | "stamp" | "header" | "title" | "signature" | "list";
  coordinates: { x: number; y: number; width: number; height: number }; // percentages 0-100
  label: string;
  confidence: number;
  content_snippet: string;
}

export interface DocumentRegion {
  id: string;
  page_number: number;
  title: string;
  type:
    | "text"
    | "table"
    | "stamp"
    | "header"
    | "footer"
    | "title"
    | "signature"
    | "list";
  confidence: number;
  reading_order: number;
  details: string;
}

export interface ParsePreviewResult {
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  raw_markdown: string;
  chunk_count: number;
  estimated_tokens: number;
  extracted_tables_count: number;
  ocr_method: string;
  preview_chunks: {
    index: number;
    token_count: number;
    section: string | null;
    preview: string;
  }[];
}

export interface DocumentChunkItem {
  id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  token_count: number;
  section: string | null;
  page_number: number | null;
  metadata: Record<string, unknown>;
}

export interface KnowledgeDocumentDetail extends KnowledgeDocument {
  chunks: DocumentChunkItem[];
  doc_metadata: Record<string, unknown>;
}

export interface ApproveDocumentResult {
  document_id: string;
  status: string;
  total_chunks: number;
  indexed_chunks: number;
}

export interface DocumentVerificationData {
  document_id: string;
  collection_id: string;
  title: string;
  filename: string;
  status?: string;
  index_status?: string;
  file_size_mb: number;
  total_pages: number;
  engine: string;
  total_chars: number;
  estimated_chunks: number;
  pdf_url?: string;
  pages: {
    page_number: number;
    word_count: number;
    line_count: number;
    image_url?: string;
    markdown_content: string;
    raw_text: string;
    bounding_boxes: DocumentBoundingBox[];
    regions: DocumentRegion[];
    dimensions?: {
      width: number;
      height: number;
      orientation?: "portrait" | "landscape";
    };
  }[];
}

export interface FactItem {
  id: string;
  collection_id: string;
  document_id: string;
  entity_name: string;
  entity_type: string;
  attribute_name: string;
  attribute_value: string;
  confidence: number;
  raw_data: Record<string, unknown>;
  created_at: string;
}

export interface FactListResponse {
  collection_id: string;
  total: number;
  facts: FactItem[];
}

export interface FactExcelImportResponse {
  collection_id: string;
  imported_count: number;
  document_id: string;
  message: string;
}

export interface ReindexDocumentResponse {
  document_id: string;
  status: string;
  index_status: "indexed" | "index_failed" | "indexing";
  indexed_chunks: number;
  message: string;
}

export interface KnowledgeReconciliationDiscrepancy {
  type: string;
  document_id?: string | null;
  details: string;
}

export interface KnowledgeReconciliationReport {
  collection_id: string;
  db_documents_count: number;
  indexed_documents_count: number;
  failed_documents_count: number;
  db_chunks_count: number;
  qdrant_points_count: number;
  storage_files_count: number;
  is_consistent: boolean;
  discrepancies: KnowledgeReconciliationDiscrepancy[];
}

export interface ReconcileFixResponse {
  collection_id: string;
  reindexed_documents: string[];
  failed_documents: string[];
  total_reindexed_chunks: number;
  message: string;
}

// ==============================================================================
// Knowledge Publishing V2 Types (ADR-011)
// ==============================================================================

export interface AvailableRepositoryDocumentItem {
  id: string;
  document_code: string;
  title: string;
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  current_revision_id?: string | null;
  current_revision_no?: number | null;
  revision_count: number;
  status: string;
  is_bound: boolean;
  bound_binding_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AvailableRepositoryDocumentsResponse {
  items: AvailableRepositoryDocumentItem[];
  total: number;
}

export interface BindingSelectionItem {
  repository_document_id: string;
  target_revision_id?: string | null;
  chunk_strategy?: string;
  sync_policy?: "manual" | "auto_on_ready";
  auto_activate?: boolean;
}

export interface CreateKnowledgeBindingsRequest {
  items: BindingSelectionItem[];
}

export interface BindingResultItem {
  binding_id?: string | null;
  repository_document_id: string;
  source_revision_id?: string | null;
  status: "created" | "already_bound" | "failed";
  message?: string | null;
  index_revision_id?: string | null;
}

export interface CreateKnowledgeBindingsResponse {
  collection_id: string;
  created_count: number;
  skipped_count: number;
  failed_count: number;
  bindings: BindingResultItem[];
}

export interface KnowledgeBinding {
  id: string;
  collection_id: string;
  repository_document_id: string;
  source_revision_id: string;
  active_index_revision_id?: string | null;
  active_epoch: number;
  chunk_strategy: string;
  sync_policy: string;
  status: "active" | "detached" | "pending";
  document_title?: string | null;
  document_code?: string | null;
  file_name?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ParityReport {
  expected_chunks?: number;
  indexed_points?: number;
  verified_points?: number;
  point_ids_count?: number;
  parity_status: "passed" | "failed" | "pending";
  reason?: string;
  checked_at?: string;
}

export interface KnowledgeIndexRevision {
  id: string;
  binding_id: string;
  source_revision_id: string;
  vector_generation_id: string;
  revision_no: number;
  chunk_count: number;
  fact_count: number;
  point_ids: string[];
  parity_report: ParityReport;
  status:
    | "building"
    | "validating"
    | "ready"
    | "active"
    | "archived"
    | "failed"
    | "pruned";
  failure_code?: string | null;
  failure_detail?: string | null;
  is_rollback_available: boolean;
  storage_state?: "available" | "pruned";
  created_at: string;
  finished_at?: string | null;
}

export interface BuildStagingIndexRequest {
  source_revision_id?: string | null;
  chunk_strategy?: string | null;
  auto_activate?: boolean;
}

export interface IndexActivationRequest {
  to_index_revision_id: string;
  expected_epoch: number;
  reason?: string | null;
}

export interface IndexActivationResponse {
  id: string;
  binding_id: string;
  from_index_revision_id?: string | null;
  to_index_revision_id: string;
  action: string;
  epoch: number;
  reason?: string | null;
  activated_by?: string | null;
  created_at: string;
}

export interface GarbageCollectionRequest {
  keep_revisions?: number;
  dry_run?: boolean;
}

export interface GarbageCollectionReport {
  collection_id: string;
  dry_run: boolean;
  keep_revisions: number;
  total_bindings_scanned: number;
  pruned_revisions_count: number;
  pruned_revision_ids: string[];
  pruned_chunks_count: number;
  pruned_facts_count: number;
  pruned_points_count: number;
  message: string;
  executed_at: string;
}

export interface KnowledgeChunkItem {
  id: string;
  chunk_index: number;
  content: string;
  token_count: number;
  section: string | null;
  page_number: number | null;
  chunk_metadata: Record<string, unknown>;
  index_revision_id: string | null;
}

export interface BindingChunksResponse {
  binding_id: string;
  index_revision_id: string | null;
  total: number;
  page: number;
  page_size: number;
  items: KnowledgeChunkItem[];
}

export interface RollbackIndexRevisionRequest {
  target_index_revision_id: string;
  expected_epoch: number;
  reason?: string;
}

export interface LegacyAuditItem {
  document_id: string;
  document_title: string;
  repository_document_id?: string | null;
  binding_id?: string | null;
  active_index_revision_id?: string | null;
  db_chunks_count: number;
  qdrant_points_count: number;
  classification: "active-parity-ok" | "needs-rebuild" | "pending-intake";
  discrepancy_reason?: string | null;
}

export interface LegacyAuditReport {
  collection_id: string;
  total_documents: number;
  active_parity_ok_count: number;
  needs_rebuild_count: number;
  pending_intake_count: number;
  parity_ratio: number;
  items: LegacyAuditItem[];
  audited_at: string;
}

export interface BackfillRequest {
  force_rebuild?: boolean;
  default_chunk_strategy?: string;
}

export interface BackfillItemResult {
  document_id: string;
  binding_id: string;
  index_revision_id: string;
  chunks_tagged: number;
  facts_tagged: number;
  classification: string;
  status: "created" | "updated" | "skipped" | "failed";
}

export interface BackfillReport {
  collection_id: string;
  documents_processed: number;
  bindings_created: number;
  index_revisions_created: number;
  chunks_tagged: number;
  facts_tagged: number;
  collection_epoch: number;
  status: "completed" | "partial" | "failed";
  items: BackfillItemResult[];
  completed_at: string;
}

export interface ShadowRetrievalRequest {
  query: string;
  top_k?: number;
}

export interface ShadowRetrievalReport {
  collection_id: string;
  query: string;
  v1_result_count: number;
  v2_result_count: number;
  overlap_count: number;
  jaccard_similarity: number;
  latency_v1_ms: number;
  latency_v2_ms: number;
  latency_delta_pct: number;
  retrieval_revision_leak_total: number;
  leak_detected: boolean;
  v1_chunk_ids: string[];
  v2_chunk_ids: string[];
  tested_at: string;
}

export interface GarbageCollectionRequest {
  keep_revisions?: number;
  dry_run?: boolean;
}

export interface GarbageCollectionReport {
  collection_id: string;
  dry_run: boolean;
  keep_revisions: number;
  total_bindings_scanned: number;
  pruned_revisions_count: number;
  pruned_revision_ids: string[];
  pruned_chunks_count: number;
  pruned_facts_count: number;
  pruned_points_count: number;
  message: string;
  executed_at: string;
}

export interface CanaryPolicyResponse {
  collection_id: string;
  read_mode: "system" | "revisioned" | "shadow" | "legacy";
  system_read_mode: string;
  effective_read_mode: string;
  retention_revisions: number;
  last_gc_report?: GarbageCollectionReport | null;
}

export interface UpdateCanaryPolicyRequest {
  read_mode: "system" | "revisioned" | "shadow" | "legacy";
  retention_revisions: number;
}

export interface SystemGarbageCollectionRequest {
  keep_revisions?: number;
  dry_run?: boolean;
}

export interface SystemGarbageCollectionReport {
  total_collections_scanned: number;
  total_bindings_scanned: number;
  total_pruned_revisions_count: number;
  total_pruned_chunks_count: number;
  total_pruned_facts_count: number;
  total_pruned_points_count: number;
  dry_run: boolean;
  reports: GarbageCollectionReport[];
  message: string;
  executed_at: string;
}

export interface SystemDecommissioningAuditReport {
  total_collections: number;
  total_legacy_documents: number;
  total_v2_bindings: number;
  v2_adoption_rate_pct: number;
  collections_in_revisioned_mode: number;
  collections_in_shadow_mode: number;
  collections_in_legacy_mode: number;
  total_prunable_revisions_estimate: number;
  audited_at: string;
}
