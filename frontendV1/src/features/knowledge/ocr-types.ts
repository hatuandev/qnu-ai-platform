/**
 * Types and interfaces for backendV1 OCR processing runs and post-OCR text review.
 */

export type ProcessingRunStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "uncertain"
  | "cancelled";

export type PageStatus =
  | "pending"
  | "in_flight"
  | "completed"
  | "blank"
  | "failed"
  | "uncertain";

export interface ProcessingRunRequest {
  provider_id?: string | null;
  force?: boolean;
  strategy?: "auto" | "native" | "ocr";
}

export interface ProcessingRunResponse {
  id: string;
  workspace_id: string;
  collection_id: string;
  source_id: string;
  revision_id: string;
  revision_no: number;
  generation: number;
  status: ProcessingRunStatus;
  provider_id: string | null;
  pages_total: number | null;
  pages_done: number;
  pages_failed: number;
  attempt_count: number;
  max_attempts: number;
  error_code: string | null;
  error_detail: string | null;
  requested_by: string;
  requested_at: string;
  dispatched_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  usage_tokens: number | null;
  config_fingerprint: string;
  dispatch_pending: boolean;
  strategy?: string;
  results_ready?: boolean;
}

export interface ProcessingRunCreatedResponse {
  run: ProcessingRunResponse;
  created: boolean;
  dispatched: boolean;
}

export interface PageStatusResponse {
  page_number: number;
  status: PageStatus;
  used_ocr?: boolean;
  image_sha256: string | null;
  blocks_count: number;
  has_tables: boolean;
  error_code: string | null;
  usage_tokens: number | null;
}

export interface ProcessingRunDetailResponse extends ProcessingRunResponse {
  pages: PageStatusResponse[];
}

export interface ProcessingRunPageMeta {
  page: number;
  page_size: number;
  total: number;
}

export interface ProcessingRunListResponse {
  items: ProcessingRunResponse[];
  meta: ProcessingRunPageMeta;
}

export interface EvidenceSnapshotResponse {
  run_id: string;
  generation: number;
  status: string;
  identity: Record<string, unknown>;
  processing: Record<string, unknown>;
  canonical_sha256: string;
  manifest_sha256: string | null;
  checks: Record<string, unknown>;
  validation: Record<string, unknown>;
  artifacts: Array<Record<string, unknown>>;
  pages: Array<Record<string, unknown>>;
  evidence: Record<string, unknown>;
}

export interface TextUnit {
  evidence_id: string;
  page: number;
  kind: string;
  text: string;
  original_text: string;
  bbox: Record<string, unknown>;
  row: number | null;
  column: number | null;
}

export interface ReviewDocument {
  run_id: string;
  version: number;
  version_id: string | null;
  canonical_sha256: string;
  original_sha256: string;
  markdown_sha256: string;
  units: TextUnit[];
  saved_at: string | null;
}

export interface TextChange {
  evidence_id: string;
  before: string;
  after: string;
}

export interface SaveReviewInput {
  expected_version: number;
  expected_sha256: string;
  changes: TextChange[];
}

export interface DetectRequestInput {
  source_version?: number | null;
  expected_version: number;
  expected_sha256: string;
  evidence_ids: string[];
  provider_id?: string | null;
  max_output_tokens?: number;
}

export interface Suggestion {
  evidence_id: string;
  start: number;
  end: number;
  original: string;
  replacement: string;
  reason: string;
  context_before?: string | null;
  context_after?: string | null;
  review_reason?: string | null;
}

export interface DetectionResponse {
  id: string;
  status: string;
  version: number;
  canonical_sha256: string;
  suggestions: Suggestion[];
  withheld_suggestions?: Suggestion[];
  checked_evidence_ids: string[];
  error_code: string | null;
  usage_id: string | null;
  created_at: string;
}
