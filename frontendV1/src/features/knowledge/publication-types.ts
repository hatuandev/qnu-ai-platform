import type { RetrievalAnnotation } from "../rag/types";
import type { ReviewFinding } from "./compilation-types";

/**
 * Types and contracts for compiled document versions, review gate, and publication lifecycle.
 * Corresponds to backendV1/qnu/domains/knowledge/publication/schemas.py
 */

export type CompiledDocumentStatus =
  | "draft"
  | "approved"
  | "published"
  | "superseded"
  | "withdrawn";

export type DecisionAction = "approve" | "publish" | "withdraw";

export interface DocumentResponse {
  id: string;
  workspace_id: string;
  collection_id: string;
  document_key: string;
  title: string;
  change_sequence: number;
  created_by: string;
  created_at: string;
}

export interface VersionResponse {
  id: string;
  document_id: string;
  workspace_id: string;
  collection_id: string;
  compilation_run_id: string;
  version_no: number;
  status: CompiledDocumentStatus;
  state_version: number;
  input_sha256: string;
  draft_sha256: string;
  markdown_sha256: string;
  bundle_sha256: string;
  provenance: Record<string, unknown>;
  /** Human-declared metadata bound to this exact version (Context673). */
  retrieval_metadata: RetrievalAnnotation[];
  /**
   * SHA-256 of `retrieval_metadata`, computed by the backend. The reviewer sends
   * it back verbatim in `review_ack`; it is never typed or recomputed in the UI.
   */
  retrieval_metadata_sha256: string;
  created_by: string;
  created_at: string;
}

export interface RegistrationResponse {
  document: DocumentResponse;
  version: VersionResponse;
  created: boolean;
}

export interface FindingResolutionInput {
  finding_id: string;
  decision: "accepted_risk" | "not_an_issue";
  reason: string;
}

export interface ReviewAckInput {
  review_id: string;
  report_sha256: string;
  confirmed_reviewed: true;
  resolutions: FindingResolutionInput[];
  /**
   * Exact `retrieval_metadata_sha256` returned by the backend for this version.
   * Required whenever the version carries metadata; omitted otherwise.
   */
  retrieval_metadata_sha256?: string;
}

export interface ReviewGateFinding {
  finding_id: string;
  finding: ReviewFinding;
}

export interface ReviewGateResponse {
  review_id: string;
  report_sha256: string;
  bundle_sha256: string;
  verdict: "needs_attention" | "no_issues_detected" | null;
  findings: ReviewGateFinding[];
}

export interface CreateDocumentRequest {
  document_key: string;
  title: string;
  compilation_run_id: string;
  retrieval_metadata?: RetrievalAnnotation[];
}

export interface RegisterVersionRequest {
  compilation_run_id: string;
  retrieval_metadata?: RetrievalAnnotation[];
}

export interface DecisionPreviewRequest {
  action: DecisionAction;
  reason: string;
  review_ack?: ReviewAckInput | null;
}

export interface DecisionPreviewResponse {
  id: string;
  version_id: string;
  document_id: string;
  actor_ref: string;
  action: DecisionAction;
  reason: string;
  expected_document_sequence: number;
  expected_version_sequence: number;
  expected_active_version_id: string | null;
  bundle_sha256: string;
  preview_sha256: string;
  expires_at: string;
  review_ack?: Record<string, unknown> | null;
}

export interface DecisionCommitRequest {
  preview_id: string;
  preview_sha256: string;
}

export interface DecisionResponse {
  id: string;
  preview_id: string;
  version_id: string;
  document_id: string;
  actor_ref: string;
  action: DecisionAction;
  reason: string;
  document_sequence: number;
  bundle_sha256: string;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
  created_at: string;
}

export interface PublishedResponse {
  document: DocumentResponse;
  version: VersionResponse;
  decision: DecisionResponse;
  content: Record<string, unknown>;
}
