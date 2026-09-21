import type {
  ConversationMessage,
  ConversationReplyRequest,
  ConversationStatusUpdateRequest,
  ConversationThreadDetail,
  ConversationThreadItem,
} from "@/types/conversations";

const CONVERSATIONS_URL = "/platform/v1alpha1/conversations";

function getErrorMessage(payload: unknown, status: number): string {
  if (typeof payload === "object" && payload !== null) {
    const record = payload as Record<string, unknown>;
    if (typeof record.detail === "string") return record.detail;
    if (typeof record.title === "string") return record.title;
  }
  return `Thao tác hội thoại thất bại (HTTP ${status}).`;
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    throw new Error(getErrorMessage(payload, response.status));
  }
  return (await response.json()) as T;
}

export async function listConversations(params?: {
  assistant_code?: string;
  status?: string;
  search?: string;
}): Promise<ConversationThreadItem[]> {
  const query = new URLSearchParams();
  if (params?.assistant_code) query.set("assistant_code", params.assistant_code);
  if (params?.status && params.status !== "all") query.set("status", params.status);
  if (params?.search?.trim()) query.set("search", params.search.trim());

  const url = query.toString() ? `${CONVERSATIONS_URL}?${query.toString()}` : CONVERSATIONS_URL;
  return requestJson<ConversationThreadItem[]>(url);
}

export async function getConversationDetail(id: string): Promise<ConversationThreadDetail> {
  return requestJson<ConversationThreadDetail>(`${CONVERSATIONS_URL}/${encodeURIComponent(id)}`);
}

export async function replyConversation(
  id: string,
  body: ConversationReplyRequest
): Promise<ConversationMessage> {
  return requestJson<ConversationMessage>(`${CONVERSATIONS_URL}/${encodeURIComponent(id)}/reply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function updateConversationStatus(
  id: string,
  body: ConversationStatusUpdateRequest
): Promise<ConversationThreadItem> {
  return requestJson<ConversationThreadItem>(
    `${CONVERSATIONS_URL}/${encodeURIComponent(id)}/status`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }
  );
}

export interface FeedbackVoteRequest {
  thread_id?: string | null;
  assistant_code: string;
  vote: "up" | "down";
  question?: string;
  answer?: string;
}

export async function recordFeedbackVote(body: FeedbackVoteRequest): Promise<unknown> {
  return requestJson<unknown>(`${CONVERSATIONS_URL}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export interface FeedbackStats {
  total: number;
  up: number;
  down: number;
  up_rate: number;
  assistant_code: string | null;
}

export interface FeedbackTrendPoint {
  date: string;
  up: number;
  down: number;
}

export interface FeedbackTrend {
  points: FeedbackTrendPoint[];
  days: number;
}

export interface FeedbackSample {
  id: string;
  thread_id: string | null;
  assistant_code: string;
  vote: "up" | "down";
  question_excerpt: string;
  answer_excerpt: string;
  created_at: string;
}

export async function getFeedbackStats(assistantCode?: string): Promise<FeedbackStats> {
  const query = assistantCode ? `?assistant_code=${encodeURIComponent(assistantCode)}` : "";
  return requestJson<FeedbackStats>(`${CONVERSATIONS_URL}/feedback/stats${query}`);
}

export async function getFeedbackTrend(days = 14): Promise<FeedbackTrend> {
  return requestJson<FeedbackTrend>(`${CONVERSATIONS_URL}/feedback/trend?days=${days}`);
}

export async function getFeedbackSamples(
  vote: "up" | "down" = "down",
  limit = 20
): Promise<FeedbackSample[]> {
  return requestJson<FeedbackSample[]>(
    `${CONVERSATIONS_URL}/feedback/samples?vote=${vote}&limit=${limit}`
  );
}

export const conversationsApi = {
  listConversations,
  getConversationDetail,
  replyConversation,
  updateConversationStatus,
  recordFeedbackVote,
  getFeedbackStats,
  getFeedbackTrend,
  getFeedbackSamples,
};
