import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import type { DraftDocumentResponse } from "./compilation-types.ts";
import { readArrayPage } from "./list-pagination";
import {
  commitDecision,
  createCompiledDocument,
  createCompiledVersion,
  createDecisionPreview,
  getCompiledDocument,
  getCompiledDocumentHistory,
  getCompiledVersion,
  getCompiledVersionDraft,
  getCompiledVersionReviewGate,
  getPublishedCompiledDocument,
  listCompiledDocuments,
  listCompiledVersions,
} from "./publication-requests.ts";
import type {
  CreateDocumentRequest,
  DecisionCommitRequest,
  DecisionPreviewRequest,
  DecisionPreviewResponse,
  DecisionResponse,
  DocumentResponse,
  PublishedResponse,
  RegisterVersionRequest,
  RegistrationResponse,
  ReviewGateResponse,
  VersionResponse,
} from "./publication-types.ts";

// ==========================================
// Scoped Query Keys
// ==========================================

export const publicationKeys = {
  all: (sessionId?: number) => ["v1", sessionId, "compiled-documents"] as const,

  documents: (
    workspaceId: string,
    collectionId: string,
    params?: { limit?: number; offset?: number },
    sessionId?: number,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "compiled-documents",
      params ?? {},
    ] as const,

  document: (
    workspaceId: string,
    collectionId: string,
    documentId: string,
    sessionId?: number,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "compiled-documents",
      documentId,
    ] as const,

  versions: (
    workspaceId: string,
    collectionId: string,
    documentId: string,
    params?: { limit?: number; offset?: number },
    sessionId?: number,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "compiled-documents",
      documentId,
      "versions",
      params ?? {},
    ] as const,

  version: (
    workspaceId: string,
    collectionId: string,
    documentId: string,
    versionId: string,
    sessionId?: number,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "compiled-documents",
      documentId,
      "versions",
      versionId,
    ] as const,

  versionDraft: (
    workspaceId: string,
    collectionId: string,
    documentId: string,
    versionId: string,
    sessionId?: number,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "compiled-documents",
      documentId,
      "versions",
      versionId,
      "draft",
    ] as const,

  versionReviewGate: (
    workspaceId: string,
    collectionId: string,
    documentId: string,
    versionId: string,
    sessionId?: number,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "compiled-documents",
      documentId,
      "versions",
      versionId,
      "review-gate",
    ] as const,

  published: (
    workspaceId: string,
    collectionId: string,
    documentId: string,
    sessionId?: number,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "compiled-documents",
      documentId,
      "published",
    ] as const,

  history: (
    workspaceId: string,
    collectionId: string,
    documentId: string,
    params?: { limit?: number; offset?: number },
    sessionId?: number,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "compiled-documents",
      documentId,
      "history",
      params ?? {},
    ] as const,
};

// ==========================================
// Query Hooks
// ==========================================

export function useCompiledDocumentsQuery(
  workspaceId: string,
  collectionId: string,
  limit = 50,
  offset = 0,
  options?: { enabled?: boolean; lookahead?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery<DocumentResponse[]>({
    queryKey: [
      ...publicationKeys.documents(
        workspaceId,
        collectionId,
        { limit, offset },
        sessionId,
      ),
      { lookahead: options?.lookahead ?? false },
    ],
    queryFn: ({ signal }) => {
      const loadRows = (count: number, start: number) =>
        listCompiledDocuments(
          v1Client,
          workspaceId,
          collectionId,
          count,
          start,
          { signal },
        );
      return options?.lookahead
        ? readArrayPage(loadRows, limit, offset)
        : loadRows(limit, offset);
    },
    enabled: Boolean(workspaceId && collectionId) && (options?.enabled ?? true),
  });
}

export function useCompiledDocumentQuery(
  workspaceId: string,
  collectionId: string,
  documentId: string | null | undefined,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery<DocumentResponse>({
    queryKey: publicationKeys.document(
      workspaceId,
      collectionId,
      documentId ?? "",
      sessionId,
    ),
    queryFn: ({ signal }) => {
      if (!documentId) throw new Error("documentId is required");
      return getCompiledDocument(
        v1Client,
        workspaceId,
        collectionId,
        documentId,
        {
          signal,
        },
      );
    },
    enabled:
      Boolean(workspaceId && collectionId && documentId) &&
      (options?.enabled ?? true),
  });
}

export function useCompiledVersionsQuery(
  workspaceId: string,
  collectionId: string,
  documentId: string | null | undefined,
  limit = 50,
  offset = 0,
  options?: { enabled?: boolean; lookahead?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery<VersionResponse[]>({
    queryKey: [
      ...publicationKeys.versions(
        workspaceId,
        collectionId,
        documentId ?? "",
        { limit, offset },
        sessionId,
      ),
      { lookahead: options?.lookahead ?? false },
    ],
    queryFn: ({ signal }) => {
      if (!documentId) throw new Error("documentId is required");
      const loadRows = (count: number, start: number) =>
        listCompiledVersions(
          v1Client,
          workspaceId,
          collectionId,
          documentId,
          count,
          start,
          { signal },
        );
      return options?.lookahead
        ? readArrayPage(loadRows, limit, offset)
        : loadRows(limit, offset);
    },
    enabled:
      Boolean(workspaceId && collectionId && documentId) &&
      (options?.enabled ?? true),
  });
}

export function useCompiledVersionQuery(
  workspaceId: string,
  collectionId: string,
  documentId: string | null | undefined,
  versionId: string | null | undefined,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery<VersionResponse>({
    queryKey: publicationKeys.version(
      workspaceId,
      collectionId,
      documentId ?? "",
      versionId ?? "",
      sessionId,
    ),
    queryFn: ({ signal }) => {
      if (!documentId || !versionId)
        throw new Error("documentId and versionId are required");
      return getCompiledVersion(
        v1Client,
        workspaceId,
        collectionId,
        documentId,
        versionId,
        { signal },
      );
    },
    enabled:
      Boolean(workspaceId && collectionId && documentId && versionId) &&
      (options?.enabled ?? true),
  });
}

export function useCompiledVersionDraftQuery(
  workspaceId: string,
  collectionId: string,
  documentId: string | null | undefined,
  versionId: string | null | undefined,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery<DraftDocumentResponse>({
    queryKey: publicationKeys.versionDraft(
      workspaceId,
      collectionId,
      documentId ?? "",
      versionId ?? "",
      sessionId,
    ),
    queryFn: ({ signal }) => {
      if (!documentId || !versionId)
        throw new Error("documentId and versionId are required");
      return getCompiledVersionDraft(
        v1Client,
        workspaceId,
        collectionId,
        documentId,
        versionId,
        { signal },
      );
    },
    enabled:
      Boolean(workspaceId && collectionId && documentId && versionId) &&
      (options?.enabled ?? true),
  });
}

export function useCompiledVersionReviewGateQuery(
  workspaceId: string,
  collectionId: string,
  documentId: string | null | undefined,
  versionId: string | null | undefined,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery<ReviewGateResponse>({
    queryKey: publicationKeys.versionReviewGate(
      workspaceId,
      collectionId,
      documentId ?? "",
      versionId ?? "",
      sessionId,
    ),
    queryFn: ({ signal }) => {
      if (!documentId || !versionId)
        throw new Error("documentId and versionId are required");
      return getCompiledVersionReviewGate(
        v1Client,
        workspaceId,
        collectionId,
        documentId,
        versionId,
        { signal },
      );
    },
    enabled:
      Boolean(workspaceId && collectionId && documentId && versionId) &&
      (options?.enabled ?? true),
  });
}

export function usePublishedCompiledDocumentQuery(
  workspaceId: string,
  collectionId: string,
  documentId: string | null | undefined,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery<PublishedResponse | null>({
    queryKey: publicationKeys.published(
      workspaceId,
      collectionId,
      documentId ?? "",
      sessionId,
    ),
    queryFn: ({ signal }) => {
      if (!documentId) throw new Error("documentId is required");
      return getPublishedCompiledDocument(
        v1Client,
        workspaceId,
        collectionId,
        documentId,
        { signal },
      );
    },
    enabled:
      Boolean(workspaceId && collectionId && documentId) &&
      (options?.enabled ?? true),
  });
}

export function useCompiledDocumentHistoryQuery(
  workspaceId: string,
  collectionId: string,
  documentId: string | null | undefined,
  limit = 50,
  offset = 0,
  options?: { enabled?: boolean; lookahead?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery<DecisionResponse[]>({
    queryKey: [
      ...publicationKeys.history(
        workspaceId,
        collectionId,
        documentId ?? "",
        { limit, offset },
        sessionId,
      ),
      { lookahead: options?.lookahead ?? false },
    ],
    queryFn: ({ signal }) => {
      if (!documentId) throw new Error("documentId is required");
      const loadRows = (count: number, start: number) =>
        getCompiledDocumentHistory(
          v1Client,
          workspaceId,
          collectionId,
          documentId,
          count,
          start,
          { signal },
        );
      return options?.lookahead
        ? readArrayPage(loadRows, limit, offset)
        : loadRows(limit, offset);
    },
    enabled:
      Boolean(workspaceId && collectionId && documentId) &&
      (options?.enabled ?? true),
  });
}

// ==========================================
// Mutation Hooks (retry: 0 for single submit)
// ==========================================

export function useCreateCompiledDocumentMutation(
  workspaceId: string,
  collectionId: string,
) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<
    RegistrationResponse,
    Error,
    { input: CreateDocumentRequest; idempotencyKey: string }
  >({
    mutationFn: ({ input, idempotencyKey }) =>
      createCompiledDocument(
        v1Client,
        workspaceId,
        collectionId,
        input,
        idempotencyKey,
      ),
    retry: 0,
    onSuccess: (data) => {
      void queryClient.invalidateQueries({
        queryKey: publicationKeys.documents(
          workspaceId,
          collectionId,
          undefined,
          sessionId,
        ),
      });
      if (data.document?.id) {
        queryClient.setQueryData(
          publicationKeys.document(
            workspaceId,
            collectionId,
            data.document.id,
            sessionId,
          ),
          data.document,
        );
      }
    },
  });
}

export function useCreateCompiledVersionMutation(
  workspaceId: string,
  collectionId: string,
  documentId: string,
) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<
    RegistrationResponse,
    Error,
    { input: RegisterVersionRequest; idempotencyKey: string }
  >({
    mutationFn: ({ input, idempotencyKey }) =>
      createCompiledVersion(
        v1Client,
        workspaceId,
        collectionId,
        documentId,
        input,
        idempotencyKey,
      ),
    retry: 0,
    onSuccess: (data) => {
      void queryClient.invalidateQueries({
        queryKey: publicationKeys.versions(
          workspaceId,
          collectionId,
          documentId,
          undefined,
          sessionId,
        ),
      });
      void queryClient.invalidateQueries({
        queryKey: publicationKeys.document(
          workspaceId,
          collectionId,
          documentId,
          sessionId,
        ),
      });
      if (data.version?.id) {
        queryClient.setQueryData(
          publicationKeys.version(
            workspaceId,
            collectionId,
            documentId,
            data.version.id,
            sessionId,
          ),
          data.version,
        );
      }
    },
  });
}

export function useDecisionPreviewMutation(
  workspaceId: string,
  collectionId: string,
  documentId: string,
  versionId: string,
) {
  return useMutation<
    DecisionPreviewResponse,
    Error,
    { input: DecisionPreviewRequest }
  >({
    mutationFn: ({ input }) =>
      createDecisionPreview(
        v1Client,
        workspaceId,
        collectionId,
        documentId,
        versionId,
        input,
      ),
    retry: 0,
  });
}

export function useCommitDecisionMutation(
  workspaceId: string,
  collectionId: string,
  documentId: string,
  versionId: string,
) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<
    DecisionResponse,
    Error,
    { input: DecisionCommitRequest; idempotencyKey: string }
  >({
    mutationFn: ({ input, idempotencyKey }) =>
      commitDecision(
        v1Client,
        workspaceId,
        collectionId,
        documentId,
        versionId,
        input,
        idempotencyKey,
      ),
    retry: 0,
    onSuccess: () => {
      // Invalidate versions, version detail, published, and history
      void queryClient.invalidateQueries({
        queryKey: publicationKeys.versions(
          workspaceId,
          collectionId,
          documentId,
          undefined,
          sessionId,
        ),
      });
      void queryClient.invalidateQueries({
        queryKey: publicationKeys.version(
          workspaceId,
          collectionId,
          documentId,
          versionId,
          sessionId,
        ),
      });
      void queryClient.invalidateQueries({
        queryKey: publicationKeys.published(
          workspaceId,
          collectionId,
          documentId,
          sessionId,
        ),
      });
      void queryClient.invalidateQueries({
        queryKey: publicationKeys.history(
          workspaceId,
          collectionId,
          documentId,
          undefined,
          sessionId,
        ),
      });
      void queryClient.invalidateQueries({
        queryKey: publicationKeys.document(
          workspaceId,
          collectionId,
          documentId,
          sessionId,
        ),
      });
    },
  });
}
