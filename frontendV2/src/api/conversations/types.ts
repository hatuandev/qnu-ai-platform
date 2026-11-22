/**
 * TypeScript types for assistant conversation logs.
 * Mirrors `backendV1/qnu/domains/conversations/schemas.py`; a completed turn
 * embeds the same `AnswerResponse` contract as answer reviews.
 */

import type { AnswerResult } from "@/api/answer-reviews";

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

export type TurnStatus =
  | "running"
  | "completed"
  | "failed"
  | "uncertain"
  | "cancelled";

export type DirectReply = {
  id: string;
  status: "direct_reply";
  route:
    | "greeting"
    | "courtesy"
    | "identity"
    | "protected_request"
    | "guardrail"
    | "direct_chat";
  answer: string;
};

export type TurnFeedback = {
  rating: "like" | "dislike";
  reason?: string | null;
  updated_at?: string;
};

export type TurnFeedbackRequest = {
  rating: "like" | "dislike" | null;
  reason?: string | null;
};

export type ConversationTurn = {
  id: string;
  conversation_id: string;
  turn_no: number;
  question: string;
  resolved_question: string | null;
  metadata_filter: Record<string, unknown>;
  history_turn_ids: string[];
  status: TurnStatus;
  error_code: string | null;
  result: AnswerResult | DirectReply | null;
  feedback?: TurnFeedback | null;
  rewrite_trace: Record<string, unknown> | null;
  source_status: string;
  source_status_reason: string | null;
  created_at: string;
  finished_at: string | null;
};

export type PromoteToBenchmarkRequest = {
  expected_points?: string[];
  expected_behavior?: string;
  notes?: string;
};

export type PromoteToBenchmarkResponse = {
  turn_id: string;
  question_id: string;
  question: string;
  already_exists: boolean;
  benchmark_file: string;
  total_questions: number;
};
