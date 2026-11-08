/**
 * Wire contract for the review handoff.
 *
 * Mirrors `backendV1/qnu/domains/knowledge/review/schemas.py`. A submission
 * pins one immutable version and bundle hash; the publication status enum is
 * never reused here.
 */

export type SubmissionPreviewAction = "submit" | "request_changes" | "cancel";

export type SubmissionStatus =
  | "pending"
  | "changes_requested"
  | "resolved"
  | "cancelled";

export type SubmissionPreviewRequest = {
  document_id: string;
  version_id: string;
  submission_id?: string;
  action: SubmissionPreviewAction;
  reason: string;
};

export type SubmissionPreviewResponse = {
  id: string;
  workspace_id: string;
  collection_id: string;
  document_id: string;
  version_id: string;
  submission_id: string | null;
  actor_ref: string;
  action: SubmissionPreviewAction;
  reason: string;
  expected_document_sequence: number;
  expected_version_sequence: number;
  expected_submission_status: string | null;
  expected_submission_sequence: number | null;
  bundle_sha256: string;
  preview_sha256: string;
  expires_at: string;
};

export type SubmissionCommitRequest = {
  preview_id: string;
  preview_sha256: string;
};

export type SubmissionResponse = {
  id: string;
  workspace_id: string;
  collection_id: string;
  document_id: string;
  document_title: string;
  version_id: string;
  version_no: number;
  bundle_sha256: string;
  status: SubmissionStatus;
  state_version: number;
  note: string;
  submitted_by: string;
  submitted_at: string;
  document_sequence: number;
  closed_by: string | null;
  closed_at: string | null;
  close_reason: string | null;
  is_open: boolean;
};

export type SubmissionOutcome = {
  submission: SubmissionResponse;
  action: string;
  created: boolean;
};

export type SubmissionListParams = {
  status?: SubmissionStatus;
  document_id?: string;
  version_id?: string;
  page: number;
  pageSize: number;
};
