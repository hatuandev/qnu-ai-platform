import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import {
  cancelPreparationIntent,
  createPreparationIntent,
  getPreparationIntent,
  listPreparationIntents,
} from "./preparation-requests";
import { isPreparationActive } from "./preparation-schemas";
import type {
  PreparationCreatedResponse,
  PreparationIntent,
  PreparationRequestInput,
} from "./preparation-types";
import { summaryKeys } from "./summary-queries";

const PREPARATION_POLL_MS = 2500;

export const preparationKeys = {
  root: (
    sessionId: number | undefined,
    workspaceId: string,
    collectionId: string,
    sourceId: string,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "sources",
      sourceId,
      "preparation-intents",
    ] as const,

  list: (
    sessionId: number | undefined,
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    limit: number,
  ) =>
    [
      ...preparationKeys.root(sessionId, workspaceId, collectionId, sourceId),
      "list",
      { limit },
    ] as const,

  intent: (
    sessionId: number | undefined,
    workspaceId: string,
    collectionId: string,
    intentId: string,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "preparation-intents",
      intentId,
    ] as const,
};

export function usePreparationIntentsQuery(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  limit = 20,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery<PreparationIntent[]>({
    queryKey: preparationKeys.list(
      sessionId,
      workspaceId,
      collectionId,
      sourceId,
      limit,
    ),
    queryFn: ({ signal }) =>
      listPreparationIntents(
        v1Client,
        workspaceId,
        collectionId,
        sourceId,
        limit,
        { signal },
      ),
    enabled:
      Boolean(workspaceId && collectionId && sourceId) &&
      (options?.enabled ?? true),
    refetchInterval: (query) =>
      (query.state.data ?? []).some(isPreparationActive)
        ? PREPARATION_POLL_MS
        : false,
  });
}

export function usePreparationIntentQuery(
  workspaceId: string,
  collectionId: string,
  intentId: string | null | undefined,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery<PreparationIntent>({
    queryKey: preparationKeys.intent(
      sessionId,
      workspaceId,
      collectionId,
      intentId ?? "",
    ),
    queryFn: ({ signal }) =>
      getPreparationIntent(
        v1Client,
        workspaceId,
        collectionId,
        intentId as string,
        { signal },
      ),
    enabled:
      Boolean(workspaceId && collectionId && intentId) &&
      (options?.enabled ?? true),
    refetchInterval: (query) =>
      isPreparationActive(query.state.data) ? PREPARATION_POLL_MS : false,
  });
}

export function useCreatePreparationIntentMutation(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<
    PreparationCreatedResponse,
    Error,
    { input: PreparationRequestInput; idempotencyKey: string }
  >({
    mutationFn: ({ input, idempotencyKey }) =>
      createPreparationIntent(
        v1Client,
        workspaceId,
        collectionId,
        sourceId,
        input,
        idempotencyKey,
      ),
    retry: 0,
    onSuccess: (data) => {
      queryClient.setQueryData(
        preparationKeys.intent(
          sessionId,
          workspaceId,
          collectionId,
          data.intent.id,
        ),
        data.intent,
      );
      void queryClient.invalidateQueries({
        queryKey: preparationKeys.root(
          sessionId,
          workspaceId,
          collectionId,
          sourceId,
        ),
      });
      void queryClient.invalidateQueries({
        queryKey: summaryKeys.sourceBase(
          sessionId,
          workspaceId,
          collectionId,
          sourceId,
        ),
      });
    },
  });
}

export function useCancelPreparationIntentMutation(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<PreparationIntent, Error, string>({
    mutationFn: (intentId) =>
      cancelPreparationIntent(v1Client, workspaceId, collectionId, intentId),
    retry: 0,
    onSuccess: (intent) => {
      queryClient.setQueryData(
        preparationKeys.intent(sessionId, workspaceId, collectionId, intent.id),
        intent,
      );
      void queryClient.invalidateQueries({
        queryKey: preparationKeys.root(
          sessionId,
          workspaceId,
          collectionId,
          sourceId,
        ),
      });
    },
  });
}
