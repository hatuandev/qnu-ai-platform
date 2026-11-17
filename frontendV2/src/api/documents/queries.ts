/**
 * TanStack Query hooks for Compiled Documents and Publication domain.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  commitDecision,
  createCompiledDocument,
  createDecisionPreview,
  getCompiledVersion,
  getDocumentSummary,
  getRegistrationMetadata,
  getReviewGate,
  listCompiledDocuments,
  registerCompiledDocumentVersion,
} from "./requests";
import type {
  CreateDocumentRequest,
  DecisionCommitRequest,
  DecisionPreviewRequest,
  RegisterVersionRequest,
} from "./types";

export const documentKeys = {
  all: ["v1", "documents"] as const,

  list: (workspaceId: string, collectionId: string) =>
    [...documentKeys.all, "list", workspaceId, collectionId] as const,

  summary: (workspaceId: string, collectionId: string, documentId: string) =>
    [
      ...documentKeys.all,
      "summary",
      workspaceId,
      collectionId,
      documentId,
    ] as const,

  reviewGate: (
    workspaceId: string,
    collectionId: string,
    documentId: string,
    versionId: string,
  ) =>
    [
      ...documentKeys.all,
      "reviewGate",
      workspaceId,
      collectionId,
      documentId,
      versionId,
    ] as const,
};

export function useCompiledDocumentsQuery(
  workspaceId?: string | null,
  collectionId?: string | null,
) {
  return useQuery({
    queryKey:
      workspaceId && collectionId
        ? documentKeys.list(workspaceId, collectionId)
        : [...documentKeys.all, "list", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !collectionId)
        throw new Error("workspaceId and collectionId are required");
      return listCompiledDocuments(workspaceId, collectionId, { signal });
    },
    enabled: Boolean(workspaceId && collectionId),
  });
}

export function useReviewGateQuery(
  workspaceId?: string | null,
  collectionId?: string | null,
  documentId?: string | null,
  versionId?: string | null,
) {
  return useQuery({
    queryKey:
      workspaceId && collectionId && documentId && versionId
        ? documentKeys.reviewGate(
            workspaceId,
            collectionId,
            documentId,
            versionId,
          )
        : [...documentKeys.all, "reviewGate", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !collectionId || !documentId || !versionId)
        throw new Error(
          "workspaceId, collectionId, documentId and versionId are required",
        );
      return getReviewGate(workspaceId, collectionId, documentId, versionId, {
        signal,
      });
    },
    enabled: Boolean(workspaceId && collectionId && documentId && versionId),
    retry: false,
  });
}

export function useDocumentSummaryQuery(
  workspaceId?: string | null,
  collectionId?: string | null,
  documentId?: string | null,
) {
  return useQuery({
    queryKey:
      workspaceId && collectionId && documentId
        ? documentKeys.summary(workspaceId, collectionId, documentId)
        : [...documentKeys.all, "summary", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !collectionId || !documentId)
        throw new Error(
          "workspaceId, collectionId and documentId are required",
        );
      return getDocumentSummary(workspaceId, collectionId, documentId, {
        signal,
      });
    },
    enabled: Boolean(workspaceId && collectionId && documentId),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      // Auto-poll when published but index is not ready yet
      const isPublishing =
        data.published_version?.status === "published" &&
        (!data.serving_matches_published || data.readiness.status !== "ready");
      return isPublishing ? 3000 : false;
    },
  });
}

export function useRegistrationMetadataQuery(
  workspaceId: string,
  collectionId: string,
  runId: string | null,
  enabled: boolean,
) {
  return useQuery({
    queryKey: [
      ...documentKeys.all,
      "registrationMetadata",
      workspaceId,
      collectionId,
      runId,
    ],
    queryFn: ({ signal }) => {
      if (!runId) throw new Error("runId is required");
      return getRegistrationMetadata(workspaceId, collectionId, runId, {
        signal,
      });
    },
    enabled: Boolean(workspaceId && collectionId && runId && enabled),
    retry: false,
    refetchOnWindowFocus: false,
  });
}

export function useCreateCompiledDocumentMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      data,
      idempotencyKey,
    }: {
      data: CreateDocumentRequest;
      idempotencyKey?: string;
    }) => {
      if (!workspaceId || !collectionId)
        throw new Error("workspaceId and collectionId are required");
      return createCompiledDocument(
        workspaceId,
        collectionId,
        data,
        idempotencyKey,
      );
    },
    onSuccess: () => {
      if (workspaceId && collectionId) {
        void queryClient.invalidateQueries({
          queryKey: documentKeys.list(workspaceId, collectionId),
        });
      }
    },
  });
}

export function useRegisterCompiledDocumentVersionMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      documentId,
      data,
      idempotencyKey,
    }: {
      documentId: string;
      data: RegisterVersionRequest;
      idempotencyKey?: string;
    }) => {
      if (!workspaceId || !collectionId)
        throw new Error("workspaceId and collectionId are required");
      return registerCompiledDocumentVersion(
        workspaceId,
        collectionId,
        documentId,
        data,
        idempotencyKey,
      );
    },
    onSuccess: (_data, variables) => {
      if (workspaceId && collectionId) {
        void queryClient.invalidateQueries({
          queryKey: documentKeys.summary(
            workspaceId,
            collectionId,
            variables.documentId,
          ),
        });
      }
    },
  });
}

export function useDecisionPreviewMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
) {
  return useMutation({
    mutationFn: ({
      documentId,
      versionId,
      data,
    }: {
      documentId: string;
      versionId: string;
      data: DecisionPreviewRequest;
    }) => {
      if (!workspaceId || !collectionId)
        throw new Error("workspaceId and collectionId are required");
      return createDecisionPreview(
        workspaceId,
        collectionId,
        documentId,
        versionId,
        data,
      );
    },
  });
}

export function useCommitDecisionMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      documentId,
      versionId,
      data,
      idempotencyKey,
    }: {
      documentId: string;
      versionId: string;
      data: DecisionCommitRequest;
      idempotencyKey?: string;
    }) => {
      if (!workspaceId || !collectionId)
        throw new Error("workspaceId and collectionId are required");
      return commitDecision(
        workspaceId,
        collectionId,
        documentId,
        versionId,
        data,
        idempotencyKey,
      );
    },
    onSuccess: (_data, variables) => {
      if (workspaceId && collectionId) {
        void queryClient.invalidateQueries({
          queryKey: documentKeys.summary(
            workspaceId,
            collectionId,
            variables.documentId,
          ),
        });
        void queryClient.invalidateQueries({
          queryKey: documentKeys.list(workspaceId, collectionId),
        });
      }
    },
  });
}

export function useCompiledVersionQuery(
  workspaceId: string,
  collectionId: string,
  documentId: string | null,
  versionId: string | null,
) {
  return useQuery({
    queryKey: [
      ...documentKeys.all,
      "version",
      workspaceId,
      collectionId,
      documentId,
      versionId,
    ],
    queryFn: ({ signal }) => {
      if (!documentId || !versionId)
        throw new Error("documentId and versionId are required");
      return getCompiledVersion(
        workspaceId,
        collectionId,
        documentId,
        versionId,
        { signal },
      );
    },
    enabled: Boolean(workspaceId && collectionId && documentId && versionId),
    retry: false,
    refetchOnWindowFocus: false,
  });
}
