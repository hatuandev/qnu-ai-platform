/**
 * Assistant answer-test types mirroring
 * `backendV1/qnu/domains/answer_review/schemas.py`.
 *
 * These records are human answer reviews, not retrieval benchmark gold: the
 * question/answer store is separate from `gold_chunk_ids`.
 */

import type { AnswerResponse } from "@/features/conversations/types";

export type AnswerReviewLabel =
  | "correct"
  | "missing"
  | "wrong_source"
  | "wrong_year";

export type AnswerReviewItemStatus =
  | "answered"
  | "insufficient_evidence"
  | "failed"
  | "uncertain";

export type AnswerReviewStatus =
  | "running"
  | "completed"
  | "failed"
  | "uncertain";

export type AnswerReviewItem = {
  id: string;
  review_id: string;
  ordinal: number;
  question: string;
  status: AnswerReviewItemStatus;
  error_code: string | null;
  result: AnswerResponse | null;
  index_run_id: string | null;
  generation: number | null;
  label: AnswerReviewLabel | null;
  label_note: string | null;
  labelled_by: string | null;
  labelled_at: string | null;
  created_at: string;
  finished_at: string | null;
};

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

export type AnswerReviewCreateInput = {
  questions: string[];
};

export type AnswerReviewLabelInput = {
  label: AnswerReviewLabel | null;
  note?: string;
};

export type AnswerReviewListParams = {
  limit?: number;
  offset?: number;
};
