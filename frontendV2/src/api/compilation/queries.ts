/**
 * TanStack Query hooks for Compilation domain.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  commitEdits,
  createEditPreview,
  getCompilationDraft,
  getCompilationMarkdown,
  getEditContext,
} from "./requests";
import type { EditCommitRequest, EditPreviewRequest } from "./types";

export const compilationKeys = {
  all: ["v1", "compilation"] as const,

  draft: (workspaceId: string, collectionId: string, runId: string) =>
    [
      ...compilationKeys.all,
      "draft",
      workspaceId,
      collectionId,
      runId,
    ] as const,

  markdown: (workspaceId: string, collectionId: string, runId: string) =>
    [
      ...compilationKeys.all,
      "markdown",
      workspaceId,
      collectionId,
      runId,
    ] as const,

  editContext: (workspaceId: string, collectionId: string, runId: string) =>
    [
      ...compilationKeys.all,
      "editContext",
      workspaceId,
      collectionId,
      runId,
    ] as const,
};

export function useCompilationDraftQuery(
  workspaceId?: string | null,
  collectionId?: string | null,
  runId?: string | null,
) {
  return useQuery({
    queryKey:
      workspaceId && collectionId && runId
        ? compilationKeys.draft(workspaceId, collectionId, runId)
        : [...compilationKeys.all, "draft", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !collectionId || !runId)
        throw new Error("workspaceId, collectionId and runId are required");
      return getCompilationDraft(workspaceId, collectionId, runId, { signal });
    },
    enabled: Boolean(workspaceId && collectionId && runId),
  });
}

export function useCompilationMarkdownQuery(
  workspaceId?: string | null,
  collectionId?: string | null,
  runId?: string | null,
) {
  return useQuery({
    queryKey:
      workspaceId && collectionId && runId
        ? compilationKeys.markdown(workspaceId, collectionId, runId)
        : [...compilationKeys.all, "markdown", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !collectionId || !runId)
        throw new Error("workspaceId, collectionId and runId are required");
      return getCompilationMarkdown(workspaceId, collectionId, runId, {
        signal,
      });
    },
    enabled: Boolean(workspaceId && collectionId && runId),
  });
}

export function useEditContextQuery(
  workspaceId?: string | null,
  collectionId?: string | null,
  runId?: string | null,
) {
  return useQuery({
    queryKey:
      workspaceId && collectionId && runId
        ? compilationKeys.editContext(workspaceId, collectionId, runId)
        : [...compilationKeys.all, "editContext", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !collectionId || !runId)
        throw new Error("workspaceId, collectionId and runId are required");
      return getEditContext(workspaceId, collectionId, runId, { signal });
    },
    enabled: Boolean(workspaceId && collectionId && runId),
  });
}

export function useCreateEditPreviewMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
) {
  return useMutation({
    mutationFn: ({
      runId,
      data,
    }: {
      runId: string;
      data: EditPreviewRequest;
    }) => {
      if (!workspaceId || !collectionId)
        throw new Error("workspaceId and collectionId are required");
      return createEditPreview(workspaceId, collectionId, runId, data);
    },
  });
}

export function useCommitEditsMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      runId,
      data,
      idempotencyKey,
    }: {
      runId: string;
      data: EditCommitRequest;
      idempotencyKey?: string;
    }) => {
      if (!workspaceId || !collectionId)
        throw new Error("workspaceId and collectionId are required");
      return commitEdits(
        workspaceId,
        collectionId,
        runId,
        data,
        idempotencyKey,
      );
    },
    onSuccess: (result) => {
      if (workspaceId && collectionId) {
        void queryClient.invalidateQueries({
          queryKey: [
            ...compilationKeys.all,
            "draft",
            workspaceId,
            collectionId,
            result.run.id,
          ],
        });
      }
    },
  });
}
