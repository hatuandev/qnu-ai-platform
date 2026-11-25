/**
 * TanStack Query hooks for assistant conversation logs.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createConversation,
  listConversations,
  listConversationTurns,
  promoteTurnToBenchmark,
  sendConversationTurn,
  submitTurnFeedback,
} from "./requests";
import type {
  Conversation,
  ConversationTurn,
  PromoteToBenchmarkRequest,
} from "./types";

export const conversationKeys = {
  all: ["v1", "conversations"] as const,
  list: (workspaceId: string, assistantId: string) =>
    [...conversationKeys.all, "list", workspaceId, assistantId] as const,
  turns: (workspaceId: string, conversationId: string) =>
    [...conversationKeys.all, "turns", workspaceId, conversationId] as const,
};

const RUNNING_POLL_MS = 1500;

export function useAssistantConversationsQuery(
  workspaceId?: string | null,
  assistantId?: string | null,
) {
  return useQuery({
    queryKey:
      workspaceId && assistantId
        ? conversationKeys.list(workspaceId, assistantId)
        : [...conversationKeys.all, "list", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !assistantId) {
        throw new Error("workspaceId and assistantId are required");
      }
      return listConversations(
        workspaceId,
        { assistantId, limit: 20 },
        { signal },
      );
    },
    enabled: Boolean(workspaceId && assistantId),
  });
}

export function useConversationTurnsQuery(
  workspaceId?: string | null,
  conversationId?: string | null,
  enabled = true,
) {
  return useQuery({
    queryKey:
      workspaceId && conversationId
        ? conversationKeys.turns(workspaceId, conversationId)
        : [...conversationKeys.all, "turns", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !conversationId) {
        throw new Error("workspaceId and conversationId are required");
      }
      return listConversationTurns(
        workspaceId,
        conversationId,
        { limit: 20 },
        { signal },
      );
    },
    enabled: Boolean(workspaceId && conversationId && enabled),
    refetchInterval: (query) =>
      query.state.data?.some((turn) => turn.status === "running")
        ? RUNNING_POLL_MS
        : false,
  });
}

export function useCreateConversationMutation(workspaceId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      assistantId,
      title,
    }: {
      assistantId: string;
      title?: string;
    }) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return createConversation(workspaceId, {
        assistant_id: assistantId,
        title,
      });
    },
    onSuccess: (conversation, variables) => {
      if (!workspaceId) return;
      const listKey = conversationKeys.list(workspaceId, variables.assistantId);
      queryClient.setQueryData<Conversation[]>(listKey, (previous) =>
        previous
          ? [
              conversation,
              ...previous.filter((item) => item.id !== conversation.id),
            ]
          : [conversation],
      );
      void queryClient.invalidateQueries({
        queryKey: [...conversationKeys.all, "list", workspaceId],
      });
    },
  });
}

export function useSendTurnMutation(workspaceId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      conversationId,
      question,
      expectedTurnNo,
      model,
      providerId,
      signal,
    }: {
      conversationId: string;
      question: string;
      expectedTurnNo: number;
      model?: string | null;
      providerId?: string | null;
      signal?: AbortSignal;
    }) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return sendConversationTurn(
        workspaceId,
        conversationId,
        {
          question,
          expected_turn_no: expectedTurnNo,
          ...(model ? { model } : {}),
          ...(providerId ? { provider_id: providerId } : {}),
        },
        `chat_${crypto.randomUUID()}`,
        { signal },
      );
    },
    onSuccess: (turn, variables) => {
      if (!workspaceId) return;
      const key = conversationKeys.turns(workspaceId, variables.conversationId);
      queryClient.setQueryData<ConversationTurn[]>(key, (previous) => {
        if (!previous) return [turn];
        const exists = previous.some((item) => item.id === turn.id);
        if (exists) {
          return previous.map((item) => (item.id === turn.id ? turn : item));
        }
        return [...previous, turn].sort(
          (left, right) => left.turn_no - right.turn_no,
        );
      });
      void queryClient.invalidateQueries({
        queryKey: [...conversationKeys.all, "list", workspaceId],
      });
    },
    onError: (_error, variables) => {
      if (!workspaceId) return;
      void queryClient.invalidateQueries({
        queryKey: conversationKeys.turns(workspaceId, variables.conversationId),
      });
    },
  });
}

export function useSubmitTurnFeedbackMutation(workspaceId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      conversationId,
      turnId,
      rating,
      reason,
      signal,
    }: {
      conversationId: string;
      turnId: string;
      rating: "like" | "dislike" | null;
      reason?: string | null;
      signal?: AbortSignal;
    }) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return submitTurnFeedback(
        workspaceId,
        conversationId,
        turnId,
        { rating, reason },
        { signal },
      );
    },
    onSuccess: (updatedTurn, variables) => {
      if (!workspaceId) return;
      const key = conversationKeys.turns(workspaceId, variables.conversationId);
      queryClient.setQueryData<ConversationTurn[]>(key, (previous) => {
        if (!previous) return [updatedTurn];
        return previous.map((item) =>
          item.id === updatedTurn.id ? updatedTurn : item,
        );
      });
    },
  });
}

export function usePromoteTurnToBenchmarkMutation(workspaceId?: string | null) {
  return useMutation({
    mutationFn: ({
      conversationId,
      turnId,
      body,
      signal,
    }: {
      conversationId: string;
      turnId: string;
      body?: PromoteToBenchmarkRequest;
      signal?: AbortSignal;
    }) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return promoteTurnToBenchmark(workspaceId, conversationId, turnId, body, {
        signal,
      });
    },
  });
}
