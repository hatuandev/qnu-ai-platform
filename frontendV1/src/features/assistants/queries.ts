import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import {
  createAssistant,
  getAssistant,
  getAssistantReadiness,
  listAssistants,
  updateAssistant,
} from "@/features/assistants/requests";
import type {
  Assistant,
  AssistantCreateInput,
  AssistantListParams,
  AssistantReadiness,
  AssistantUpdateInput,
} from "@/features/assistants/types";

export const assistantKeys = {
  all: (sessionId?: number, workspaceId?: string) =>
    sessionId !== undefined && workspaceId !== undefined
      ? (["v1", sessionId, "workspaces", workspaceId, "assistants"] as const)
      : (["v1", "assistants"] as const),

  list: (
    sessionId?: number,
    workspaceId?: string,
    params?: AssistantListParams,
  ) =>
    sessionId !== undefined && workspaceId !== undefined
      ? ([
          "v1",
          sessionId,
          "workspaces",
          workspaceId,
          "assistants",
          "list",
          params?.limit ?? 20,
          params?.offset ?? 0,
        ] as const)
      : (["v1", "assistants", "list"] as const),

  detail: (sessionId?: number, workspaceId?: string, assistantId?: string) =>
    sessionId !== undefined &&
    workspaceId !== undefined &&
    assistantId !== undefined
      ? ([
          "v1",
          sessionId,
          "workspaces",
          workspaceId,
          "assistants",
          "detail",
          assistantId,
        ] as const)
      : (["v1", "assistants", "detail"] as const),

  readiness: (
    sessionId?: number,
    workspaceId?: string,
    assistantId?: string,
  ) =>
    sessionId !== undefined &&
    workspaceId !== undefined &&
    assistantId !== undefined
      ? ([
          "v1",
          sessionId,
          "workspaces",
          workspaceId,
          "assistants",
          "readiness",
          assistantId,
        ] as const)
      : (["v1", "assistants", "readiness"] as const),
};

export function useAssistantsQuery(
  workspaceId: string,
  params?: AssistantListParams,
) {
  const { sessionId } = useV1Auth();
  return useQuery<Assistant[]>({
    queryKey: assistantKeys.list(sessionId, workspaceId, params),
    queryFn: ({ signal }) =>
      listAssistants(v1Client, workspaceId, params, { signal }),
    enabled: Boolean(workspaceId),
  });
}

export function useAssistantQuery(workspaceId: string, assistantId: string) {
  const { sessionId } = useV1Auth();
  return useQuery<Assistant>({
    queryKey: assistantKeys.detail(sessionId, workspaceId, assistantId),
    queryFn: ({ signal }) =>
      getAssistant(v1Client, workspaceId, assistantId, { signal }),
    enabled: Boolean(workspaceId && assistantId),
  });
}

export function useAssistantReadinessQuery(
  workspaceId: string,
  assistantId: string,
) {
  const { sessionId } = useV1Auth();
  return useQuery<AssistantReadiness>({
    queryKey: assistantKeys.readiness(sessionId, workspaceId, assistantId),
    queryFn: ({ signal }) =>
      getAssistantReadiness(v1Client, workspaceId, assistantId, { signal }),
    enabled: Boolean(workspaceId && assistantId),
    // Truthful live state only: poll while publication/index is being prepared.
    refetchInterval: (query) =>
      query.state.data?.status === "syncing" ? 5000 : false,
  });
}

export function useCreateAssistant(workspaceId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<Assistant, Error, AssistantCreateInput>({
    mutationFn: (input) => createAssistant(v1Client, workspaceId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: assistantKeys.all(sessionId, workspaceId),
      });
      void queryClient.invalidateQueries({
        queryKey: ["v1", sessionId, "workspaces", "events", workspaceId],
      });
    },
  });
}

export function useUpdateAssistant(workspaceId: string, assistantId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<Assistant, Error, AssistantUpdateInput>({
    mutationFn: (input) =>
      updateAssistant(v1Client, workspaceId, assistantId, input),
    onSuccess: (updatedAssistant) => {
      // Invalidate both list and detail queries
      void queryClient.invalidateQueries({
        queryKey: assistantKeys.all(sessionId, workspaceId),
      });
      void queryClient.invalidateQueries({
        queryKey: assistantKeys.detail(sessionId, workspaceId, assistantId),
      });
      void queryClient.setQueryData(
        assistantKeys.detail(sessionId, workspaceId, assistantId),
        updatedAssistant,
      );
      void queryClient.invalidateQueries({
        queryKey: ["v1", sessionId, "workspaces", "events", workspaceId],
      });
    },
  });
}
