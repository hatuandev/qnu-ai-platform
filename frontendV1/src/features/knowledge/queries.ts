import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import {
  addRevision,
  createCollection,
  downloadRevisionContent,
  getCollection,
  getSource,
  listCollections,
  listRevisions,
  listSources,
  updateCollection,
  uploadSource,
} from "@/features/knowledge/requests";
import type {
  CollectionCreateInput,
  CollectionUpdateInput,
  KBCollection,
  KBRevision,
  KBSource,
  PageParams,
  PageResponse,
  SourceUploadResult,
} from "@/features/knowledge/types";

export const knowledgeKeys = {
  all: (sessionId?: number, workspaceId?: string) =>
    sessionId !== undefined && workspaceId !== undefined
      ? (["v1", sessionId, "workspaces", workspaceId, "knowledge"] as const)
      : (["v1", "knowledge"] as const),

  collections: (
    sessionId?: number,
    workspaceId?: string,
    params?: PageParams,
  ) =>
    sessionId !== undefined && workspaceId !== undefined
      ? ([
          "v1",
          sessionId,
          "workspaces",
          workspaceId,
          "knowledge",
          "collections",
          params?.page ?? 1,
          params?.pageSize ?? 20,
        ] as const)
      : (["v1", "knowledge", "collections"] as const),

  collection: (
    sessionId?: number,
    workspaceId?: string,
    collectionId?: string,
  ) =>
    sessionId !== undefined &&
    workspaceId !== undefined &&
    collectionId !== undefined
      ? ([
          "v1",
          sessionId,
          "workspaces",
          workspaceId,
          "knowledge",
          "collections",
          collectionId,
        ] as const)
      : (["v1", "knowledge", "collection"] as const),

  sources: (
    sessionId?: number,
    workspaceId?: string,
    collectionId?: string,
    params?: PageParams,
  ) =>
    sessionId !== undefined &&
    workspaceId !== undefined &&
    collectionId !== undefined
      ? ([
          "v1",
          sessionId,
          "workspaces",
          workspaceId,
          "knowledge",
          "collections",
          collectionId,
          "sources",
          params?.page ?? 1,
          params?.pageSize ?? 20,
        ] as const)
      : (["v1", "knowledge", "sources"] as const),

  source: (
    sessionId?: number,
    workspaceId?: string,
    collectionId?: string,
    sourceId?: string,
  ) =>
    sessionId !== undefined &&
    workspaceId !== undefined &&
    collectionId !== undefined &&
    sourceId !== undefined
      ? ([
          "v1",
          sessionId,
          "workspaces",
          workspaceId,
          "knowledge",
          "collections",
          collectionId,
          "sources",
          sourceId,
        ] as const)
      : (["v1", "knowledge", "source"] as const),

  revisions: (
    sessionId?: number,
    workspaceId?: string,
    collectionId?: string,
    sourceId?: string,
  ) =>
    sessionId !== undefined &&
    workspaceId !== undefined &&
    collectionId !== undefined &&
    sourceId !== undefined
      ? ([
          "v1",
          sessionId,
          "workspaces",
          workspaceId,
          "knowledge",
          "collections",
          collectionId,
          "sources",
          sourceId,
          "revisions",
        ] as const)
      : (["v1", "knowledge", "revisions"] as const),
};

export function useCollectionsQuery(
  workspaceId: string,
  params: PageParams = {},
) {
  const { sessionId } = useV1Auth();
  return useQuery<PageResponse<KBCollection>>({
    queryKey: knowledgeKeys.collections(sessionId, workspaceId, params),
    queryFn: () => listCollections(v1Client, workspaceId, params),
    enabled: Boolean(workspaceId),
  });
}

export function useCollectionQuery(workspaceId: string, collectionId: string) {
  const { sessionId } = useV1Auth();
  return useQuery<KBCollection>({
    queryKey: knowledgeKeys.collection(sessionId, workspaceId, collectionId),
    queryFn: () => getCollection(v1Client, workspaceId, collectionId),
    enabled: Boolean(workspaceId && collectionId),
  });
}

export function useCreateCollection(workspaceId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<KBCollection, Error, CollectionCreateInput>({
    mutationFn: (input) => createCollection(v1Client, workspaceId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: [
          "v1",
          sessionId,
          "workspaces",
          workspaceId,
          "knowledge",
          "collections",
        ],
      });
    },
  });
}

export function useUpdateCollection(workspaceId: string, collectionId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<KBCollection, Error, CollectionUpdateInput>({
    mutationFn: (input) =>
      updateCollection(v1Client, workspaceId, collectionId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: knowledgeKeys.collection(
          sessionId,
          workspaceId,
          collectionId,
        ),
      });
      void queryClient.invalidateQueries({
        queryKey: [
          "v1",
          sessionId,
          "workspaces",
          workspaceId,
          "knowledge",
          "collections",
        ],
      });
    },
  });
}

export function useSourcesQuery(
  workspaceId: string,
  collectionId: string,
  params: PageParams = {},
) {
  const { sessionId } = useV1Auth();
  return useQuery<PageResponse<KBSource>>({
    queryKey: knowledgeKeys.sources(
      sessionId,
      workspaceId,
      collectionId,
      params,
    ),
    queryFn: () => listSources(v1Client, workspaceId, collectionId, params),
    enabled: Boolean(workspaceId && collectionId),
  });
}

export function useSourceQuery(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
) {
  const { sessionId } = useV1Auth();
  return useQuery<KBSource>({
    queryKey: knowledgeKeys.source(
      sessionId,
      workspaceId,
      collectionId,
      sourceId,
    ),
    queryFn: () => getSource(v1Client, workspaceId, collectionId, sourceId),
    enabled: Boolean(workspaceId && collectionId && sourceId),
  });
}

export function useRevisionsQuery(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
) {
  const { sessionId } = useV1Auth();
  return useQuery<KBRevision[]>({
    queryKey: knowledgeKeys.revisions(
      sessionId,
      workspaceId,
      collectionId,
      sourceId,
    ),
    queryFn: () => listRevisions(v1Client, workspaceId, collectionId, sourceId),
    enabled: Boolean(workspaceId && collectionId && sourceId),
  });
}

export function useUploadSource(workspaceId: string, collectionId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<
    SourceUploadResult,
    Error,
    { file: File; title?: string; idempotencyKey?: string }
  >({
    mutationFn: ({ file, title, idempotencyKey }) =>
      uploadSource(
        v1Client,
        workspaceId,
        collectionId,
        file,
        title,
        idempotencyKey,
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: [
          "v1",
          sessionId,
          "workspaces",
          workspaceId,
          "knowledge",
          "collections",
          collectionId,
          "sources",
        ],
      });
      void queryClient.invalidateQueries({
        queryKey: knowledgeKeys.collection(
          sessionId,
          workspaceId,
          collectionId,
        ),
      });
    },
  });
}

export function useAddRevision(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<
    SourceUploadResult,
    Error,
    { file: File; idempotencyKey?: string; staged?: boolean }
  >({
    mutationFn: ({ file, idempotencyKey, staged }) =>
      addRevision(
        v1Client,
        workspaceId,
        collectionId,
        sourceId,
        file,
        idempotencyKey,
        staged,
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: knowledgeKeys.revisions(
          sessionId,
          workspaceId,
          collectionId,
          sourceId,
        ),
      });
      void queryClient.invalidateQueries({
        queryKey: knowledgeKeys.source(
          sessionId,
          workspaceId,
          collectionId,
          sourceId,
        ),
      });
      void queryClient.invalidateQueries({
        queryKey: [
          "v1",
          sessionId,
          "workspaces",
          workspaceId,
          "knowledge",
          "collections",
          collectionId,
          "sources",
        ],
      });
    },
  });
}

export function downloadSourceRevision(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
) {
  return downloadRevisionContent(
    v1Client,
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
  );
}
