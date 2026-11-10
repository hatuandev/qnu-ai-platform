/**
 * TanStack Query hooks for Preparation domain.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  cancelPreparationIntent,
  createPreparationIntent,
  getPreparationIntent,
  listPreparationIntents,
} from "./requests";
import type { PreparationRequestInput } from "./types";

export const preparationKeys = {
  all: ["v1", "preparation"] as const,

  intents: (workspaceId: string, collectionId: string, sourceId: string) =>
    [
      ...preparationKeys.all,
      "intents",
      workspaceId,
      collectionId,
      sourceId,
    ] as const,

  intent: (workspaceId: string, collectionId: string, intentId: string) =>
    [
      ...preparationKeys.all,
      "intent",
      workspaceId,
      collectionId,
      intentId,
    ] as const,
};

export function usePreparationIntentQuery(
  workspaceId?: string | null,
  collectionId?: string | null,
  intentId?: string | null,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey:
      workspaceId && collectionId && intentId
        ? preparationKeys.intent(workspaceId, collectionId, intentId)
        : [...preparationKeys.all, "intent", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !collectionId || !intentId)
        throw new Error("workspaceId, collectionId and intentId are required");
      return getPreparationIntent(workspaceId, collectionId, intentId, {
        signal,
      });
    },
    enabled: Boolean(
      workspaceId && collectionId && intentId && (options?.enabled ?? true),
    ),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 2000;
      const isRunning =
        data.status === "queued" ||
        data.status === "waiting_ocr" ||
        data.status === "compiling";
      return isRunning ? 2500 : false;
    },
  });
}

export function usePreparationIntentsQuery(
  workspaceId?: string | null,
  collectionId?: string | null,
  sourceId?: string | null,
) {
  return useQuery({
    queryKey:
      workspaceId && collectionId && sourceId
        ? preparationKeys.intents(workspaceId, collectionId, sourceId)
        : [...preparationKeys.all, "intents", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !collectionId || !sourceId)
        throw new Error("workspaceId, collectionId and sourceId are required");
      return listPreparationIntents(workspaceId, collectionId, sourceId, 20, {
        signal,
      });
    },
    enabled: Boolean(workspaceId && collectionId && sourceId),
  });
}

export function useCreatePreparationIntentMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      sourceId,
      input,
      idempotencyKey,
    }: {
      sourceId: string;
      input: PreparationRequestInput;
      idempotencyKey?: string;
    }) => {
      if (!workspaceId || !collectionId)
        throw new Error("workspaceId and collectionId are required");
      return createPreparationIntent(
        workspaceId,
        collectionId,
        sourceId,
        input,
        idempotencyKey,
      );
    },
    onSuccess: (data, variables) => {
      if (workspaceId && collectionId) {
        void queryClient.invalidateQueries({
          queryKey: preparationKeys.intents(
            workspaceId,
            collectionId,
            variables.sourceId,
          ),
        });
        void queryClient.setQueryData(
          preparationKeys.intent(workspaceId, collectionId, data.intent.id),
          data.intent,
        );
      }
    },
  });
}

export function useCancelPreparationIntentMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (intentId: string) => {
      if (!workspaceId || !collectionId)
        throw new Error("workspaceId and collectionId are required");
      return cancelPreparationIntent(workspaceId, collectionId, intentId);
    },
    onSuccess: (data) => {
      if (workspaceId && collectionId) {
        void queryClient.setQueryData(
          preparationKeys.intent(workspaceId, collectionId, data.id),
          data,
        );
        void queryClient.invalidateQueries({
          queryKey: preparationKeys.intents(
            workspaceId,
            collectionId,
            data.source_id,
          ),
        });
      }
    },
  });
}
