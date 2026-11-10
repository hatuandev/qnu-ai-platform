/**
 * TanStack Query hooks for Lifecycle domain.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { knowledgeKeys } from "../knowledge/queries";
import {
  commitLifecycleAction,
  createLifecyclePreview,
  getLifecycleAction,
} from "./requests";
import type {
  LifecycleActionReceipt,
  LifecycleActionRequest,
  LifecyclePreviewRequest,
} from "./types";

export const lifecycleKeys = {
  all: ["v1", "lifecycle"] as const,

  action: (workspaceId: string, actionId: string) =>
    [...lifecycleKeys.all, "action", workspaceId, actionId] as const,
};

export function useLifecycleActionQuery(
  workspaceId?: string | null,
  actionId?: string | null,
) {
  return useQuery({
    queryKey:
      workspaceId && actionId
        ? lifecycleKeys.action(workspaceId, actionId)
        : [...lifecycleKeys.all, "action", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !actionId)
        throw new Error("workspaceId and actionId are required");
      return getLifecycleAction(workspaceId, actionId, { signal });
    },
    enabled: Boolean(workspaceId && actionId),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 2000;
      return data.status === "pending" || data.status === "preview"
        ? 2000
        : false;
    },
  });
}

export function useCreateLifecyclePreviewMutation(workspaceId?: string | null) {
  return useMutation({
    mutationFn: (data: LifecyclePreviewRequest) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return createLifecyclePreview(workspaceId, data);
    },
  });
}

export function useCommitLifecycleActionMutation(workspaceId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      data,
      idempotencyKey,
    }: {
      data: LifecycleActionRequest;
      idempotencyKey?: string;
    }) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return commitLifecycleAction(workspaceId, data, idempotencyKey);
    },
    onSuccess: (receipt: LifecycleActionReceipt) => {
      if (workspaceId) {
        void queryClient.setQueryData(
          lifecycleKeys.action(workspaceId, receipt.id),
          receipt,
        );
        // If source delete, invalidate knowledge sources
        if (receipt.kind === "source") {
          void queryClient.invalidateQueries({
            queryKey: [...knowledgeKeys.all, "sources", workspaceId],
          });
        }
      }
    },
  });
}
