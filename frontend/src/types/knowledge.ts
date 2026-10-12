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
  ocr_profile: "auto" | "PyMuPDF" | "PaddleOCR" | "Gemini" | "Mistral";
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
  coordinates: {
    x?: number;
    y?: number;
    left?: number;
    top?: number;
    width: number;
    height: number;
    coordinate_system?: string;
    is_valid?: boolean;
  };
  label: string;
  confidence: number;
  content_snippet: string;
}

export interface DocumentRegion {
  layout_confidence?: number | null;
  text_confidence?: number | null;
  coordinates?: DocumentBoundingBox["coordinates"];
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
  citation_metadata?: Record<string, string | null>;
  source_metadata?: Record<string, unknown>;
  structured_artifact?: SourceArtifact;
  layout_text_alignment?: string;
  revision_id?: string;
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
  document_id: string | null;
  binding_id?: string | null;
  index_revision_id?: string | null;
  entity_name: string;
  entity_type: string;
  attribute_name: string;
  attribute_value: string;
  confidence: number;
  raw_data: Record<string, unknown>;
  created_at: string;
}

export interface SourceArtifact {
  temporal_metadata?: {
    issued_date: {
      value: string | null;
      status: string;
      precision: string | null;
    };
    issued_year: { value: number | null; status: string };
    subject_years: { values: number[]; status: string };
    filename_years: { values: number[]; status: string };
  };
  version: string;
  content_hash: string;
  fact_set_hash: string;
  metadata: Record<string, string | null>;
  facts: Pick<
    FactItem,
    | "id"
    | "entity_name"
    | "entity_type"
    | "attribute_name"
    | "attribute_value"
    | "confidence"
    | "raw_data"
  >[];
  tables: {
    id: string;
    page_number: number | null;
    headers: string[];
    rows: string[][];
  }[];
  issues: { code: string; table_id?: string; row_index?: number }[];
  review: { status: string };
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
  repository_document_id: string | null;
  source_revision_id: string | null;
  active_index_revision_id?: string | null;
  active_source_revision_id?: string | null;
  source_status?: string | null;
  active_epoch: number;
  chunk_strategy: string;
  sync_policy: string;
  status: "active" | "detached" | "pending" | "paused";
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
  source_revision_id: string | null;
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

export interface AttachDocumentGroupRequest {
  group_id: string;
  chunk_strategy?: string;
  sync_policy?: string;
  auto_activate?: boolean;
  strict_ready?: boolean;
}

export interface AttachDocumentGroupItemResult {
  document_id: string;
  document_title?: string | null;
  source_revision_id?: string | null;
  binding_id?: string | null;
  status: "created" | "already_bound" | "not_ready" | "failed";
  message?: string | null;
  index_revision_id?: string | null;
}

export interface AttachDocumentGroupResponse {
  collection_id: string;
  group_id: string;
  group_name: string;
  total_documents: number;
  created_count: number;
  already_bound_count: number;
  not_ready_count: number;
  failed_count: number;
  items: AttachDocumentGroupItemResult[];
}

export interface PreviewDocumentGroupRequest {
  group_id: string;
}

export interface PreviewDocumentGroupItem {
  document_id: string;
  title: string;
  file_name: string;
  current_revision_id?: string | null;
  revision_status?: string | null;
  already_bound: boolean;
  eligible_for_binding: boolean;
  reason?: string;
}

export interface PreviewDocumentGroupResponse {
  collection_id: string;
  group_id: string;
  group_name: string;
  total_documents: number;
  ready_count: number;
  already_bound_count: number;
  not_ready_count: number;
  failed_count: number;
  items: PreviewDocumentGroupItem[];
}

export interface DocumentSyncItemResult {
  document_id: string;
  binding_id?: string | null;
  source_revision_id?: string | null;
  staging_revision_id?: string | null;
  status: "success" | "failed" | "skipped";
  error_code?: string | null;
  error_message?: string | null;
}

export interface KnowledgeGroupSource {
  id: string;
  collection_id: string;
  document_group_id: string;
  group_name: string;
  group_description?: string | null;
  sync_policy: string;
  chunk_strategy: string;
  status:
    | "pending"
    | "empty"
    | "up_to_date"
    | "updates_available"
    | "syncing"
    | "review_required"
    | "ready"
    | "failed"
    | "detached";
  last_synced_at?: string | null;
  last_membership_hash?: string | null;
  total_documents: number;
  published_count: number;
  new_revision_count: number;
  new_document_count: number;
  not_ready_count: number;
  failed_count: number;
  needs_build_count?: number;
  awaiting_publish_count?: number;
  publishable_count?: number;
  has_updates: boolean;
  items?: DocumentSyncItemResult[];
  created_at: string;
  updated_at: string;
}

export interface AttachGroupSourceRequest {
  group_id: string;
  chunk_strategy?: string;
  sync_policy?: "manual" | "auto_on_ready";
  auto_activate?: boolean;
}

export interface PreviewGroupSourceDiffItem {
  document_id: string;
  title: string;
  file_name: string;
  revision_id?: string | null;
  revision_status?: string | null;
  category:
    | "added"
    | "updated"
    | "removed"
    | "unchanged"
    | "not_ready"
    | "failed";
  reason?: string;
}

export interface PreviewGroupSourceDiffResponse {
  source_id?: string | null;
  collection_id: string;
  group_id: string;
  group_name: string;
  membership_hash: string;
  last_membership_hash?: string | null;
  has_changes: boolean;
  total_documents_in_group: number;
  added_count: number;
  updated_count: number;
  removed_count: number;
  unchanged_count: number;
  not_ready_count: number;
  failed_count: number;
  needs_build_count?: number;
  awaiting_publish_count?: number;
  publishable_count?: number;
  items: PreviewGroupSourceDiffItem[];
}

export interface SyncGroupSourceRequest {
  confirm_detach_removed?: boolean;
  chunk_strategy?: string;
  auto_publish?: boolean;
}

export interface SyncGroupSourceResponse {
  source_id: string;
  collection_id: string;
  status: string;
  synced_count: number;
  detached_count: number;
  failed_count: number;
  review_required_count: number;
  published_count: number;
  new_membership_hash?: string | null;
  message: string;
  items?: DocumentSyncItemResult[];
}

export interface PublishGroupSourceResponse {
  source_id: string;
  collection_id: string;
  status: string;
  published_count: number;
  failed_count?: number;
  message: string;
  items?: DocumentSyncItemResult[];
}

export interface DetachGroupSourceResponse {
  source_id: string;
  collection_id: string;
  status: string;
  detached_bindings_count: number;
  message: string;
}

export interface CollectionSummaryMetrics {
  collection_id: string;
  total_sources: number;
  published_documents_count: number;
  documents_needing_sync_count: number;
  active_chunks_count: number;
  collection_status:
    | "empty"
    | "pending"
    | "syncing"
    | "review_required"
    | "updates_available"
    | "ready"
    | "failed";
  configured_embedding_model?: string | null;
  default_chunk_strategy?: string | null;
}

// ==============================================================================
// V3 Types: Candidate Groups & Documents (ADR-012)
// ==============================================================================

export interface CandidateGroupItem {
  id: string;
  name: string;
  description: string | null;
  total_documents: number;
  imported_documents: number;
  created_at: string | null;
}

export interface CandidateGroupListResponse {
  items: CandidateGroupItem[];
  total: number;
}

export interface RepositoryCandidateItem {
  document_id: string;
  title: string;
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  file_hash: string;
  document_type_code?: string | null;
  document_number?: string | null;
  issuing_authority?: string | null;
  issued_date?: string | null;
  groups: Array<{
    id: string;
    name: string;
    description?: string | null;
  }>;
  source_state:
    | "not_imported"
    | "current"
    | "update_available"
    | "processing"
    | "failed";
  vector_state: "not_indexed" | "indexed" | "indexing" | "index_failed";
  knowledge_source_id?: string | null;
  imported_file_hash?: string | null;
  selectable: boolean;
  unselectable_reason?: string | null;
}

export interface CandidateListResponse {
  items: RepositoryCandidateItem[];
  total: number;
  vector_generation_id?: string | null;
}

// ==============================================================================
// V3 Types: Snapshot Import Batches (ADR-012)
// ==============================================================================

export interface KnowledgeImportBatchCreateRequest {
  document_ids: string[];
  vector_generation_id?: string | null;
  parser_profile?: string;
  chunk_strategy?: string;
  chunk_config?: Record<string, unknown>;
}

export interface KnowledgeImportItemResponse {
  progress?: number;
  progress_phase?: string | null;
  progress_kind?: "milestone";
  id: string;
  batch_id: string;
  origin_document_id: string;
  origin_title: string;
  origin_file_name: string;
  origin_file_type: string;
  origin_file_hash: string;
  knowledge_binding_id?: string | null;
  knowledge_source_revision_id?: string | null;
  index_revision_id?: string | null;
  phase: string;
  status:
    | "queued"
    | "processing"
    | "succeeded"
    | "failed"
    | "skipped"
    | "review_required";
  failure_code?: string | null;
  failure_detail?: string | null;
  retry_count: number;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeImportBatchResponse {
  id: string;
  collection_id: string;
  vector_generation_id?: string | null;
  parser_profile: string;
  chunk_strategy: string;
  total_count: number;
  queued_count: number;
  processing_count: number;
  review_required_count: number;
  succeeded_count: number;
  failed_count: number;
  skipped_count: number;
  status:
    | "queued"
    | "processing"
    | "review_required"
    | "completed"
    | "partial_failed"
    | "failed"
    | "cancelled";
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  items: KnowledgeImportItemResponse[];
}

// ==============================================================================
// V3 Types: Knowledge Sources & Revisions (ADR-012)
// ==============================================================================

export interface KnowledgeSourceRevisionResponse {
  id: string;
  binding_id: string;
  revision_no: number;
  origin_document_id: string;
  origin_file_hash: string;
  canonical_hash?: string | null;
  canonical_markdown?: string | null;
  page_manifest: Array<Record<string, unknown>>;
  citation_metadata: Record<string, unknown>;
  quality_report: {
    passed?: boolean;
    quality_score?: number;
    metrics?: Record<string, unknown>;
    violations?: Array<{
      rule_name: string;
      level: "warning" | "error";
      description: string;
      snippet?: string;
    }>;
    [key: string]: unknown;
  };
  status:
    | "queued"
    | "extracting"
    | "normalizing"
    | "validating"
    | "review_required"
    | "ready"
    | "failed"
    | "cancelled";
  failure_code?: string | null;
  failure_detail?: string | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeSourceDetailResponse {
  id: string;
  collection_id: string;
  repository_document_id: string | null;
  status: string;
  active_source_revision_id?: string | null;
  active_source_revision?: KnowledgeSourceRevisionResponse | null;
  revisions: KnowledgeSourceRevisionResponse[];
  created_at: string;
  updated_at: string;
}

export interface UpdateSourceContentRequest {
  canonical_markdown: string;
}

export interface SourceContextEditRequest {
  expected_fact_set_hash: string;
  reason: string;
  issued_date?: string | null;
  issued_year?: number | null;
  subject_years?: number[];
  facts?: {
    fact_id: string;
    year?: number | null;
    method?: string | null;
    unit?: string | null;
  }[];
}

export interface ReviewSourceRevisionRequest {
  decision: "approved" | "rejected";
  comment?: string;
}

// ==============================================================================
// V3 Types: Chunk Sets & Multi-Vector Generations (ADR-012)
// ==============================================================================

export interface KnowledgeChunkSetResponse {
  id: string;
  source_revision_id: string;
  chunk_strategy: string;
  chunk_config: Record<string, unknown>;
  config_hash: string;
  chunk_count: number;
  fact_count: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface CreateVectorGenerationRequest {
  embedding_model: string;
  provider_id?: string;
  embedding_dimension?: number;
}

export interface KnowledgeVectorGenerationResponse {
  id: string;
  collection_id: string;
  embedding_model: string;
  provider_id: string;
  embedding_dimension: number;
  distance_metric: string;
  generation_epoch: number;
  status: "building" | "ready" | "active" | "retired";
  config_hash: string;
  created_at: string;
}

export interface ActivateVectorGenerationResponse {
  collection_id: string;
  activated_generation_id: string;
  previous_generation_id?: string | null;
  new_epoch: number;
  status: string;
}

export interface BuildVectorGenerationRequest {
  chunk_strategy?: string;
  chunk_config?: Record<string, unknown>;
}

export interface VectorLoadItem {
  binding_id: string;
  source_revision_id: string;
}

export interface VectorLoadJob {
  id: string;
  status: string;
  progress: number;
  error?: string | null;
  payload: {
    binding_id?: string;
    generation_id?: string;
    source_revision_id?: string;
  };
}

export interface VectorSourceIndexStatus {
  id: string;
  binding_id: string;
  source_revision_v2_id?: string | null;
  vector_generation_id: string;
  chunk_count: number;
  status: string;
  failure_detail?: string | null;
}

export interface VectorLoadState {
  jobs: VectorLoadJob[];
  indexes: VectorSourceIndexStatus[];
}

export interface BuildVectorGenerationResponse {
  collection_id: string;
  generation_id: string;
  total_sources: number;
  built_count: number;
  reused_count: number;
  failed_count: number;
  status: string;
}
