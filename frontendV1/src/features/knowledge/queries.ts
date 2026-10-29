import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import {
  addRevision,
  createCollection,
  createFolder,
  deleteFolder,
  downloadRevisionContent,
  getCollection,
  getFolder,
  getFolderImpact,
  getSource,
  listCollections,
  listFolders,
  listRevisions,
  listSources,
  moveFolder,
  moveSource,
  renameSource,
  restoreFolder,
  updateCollection,
  updateFolder,
  uploadSource,
} from "@/features/knowledge/requests";
import type {
  CollectionCreateInput,
  CollectionUpdateInput,
  FolderCreateInput,
  FolderImpact,
  FolderMoveInput,
  FolderUpdateInput,
  KBCollection,
  KBFolder,
  KBFolderDetail,
  KBRevision,
  KBSource,
  PageParams,
  PageResponse,
  SourceListParams,
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

  folders: (sessionId?: number, workspaceId?: string, collectionId?: string) =>
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
          "folders",
        ] as const)
      : (["v1", "knowledge", "folders"] as const),

  folder: (
    sessionId?: number,
    workspaceId?: string,
    collectionId?: string,
    folderId?: string,
  ) =>
    sessionId !== undefined &&
    workspaceId !== undefined &&
    collectionId !== undefined &&
    folderId !== undefined
      ? ([
          "v1",
          sessionId,
          "workspaces",
          workspaceId,
          "knowledge",
          "collections",
          collectionId,
          "folders",
          folderId,
        ] as const)
      : (["v1", "knowledge", "folder"] as const),

  folderImpact: (
    sessionId?: number,
    workspaceId?: string,
    collectionId?: string,
    folderId?: string,
  ) =>
    sessionId !== undefined &&
    workspaceId !== undefined &&
    collectionId !== undefined &&
    folderId !== undefined
      ? ([
          "v1",
          sessionId,
          "workspaces",
          workspaceId,
          "knowledge",
          "collections",
          collectionId,
          "folders",
          folderId,
          "impact",
        ] as const)
      : (["v1", "knowledge", "folderImpact"] as const),

  sources: (
    sessionId?: number,
    workspaceId?: string,
    collectionId?: string,
    params?: SourceListParams,
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
          params?.folderId ?? "root",
          Boolean(params?.allFolders),
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

export function useFoldersQuery(workspaceId: string, collectionId: string) {
  const { sessionId } = useV1Auth();
  return useQuery<KBFolder[]>({
    queryKey: knowledgeKeys.folders(sessionId, workspaceId, collectionId),
    queryFn: () => listFolders(v1Client, workspaceId, collectionId),
    enabled: Boolean(workspaceId && collectionId),
  });
}

export function useFolderQuery(
  workspaceId: string,
  collectionId: string,
  folderId: string,
) {
  const { sessionId } = useV1Auth();
  return useQuery<KBFolderDetail>({
    queryKey: knowledgeKeys.folder(
      sessionId,
      workspaceId,
      collectionId,
      folderId,
    ),
    queryFn: () => getFolder(v1Client, workspaceId, collectionId, folderId),
    enabled: Boolean(workspaceId && collectionId && folderId),
  });
}

export function useFolderImpactQuery(
  workspaceId: string,
  collectionId: string,
  folderId: string,
) {
  const { sessionId } = useV1Auth();
  return useQuery<FolderImpact>({
    queryKey: knowledgeKeys.folderImpact(
      sessionId,
      workspaceId,
      collectionId,
      folderId,
    ),
    queryFn: () =>
      getFolderImpact(v1Client, workspaceId, collectionId, folderId),
    enabled: Boolean(workspaceId && collectionId && folderId),
  });
}

export function useCreateFolder(workspaceId: string, collectionId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<KBFolder, Error, FolderCreateInput>({
    mutationFn: (input) =>
      createFolder(v1Client, workspaceId, collectionId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: knowledgeKeys.folders(sessionId, workspaceId, collectionId),
      });
    },
  });
}

export function useUpdateFolder(
  workspaceId: string,
  collectionId: string,
  folderId: string,
) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<KBFolder, Error, FolderUpdateInput>({
    mutationFn: (input) =>
      updateFolder(v1Client, workspaceId, collectionId, folderId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: knowledgeKeys.folders(sessionId, workspaceId, collectionId),
      });
      void queryClient.invalidateQueries({
        queryKey: knowledgeKeys.folder(
          sessionId,
          workspaceId,
          collectionId,
          folderId,
        ),
      });
    },
  });
}

export function useMoveFolder(
  workspaceId: string,
  collectionId: string,
  folderId: string,
) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<KBFolder, Error, FolderMoveInput>({
    mutationFn: (input) =>
      moveFolder(v1Client, workspaceId, collectionId, folderId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: knowledgeKeys.folders(sessionId, workspaceId, collectionId),
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

export function useDeleteFolder(workspaceId: string, collectionId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<FolderImpact, Error, string>({
    mutationFn: (folderId) =>
      deleteFolder(v1Client, workspaceId, collectionId, folderId),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: knowledgeKeys.folders(sessionId, workspaceId, collectionId),
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

export function useRestoreFolder(workspaceId: string, collectionId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<KBFolder, Error, string>({
    mutationFn: (folderId) =>
      restoreFolder(v1Client, workspaceId, collectionId, folderId),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: knowledgeKeys.folders(sessionId, workspaceId, collectionId),
      });
    },
  });
}

export function useSourcesQuery(
  workspaceId: string,
  collectionId: string,
  params: SourceListParams = {},
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
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? [];
      const hasActiveProcessing = items.some(
        (item) =>
          item.processing?.status === "queued" ||
          item.processing?.status === "running" ||
          item.processing?.dispatch_pending === true,
      );
      return hasActiveProcessing ? 3000 : false;
    },
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
    refetchInterval: (query) => {
      const proc = query.state.data?.processing;
      return proc?.status === "queued" ||
        proc?.status === "running" ||
        proc?.dispatch_pending === true
        ? 3000
        : false;
    },
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
    {
      file: File;
      title?: string;
      idempotencyKey?: string;
      folder_id?: string | null;
    }
  >({
    mutationFn: ({ file, title, idempotencyKey, folder_id }) =>
      uploadSource(
        v1Client,
        workspaceId,
        collectionId,
        file,
        title,
        idempotencyKey,
        folder_id,
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
        queryKey: knowledgeKeys.folders(sessionId, workspaceId, collectionId),
      });
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

export function useMoveSource(workspaceId: string, collectionId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<
    KBSource,
    Error,
    { sourceId: string; targetFolderId: string | null }
  >({
    mutationFn: ({ sourceId, targetFolderId }) =>
      moveSource(v1Client, workspaceId, collectionId, sourceId, targetFolderId),
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
        queryKey: knowledgeKeys.folders(sessionId, workspaceId, collectionId),
      });
    },
  });
}

export function useRenameSource(workspaceId: string, collectionId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<KBSource, Error, { sourceId: string; title: string }>({
    mutationFn: ({ sourceId, title }) =>
      renameSource(v1Client, workspaceId, collectionId, sourceId, title),
    onSuccess: (_, vars) => {
      void queryClient.invalidateQueries({
        queryKey: knowledgeKeys.source(
          sessionId,
          workspaceId,
          collectionId,
          vars.sourceId,
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
