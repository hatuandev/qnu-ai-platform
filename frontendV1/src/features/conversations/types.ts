/**
 * Conversation and Turn domain types strictly mirroring backendV1 schemas
 * from `backendV1/qnu/domains/conversations/schemas.py` and `backendV1/qnu/domains/rag/answer/schemas.py`.
 */

import type {
  ContextTrace,
  MetadataFilter,
  RetrievalTrace,
  VerificationTrace,
} from "@/features/rag/types";

export type ConversationStatus = "active" | "archived";

export type Conversation = {
  id: string;
  workspace_id: string;
  collection_id: string;
  assistant_id: string;
  assistant_revision: number;
  owner_ref: string;
  title: string;
  status: ConversationStatus;
  document_ids: string[] | null;
  last_turn_no: number;
  created_at: string;
  updated_at: string;
};

export type ConversationCreateInput = {
  assistant_id: string;
  title?: string;
  document_ids?: string[] | null;
};

export type ConversationUpdateInput = {
  title: string;
  status: ConversationStatus;
};

/**
 * `cancelled` is a terminal state: the backend stops the turn (assistant stop,
 * conversation archived mid-answer, lease replacement) and records
 * `error_code = "operation_cancelled"`. The turn keeps its idempotency key, so
 * the UI must not offer to resend it as a brand-new request.
 */
export type TurnStatus =
  | "running"
  | "completed"
  | "failed"
  | "uncertain"
  | "cancelled";

export type AnswerStatus = "answered" | "insufficient_evidence";

export type InsufficientEvidenceReason =
  | "no_eligible_content"
  | "no_match"
  | "model_abstained"
  | "answer_not_supported"
  | "answer_verification_uncertain";

export type Statement = {
  text: string;
  evidence_ids: string[];
};

export type EvidenceSource = {
  evidence_id: string;
  chunk_id: string;
  document_id: string;
  version_id: string;
  publication_decision_id: string;
  score: number;
  kind: string;
  text: string;
  citations: Record<string, unknown>;
  structure: Record<string, unknown> | null;
};

export type AnswerTrace = {
  retrieval?: RetrievalTrace & Record<string, unknown>;
  prompt_version?: string;
  evidence_sha256?: string | null;
  provider_id?: string | null;
  model_name?: string | null;
  configuration_hash?: string | null;
  usage_id?: string | null;
  /**
   * Generation usage only. The judge keeps its own usage inside
   * `trace.verification`; never present these numbers as pipeline totals.
   */
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
  stage_ms?: Record<string, number>;
  context?: ContextTrace;
  verification?: VerificationTrace;
};

export type AnswerResponse = {
  id: string;
  status: AnswerStatus;
  reason?: InsufficientEvidenceReason | null;
  answer?: string | null;
  statements: Statement[];
  sources: EvidenceSource[];
  index_run_id: string;
  generation: number;
  trace: AnswerTrace;
};

export type SourceStatus = "current" | "unavailable";

export type TurnResponse = {
  id: string;
  conversation_id: string;
  turn_no: number;
  question: string;
  resolved_question: string | null;
  /** Explicit scope actually used by the backend for this turn. */
  metadata_filter?: MetadataFilter;
  history_turn_ids: string[];
  status: TurnStatus;
  error_code: string | null;
  result: AnswerResponse | null;
  rewrite_trace: Record<string, unknown> | null;
  source_status: SourceStatus;
  created_at: string;
  finished_at: string | null;
};

export type TurnRequestInput = {
  question: string;
  expected_turn_no: number;
  /**
   * Explicit metadata scope. Omitted means "inherit the assistant policy and the
   * last completed turn"; the backend rejects a value that contradicts a fixed
   * assistant scope with `conversation_scope_conflict`.
   */
  metadata_filter?: MetadataFilter | null;
};

export type ConversationListParams = {
  limit?: number;
  offset?: number;
};

export type TurnListParams = {
  limit?: number;
  offset?: number;
};
