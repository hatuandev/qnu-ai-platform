/**
 * TanStack Query hooks for the Assistants domain.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createAssistant,
  deleteAssistant,
  getAssistant,
  getAssistantReadiness,
  listAssistants,
  updateAssistant,
} from "./requests";
import type { AssistantCreateRequest, AssistantUpdateRequest } from "./types";

export const assistantKeys = {
  all: ["v1", "assistants"] as const,
  list: (workspaceId: string) =>
    [...assistantKeys.all, "list", workspaceId] as const,
  detail: (workspaceId: string, assistantId: string) =>
    [...assistantKeys.all, "detail", workspaceId, assistantId] as const,
  readiness: (workspaceId: string, assistantId: string) =>
    [...assistantKeys.all, "readiness", workspaceId, assistantId] as const,
};

export function useAssistantQuery(
  workspaceId?: string | null,
  assistantId?: string | null,
) {
  return useQuery({
    queryKey:
      workspaceId && assistantId
        ? assistantKeys.detail(workspaceId, assistantId)
        : [...assistantKeys.all, "detail", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !assistantId) {
        throw new Error("workspaceId and assistantId are required");
      }
      return getAssistant(workspaceId, assistantId, { signal });
    },
    enabled: Boolean(workspaceId && assistantId),
  });
}

export function useAssistantsQuery(workspaceId?: string | null) {
  return useQuery({
    queryKey: workspaceId
      ? assistantKeys.list(workspaceId)
      : [...assistantKeys.all, "list", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return listAssistants(workspaceId, { limit: 100 }, { signal });
    },
    enabled: Boolean(workspaceId),
  });
}

export function useAssistantReadinessQuery(
  workspaceId?: string | null,
  assistantId?: string | null,
) {
  return useQuery({
    queryKey:
      workspaceId && assistantId
        ? assistantKeys.readiness(workspaceId, assistantId)
        : [...assistantKeys.all, "readiness", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !assistantId) {
        throw new Error("workspaceId and assistantId are required");
      }
      return getAssistantReadiness(workspaceId, assistantId, { signal });
    },
    enabled: Boolean(workspaceId && assistantId),
    staleTime: 30 * 1000,
  });
}

export function useCreateAssistantMutation(workspaceId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AssistantCreateRequest) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return createAssistant(workspaceId, data);
    },
    onSuccess: () => {
      if (workspaceId) {
        void queryClient.invalidateQueries({
          queryKey: assistantKeys.list(workspaceId),
        });
      }
    },
  });
}

export function useUpdateAssistantMutation(workspaceId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      assistantId,
      data,
    }: {
      assistantId: string;
      data: AssistantUpdateRequest;
    }) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return updateAssistant(workspaceId, assistantId, data);
    },
    onSuccess: (assistant) => {
      if (workspaceId) {
        queryClient.setQueryData(
          assistantKeys.detail(workspaceId, assistant.id),
          assistant,
        );
        void queryClient.invalidateQueries({
          queryKey: assistantKeys.list(workspaceId),
        });
        void queryClient.invalidateQueries({
          queryKey: assistantKeys.readiness(workspaceId, assistant.id),
        });
      }
    },
  });
}

export function useDeleteAssistantMutation(workspaceId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (assistantId: string) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return deleteAssistant(workspaceId, assistantId);
    },
    onSuccess: (_data, assistantId) => {
      if (workspaceId) {
        queryClient.removeQueries({
          queryKey: assistantKeys.readiness(workspaceId, assistantId),
        });
        queryClient.removeQueries({
          queryKey: assistantKeys.detail(workspaceId, assistantId),
        });
        void queryClient.invalidateQueries({
          queryKey: assistantKeys.list(workspaceId),
        });
      }
    },
  });
}
