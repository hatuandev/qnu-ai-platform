/**
 * HTTP request functions for conversation logs.
 * Mirrors `backendV1/qnu/domains/conversations/router.py`.
 */

import { v1Client } from "../v1-client";
import { conversationPaths } from "./endpoints";
import type {
  Conversation,
  ConversationTurn,
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
  body: { question: string; expected_turn_no: number },
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
