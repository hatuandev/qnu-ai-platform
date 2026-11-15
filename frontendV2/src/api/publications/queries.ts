/**
 * TanStack Query hooks for the Publications domain.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { assistantKeys } from "../assistants/queries";
import {
  createPublicChatSession,
  getPublication,
  getPublicationStats,
  getPublicChatbotInfo,
  getPublicChatbotList,
  savePublication,
  sendPublicTurn,
} from "./requests";
import type { PublicationUpdateRequest, PublicTurnRequest } from "./types";

export const publicationKeys = {
  all: ["v1", "publications"] as const,
  detail: (workspaceId: string, assistantId: string) =>
    [...publicationKeys.all, "detail", workspaceId, assistantId] as const,
  stats: (workspaceId: string, assistantId: string, days: number) =>
    [...publicationKeys.all, "stats", workspaceId, assistantId, days] as const,
  publicList: ["v1", "publications", "public-list"] as const,
  publicInfo: (slug: string) =>
    [...publicationKeys.all, "public-info", slug] as const,
};

export function useAssistantPublicationQuery(
  workspaceId?: string | null,
  assistantId?: string | null,
) {
  return useQuery({
    queryKey:
      workspaceId && assistantId
        ? publicationKeys.detail(workspaceId, assistantId)
        : [...publicationKeys.all, "detail", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !assistantId) {
        throw new Error("workspaceId and assistantId are required");
      }
      return getPublication(workspaceId, assistantId, { signal });
    },
    enabled: Boolean(workspaceId && assistantId),
    staleTime: 30 * 1000,
  });
}

export function useSavePublicationMutation(
  workspaceId?: string | null,
  assistantId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PublicationUpdateRequest) => {
      if (!workspaceId || !assistantId) {
        throw new Error("workspaceId and assistantId are required");
      }
      return savePublication(workspaceId, assistantId, data);
    },
    onSuccess: (publication) => {
      if (workspaceId && assistantId) {
        queryClient.setQueryData(
          publicationKeys.detail(workspaceId, assistantId),
          publication,
        );
        void queryClient.invalidateQueries({
          queryKey: assistantKeys.list(workspaceId),
        });
      }
    },
  });
}

export function usePublicationStatsQuery(
  workspaceId?: string | null,
  assistantId?: string | null,
  days = 7,
) {
  return useQuery({
    queryKey:
      workspaceId && assistantId
        ? publicationKeys.stats(workspaceId, assistantId, days)
        : [...publicationKeys.all, "stats", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !assistantId) {
        throw new Error("workspaceId and assistantId are required");
      }
      return getPublicationStats(workspaceId, assistantId, days, { signal });
    },
    enabled: Boolean(workspaceId && assistantId),
    staleTime: 30 * 1000,
    retry: 1,
  });
}

export function usePublicChatbotListQuery() {
  return useQuery({
    queryKey: publicationKeys.publicList,
    queryFn: ({ signal }) => getPublicChatbotList({ signal }),
    staleTime: 60 * 1000,
    retry: 1,
  });
}

export function usePublicChatbotInfoQuery(slug?: string | null) {
  return useQuery({
    queryKey: slug
      ? publicationKeys.publicInfo(slug)
      : [...publicationKeys.all, "public-info", "empty"],
    queryFn: ({ signal }) => {
      if (!slug) throw new Error("slug is required");
      return getPublicChatbotInfo(slug, { signal });
    },
    enabled: Boolean(slug),
    staleTime: 30 * 1000,
    retry: false,
  });
}

export function useCreatePublicChatSessionMutation(slug: string) {
  return useMutation({
    mutationFn: () => createPublicChatSession(slug),
  });
}

export function useSendPublicTurnMutation(slug: string) {
  return useMutation({
    mutationFn: (data: PublicTurnRequest) => sendPublicTurn(slug, data),
  });
}
