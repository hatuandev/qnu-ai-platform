import type { Page } from "../workspaces/types";

/**
 * TypeScript types for Publication, Compiled Documents, and Review Gates.
 * Mirrors `backendV1/qnu/domains/knowledge/publication/schemas.py`.
 */

export type DocumentResponse = {
  id: string;
  workspace_id: string;
  collection_id: string;
  document_key: string;
  title: string;
  change_sequence: number;
  created_by: string;
  created_at: string;
};

export type VersionResponse = {
  id: string;
  document_id: string;
  version_no: number;
  state_version: number;
  status: "draft" | "approved" | "published" | "superseded" | "withdrawn";
  bundle_sha256: string;
  compilation_run_id: string;
  retrieval_metadata_sha256: string;
  created_by: string;
  created_at: string;
};

export type RegistrationResponse = {
  document: DocumentResponse;
  version: VersionResponse;
};

export type CreateDocumentRequest = {
  document_key: string;
  title: string;
  compilation_run_id: string;
};

export type RegisterVersionRequest = {
  compilation_run_id: string;
};

export type ReviewFinding = {
  finding_id: string;
  finding: {
    explanation?: string;
    suggested_action?: string;
    [key: string]: unknown;
  };
};

export type ReviewGateResponse = {
  review_id: string;
  report_sha256: string;
  bundle_sha256: string;
  verdict: "passed" | "flagged" | "failed";
  findings: ReviewFinding[];
};

export type DecisionFindingResolution = {
  finding_id: string;
  decision: "accepted_risk" | "not_an_issue";
  reason: string;
};

export type ReviewAck = {
  review_id: string;
  report_sha256: string;
  confirmed_reviewed: boolean;
  resolutions: DecisionFindingResolution[];
  retrieval_metadata_sha256?: string;
};

export type ReviewSkip = {
  confirmed_skip: boolean;
  version_id: string;
  bundle_sha256: string;
  retrieval_metadata_sha256?: string;
};

export type DecisionPreviewRequest = {
  action: "approve" | "publish" | "withdraw";
  reason: string;
  review_ack?: ReviewAck;
  review_skip?: ReviewSkip;
};

export type DecisionPreviewResponse = {
  id: string;
  action: "approve" | "publish" | "withdraw";
  version_id: string;
  preview_sha256: string;
  expires_at: string;
};

export type DecisionCommitRequest = {
  preview_id: string;
  preview_sha256: string;
};

export type DecisionResponse = {
  id: string;
  action: string;
  version_id: string;
  status: string;
  created_at: string;
};

export type DocumentReadiness = {
  status: "ready" | "not_indexed" | "outdated" | "unavailable";
  reason?: string | null;
};

export type DocumentSummaryResponse = {
  observed_at: string;
  document: DocumentResponse;
  prepared_version: VersionResponse | null;
  published_version: VersionResponse | null;
  served_version: VersionResponse | null;
  readiness: DocumentReadiness;
  serving_matches_published: boolean;
  versions: Page<VersionResponse>;
  capabilities: {
    can_prepare: boolean;
    can_register: boolean;
    can_approve: boolean;
    can_publish: boolean;
  };
};
