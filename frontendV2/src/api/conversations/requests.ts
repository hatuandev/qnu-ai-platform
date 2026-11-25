/**
 * HTTP request functions for conversation logs.
 * Mirrors `backendV1/qnu/domains/conversations/router.py`.
 */

import type { BlobResponse } from "../client";
import { v1Client } from "../v1-client";
import { conversationPaths } from "./endpoints";
import type {
  Conversation,
  ConversationTurn,
  ExportFormat,
  PromoteToBenchmarkRequest,
  PromoteToBenchmarkResponse,
} from "./types";

export async function listConversations(
  workspaceId: string,
  params?: { assistantId?: string; limit?: number; offset?: number },
  options?: { signal?: AbortSignal },
): Promise<Conversation[]> {
  return v1Client.get<Conversation[]>(conversationPaths.list(workspaceId), {
    searchParams: {
      assistant_id: params?.assistantId,
      limit: params?.limit ?? 20,
      offset: params?.offset ?? 0,
    },
    signal: options?.signal,
  });
}

export async function createConversation(
  workspaceId: string,
  body: { assistant_id: string; title?: string },
  options?: { signal?: AbortSignal },
): Promise<Conversation> {
  return v1Client.post<Conversation>(
    conversationPaths.list(workspaceId),
    body,
    {
      signal: options?.signal,
    },
  );
}

export async function sendConversationTurn(
  workspaceId: string,
  conversationId: string,
  body: { question: string; expected_turn_no: number; model?: string },
  idempotencyKey: string,
  options?: { signal?: AbortSignal },
): Promise<ConversationTurn> {
  return v1Client.post<ConversationTurn>(
    conversationPaths.turns(workspaceId, conversationId),
    body,
    { idempotencyKey, signal: options?.signal, timeoutMs: null },
  );
}

export async function listConversationTurns(
  workspaceId: string,
  conversationId: string,
  params?: { limit?: number; offset?: number },
  options?: { signal?: AbortSignal },
): Promise<ConversationTurn[]> {
  return v1Client.get<ConversationTurn[]>(
    conversationPaths.turns(workspaceId, conversationId),
    {
      searchParams: {
        limit: params?.limit ?? 20,
        offset: params?.offset ?? 0,
      },
      signal: options?.signal,
    },
  );
}

export async function submitTurnFeedback(
  workspaceId: string,
  conversationId: string,
  turnId: string,
  body: { rating: "like" | "dislike" | null; reason?: string | null },
  options?: { signal?: AbortSignal },
): Promise<ConversationTurn> {
  return v1Client.post<ConversationTurn>(
    conversationPaths.feedback(workspaceId, conversationId, turnId),
    body,
    { signal: options?.signal },
  );
}

export async function promoteTurnToBenchmark(
  workspaceId: string,
  conversationId: string,
  turnId: string,
  body?: PromoteToBenchmarkRequest,
  options?: { signal?: AbortSignal },
): Promise<PromoteToBenchmarkResponse> {
  return v1Client.post<PromoteToBenchmarkResponse>(
    conversationPaths.promoteToBenchmark(workspaceId, conversationId, turnId),
    body ?? {},
    { signal: options?.signal },
  );
}

export async function downloadTurnExport(
  workspaceId: string,
  conversationId: string,
  turnId: string,
  format: ExportFormat,
  fallbackTitle?: string,
): Promise<string> {
  const result = await v1Client.request<BlobResponse>(
    conversationPaths.exportTurn(workspaceId, conversationId, turnId),
    {
      method: "GET",
      searchParams: { format },
      responseType: "blob",
      timeoutMs: 120_000,
    },
  );
  const safeBase = (fallbackTitle || "ban-thao")
    .replace(/[\\/:*?"<>|\r\n]+/g, " ")
    .trim()
    .slice(0, 80);
  const filename = result.fileName || `${safeBase || "ban-thao"}.${format}`;
  const url = URL.createObjectURL(result.blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  return filename;
}
