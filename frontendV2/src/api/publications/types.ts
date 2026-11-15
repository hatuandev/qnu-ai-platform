/**
 * TypeScript types for the Publications domain (public chatbot links).
 * Mirrors `backendV1/qnu/domains/publications/schemas.py`.
 */

import type { AssistantReadinessStatus } from "../assistants/types";

export type PublicationResponse = {
  configured: boolean;
  enabled: boolean;
  slug: string | null;
  display_name: string;
  welcome_message: string;
  starter_prompts: string[];
  max_turns_per_session: number;
  daily_token_budget: number | null;
  revision: number;
  updated_by: string | null;
  updated_at: string | null;
  public_path: string | null;
  system_enabled: boolean;
  readiness: AssistantReadinessStatus;
};

export type PublicationUpdateRequest = {
  slug: string;
  display_name: string;
  welcome_message: string;
  starter_prompts: string[];
  max_turns_per_session: number;
  daily_token_budget: number | null;
  enabled: boolean;
  expected_revision: number | null;
};

export type PublicChatbotInfo = {
  display_name: string;
  welcome_message: string;
  starter_prompts: string[];
  max_turns_per_session: number;
  available: boolean;
  unavailable_reason: string | null;
};

export type PublicChatbotSummary = {
  slug: string;
  display_name: string;
  welcome_message: string;
  available: boolean;
  unavailable_reason: string | null;
};

export type PublicChatbotList = {
  chatbots: PublicChatbotSummary[];
};

export type PublicChatSession = {
  session_id: string;
  expires_in_seconds: number;
  max_turns: number;
  turns_remaining: number;
};

export type PublicTurnRequest = {
  session_id: string;
  question: string;
};

export type PublicCitation = {
  index: number;
  title: string;
  page: number | null;
};

export type PublicTurnResponse = {
  status: "answered" | "insufficient_evidence";
  answer: string | null;
  message: string | null;
  citations: PublicCitation[];
  turns_remaining: number;
};

export type PublicationStatDay = {
  day: string;
  sessions: number;
  turns: number;
  insufficient_turns: number;
  error_turns: number;
  tokens: number;
};

export type PublicationStatTotals = {
  sessions: number;
  turns: number;
  insufficient_turns: number;
  error_turns: number;
  tokens: number;
};

export type PublicationUnansweredQuestion = {
  question: string;
  times_asked: number;
  last_asked_at: string;
};

export type PublicationStats = {
  configured: boolean;
  days: number;
  totals: PublicationStatTotals;
  daily: PublicationStatDay[];
  budget_limit: number | null;
  budget_used_today: number;
  top_questions: PublicationUnansweredQuestion[];
};
