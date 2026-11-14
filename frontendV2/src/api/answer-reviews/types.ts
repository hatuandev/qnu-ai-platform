/**
 * TypeScript types for assistant answer reviews.
 * Mirrors `backendV1/qnu/domains/answer_review/schemas.py` and the
 * `AnswerResponse` contract the reviews embed.
 */

export type AnswerStatus = "answered" | "insufficient_evidence";

export type AnswerReason =
  | "no_eligible_content"
  | "no_match"
  | "model_abstained"
  | "answer_not_supported"
  | "answer_verification_uncertain";

export type AnswerStatement = {
  text: string;
  evidence_ids: string[];
};

export type AnswerSourcePassage = {
  text: string;
  [key: string]: string;
};

export type AnswerSource = {
  chunk_id: string;
  document_id: string;
  version_id: string;
  publication_decision_id: string;
  score: number;
  kind: string;
  text: string;
  citations: Record<string, unknown>;
  structure: Record<string, unknown> | null;
  evidence_id: string;
  source_passages: AnswerSourcePassage[];
};

export type AnswerVerificationTrace = {
  mode?: string;
  status?: string;
  skip_reason?: string;
  [key: string]: unknown;
};

export type AnswerTrace = {
  prompt_version: string;
  provider_id: string | null;
  model_name: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  stage_ms: Record<string, number>;
  verification: AnswerVerificationTrace;
  [key: string]: unknown;
};

export type AnswerResult = {
  id: string;
  status: AnswerStatus;
  reason: AnswerReason | null;
  answer: string | null;
  message: string | null;
  statements: AnswerStatement[];
  sources: AnswerSource[];
  index_run_id: string;
  generation: number;
  trace: AnswerTrace;
  coverage: Record<string, unknown> | null;
};

export type AnswerLabel = "correct" | "missing" | "wrong_source" | "wrong_year";

export type AnswerReviewItemStatus =
  | "answered"
  | "insufficient_evidence"
  | "failed"
  | "uncertain";

export type AnswerReviewItem = {
  id: string;
  review_id: string;
  ordinal: number;
  question: string;
  status: AnswerReviewItemStatus;
  error_code: string | null;
  result: AnswerResult | null;
  index_run_id: string | null;
  generation: number | null;
  label: AnswerLabel | null;
  label_note: string | null;
  labelled_by: string | null;
  labelled_at: string | null;
  created_at: string;
  finished_at: string | null;
};

export type AnswerReviewStatus =
  | "running"
  | "completed"
  | "failed"
  | "uncertain";

export type AnswerReview = {
  id: string;
  workspace_id: string;
  collection_id: string;
  assistant_id: string;
  assistant_revision: number;
  requested_by: string;
  question_count: number;
  status: AnswerReviewStatus;
  error_code: string | null;
  created_at: string;
  finished_at: string | null;
  items: AnswerReviewItem[];
};

export type AnswerReviewCreateRequest = {
  questions: string[];
};

export type AnswerReviewLabelRequest = {
  label: AnswerLabel | null;
  note: string;
};
