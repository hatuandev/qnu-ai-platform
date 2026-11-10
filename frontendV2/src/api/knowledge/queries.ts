/**
 * TanStack Query hooks for Knowledge domain.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { PageParams } from "../workspaces/types";
import {
  createCollection,
  createFolder,
  deleteFolder,
  getCollection,
  getFolder,
  getSource,
  getSourceSummary,
  listCollections,
  listFolders,
  listRevisions,
  listSources,
  moveFolder,
  moveSource,
  renameSource,
  updateCollection,
  updateFolder,
  uploadSource,
} from "./requests";
import type {
  CollectionCreateRequest,
  CollectionUpdateRequest,
  FolderCreateRequest,
  FolderMoveRequest,
  FolderUpdateRequest,
  SourceListParams,
  SourceMoveRequest,
  SourceRenameRequest,
} from "./types";

export const knowledgeKeys = {
  all: ["v1", "knowledge"] as const,

  collections: (workspaceId: string, params?: Partial<PageParams>) =>
    [
      ...knowledgeKeys.all,
      "collections",
      workspaceId,
      params?.page ?? 1,
      params?.pageSize ?? 50,
    ] as const,

  collection: (workspaceId: string, collectionId: string) =>
    [...knowledgeKeys.all, "collection", workspaceId, collectionId] as const,

  folders: (workspaceId: string, collectionId: string) =>
    [...knowledgeKeys.all, "folders", workspaceId, collectionId] as const,

  folder: (workspaceId: string, collectionId: string, folderId: string) =>
    [
      ...knowledgeKeys.all,
      "folder",
      workspaceId,
      collectionId,
      folderId,
    ] as const,

  sources: (
    workspaceId: string,
    collectionId: string,
    params?: SourceListParams,
  ) =>
    [
      ...knowledgeKeys.all,
      "sources",
      workspaceId,
      collectionId,
      params?.folderId ?? "root",
      Boolean(params?.allFolders),
      params?.page ?? 1,
      params?.pageSize ?? 20,
    ] as const,

  source: (workspaceId: string, collectionId: string, sourceId: string) =>
    [
      ...knowledgeKeys.all,
      "source",
      workspaceId,
      collectionId,
      sourceId,
    ] as const,

  sourceSummary: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
  ) =>
    [
      ...knowledgeKeys.all,
      "sourceSummary",
      workspaceId,
      collectionId,
      sourceId,
    ] as const,

  revisions: (workspaceId: string, collectionId: string, sourceId: string) =>
    [
      ...knowledgeKeys.all,
      "revisions",
      workspaceId,
      collectionId,
      sourceId,
    ] as const,
};

// ==========================================
// Collection Hooks
// ==========================================

export function useCollectionsQuery(
  workspaceId?: string | null,
  params?: Partial<PageParams>,
) {
  return useQuery({
    queryKey: workspaceId
      ? knowledgeKeys.collections(workspaceId, params)
      : [...knowledgeKeys.all, "collections", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return listCollections(workspaceId, params, { signal });
    },
    enabled: Boolean(workspaceId),
  });
}

export function useCollectionQuery(
  workspaceId?: string | null,
  collectionId?: string | null,
) {
  return useQuery({
    queryKey:
      workspaceId && collectionId
        ? knowledgeKeys.collection(workspaceId, collectionId)
        : [...knowledgeKeys.all, "collection", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !collectionId)
        throw new Error("workspaceId and collectionId are required");
      return getCollection(workspaceId, collectionId, { signal });
    },
    enabled: Boolean(workspaceId && collectionId),
  });
}

export function useCreateCollectionMutation(workspaceId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CollectionCreateRequest) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return createCollection(workspaceId, data);
    },
    onSuccess: () => {
      if (workspaceId) {
        void queryClient.invalidateQueries({
          queryKey: [...knowledgeKeys.all, "collections", workspaceId],
        });
      }
    },
  });
}

export function useUpdateCollectionMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CollectionUpdateRequest) => {
      if (!workspaceId || !collectionId)
        throw new Error("workspaceId and collectionId are required");
      return updateCollection(workspaceId, collectionId, data);
    },
    onSuccess: () => {
      if (workspaceId && collectionId) {
        void queryClient.invalidateQueries({
          queryKey: knowledgeKeys.collection(workspaceId, collectionId),
        });
        void queryClient.invalidateQueries({
          queryKey: [...knowledgeKeys.all, "collections", workspaceId],
        });
      }
    },
  });
}

// ==========================================
// Folder Hooks
// ==========================================

export function useFoldersQuery(
  workspaceId?: string | null,
  collectionId?: string | null,
) {
  return useQuery({
    queryKey:
      workspaceId && collectionId
        ? knowledgeKeys.folders(workspaceId, collectionId)
        : [...knowledgeKeys.all, "folders", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !collectionId)
        throw new Error("workspaceId and collectionId are required");
      return listFolders(workspaceId, collectionId, { signal });
    },
    enabled: Boolean(workspaceId && collectionId),
  });
}

export function useFolderDetailQuery(
  workspaceId?: string | null,
  collectionId?: string | null,
  folderId?: string | null,
) {
  return useQuery({
    queryKey:
      workspaceId && collectionId && folderId
        ? knowledgeKeys.folder(workspaceId, collectionId, folderId)
        : [...knowledgeKeys.all, "folder", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !collectionId || !folderId)
        throw new Error("workspaceId, collectionId and folderId are required");
      return getFolder(workspaceId, collectionId, folderId, { signal });
    },
    enabled: Boolean(workspaceId && collectionId && folderId),
  });
}

export function useCreateFolderMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: FolderCreateRequest) => {
      if (!workspaceId || !collectionId)
        throw new Error("workspaceId and collectionId are required");
      return createFolder(workspaceId, collectionId, data);
    },
    onSuccess: () => {
      if (workspaceId && collectionId) {
        void queryClient.invalidateQueries({
          queryKey: knowledgeKeys.folders(workspaceId, collectionId),
        });
      }
    },
  });
}

export function useUpdateFolderMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      folderId,
      data,
    }: {
      folderId: string;
      data: FolderUpdateRequest;
    }) => {
      if (!workspaceId || !collectionId)
        throw new Error("workspaceId and collectionId are required");
      return updateFolder(workspaceId, collectionId, folderId, data);
    },
    onSuccess: () => {
      if (workspaceId && collectionId) {
        void queryClient.invalidateQueries({
          queryKey: knowledgeKeys.folders(workspaceId, collectionId),
        });
      }
    },
  });
}

export function useMoveFolderMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      folderId,
      data,
    }: {
      folderId: string;
      data: FolderMoveRequest;
    }) => {
      if (!workspaceId || !collectionId)
        throw new Error("workspaceId and collectionId are required");
      return moveFolder(workspaceId, collectionId, folderId, data);
    },
    onSuccess: () => {
      if (workspaceId && collectionId) {
        void queryClient.invalidateQueries({
          queryKey: knowledgeKeys.folders(workspaceId, collectionId),
        });
      }
    },
  });
}

export function useDeleteFolderMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (folderId: string) => {
      if (!workspaceId || !collectionId)
        throw new Error("workspaceId and collectionId are required");
      return deleteFolder(workspaceId, collectionId, folderId);
    },
    onSuccess: () => {
      if (workspaceId && collectionId) {
        void queryClient.invalidateQueries({
          queryKey: knowledgeKeys.folders(workspaceId, collectionId),
        });
      }
    },
  });
}

// ==========================================
// Source Hooks
// ==========================================

export function useSourcesQuery(
  workspaceId?: string | null,
  collectionId?: string | null,
  params?: SourceListParams,
) {
  return useQuery({
    queryKey:
      workspaceId && collectionId
        ? knowledgeKeys.sources(workspaceId, collectionId, params)
        : [...knowledgeKeys.all, "sources", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !collectionId)
        throw new Error("workspaceId and collectionId are required");
      return listSources(workspaceId, collectionId, params, { signal });
    },
    enabled: Boolean(workspaceId && collectionId),
  });
}

export function useSourceQuery(
  workspaceId?: string | null,
  collectionId?: string | null,
  sourceId?: string | null,
) {
  return useQuery({
    queryKey:
      workspaceId && collectionId && sourceId
        ? knowledgeKeys.source(workspaceId, collectionId, sourceId)
        : [...knowledgeKeys.all, "source", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !collectionId || !sourceId)
        throw new Error("workspaceId, collectionId and sourceId are required");
      return getSource(workspaceId, collectionId, sourceId, { signal });
    },
    enabled: Boolean(workspaceId && collectionId && sourceId),
  });
}

export function useSourceSummaryQuery(
  workspaceId?: string | null,
  collectionId?: string | null,
  sourceId?: string | null,
) {
  return useQuery({
    queryKey:
      workspaceId && collectionId && sourceId
        ? knowledgeKeys.sourceSummary(workspaceId, collectionId, sourceId)
        : [...knowledgeKeys.all, "sourceSummary", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !collectionId || !sourceId)
        throw new Error("workspaceId, collectionId and sourceId are required");
      return getSourceSummary(workspaceId, collectionId, sourceId, { signal });
    },
    enabled: Boolean(workspaceId && collectionId && sourceId),
    refetchInterval: (query) => {
      const data = query.state.data;
      // Auto-poll if intent or processing is active
      const isPreparing =
        data?.preparation?.status === "queued" ||
        data?.preparation?.status === "waiting_ocr" ||
        data?.preparation?.status === "compiling";
      return isPreparing ? 3000 : false;
    },
  });
}

export function useRevisionsQuery(
  workspaceId?: string | null,
  collectionId?: string | null,
  sourceId?: string | null,
) {
  return useQuery({
    queryKey:
      workspaceId && collectionId && sourceId
        ? knowledgeKeys.revisions(workspaceId, collectionId, sourceId)
        : [...knowledgeKeys.all, "revisions", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !collectionId || !sourceId)
        throw new Error("workspaceId, collectionId and sourceId are required");
      return listRevisions(workspaceId, collectionId, sourceId, { signal });
    },
    enabled: Boolean(workspaceId && collectionId && sourceId),
  });
}

export function useUploadSourceMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      formData,
      idempotencyKey,
    }: {
      formData: FormData;
      idempotencyKey?: string;
    }) => {
      if (!workspaceId || !collectionId)
        throw new Error("workspaceId and collectionId are required");
      return uploadSource(workspaceId, collectionId, formData, idempotencyKey);
    },
    onSuccess: () => {
      if (workspaceId && collectionId) {
        void queryClient.invalidateQueries({
          queryKey: [
            ...knowledgeKeys.all,
            "sources",
            workspaceId,
            collectionId,
          ],
        });
        void queryClient.invalidateQueries({
          queryKey: knowledgeKeys.collection(workspaceId, collectionId),
        });
        void queryClient.invalidateQueries({
          queryKey: knowledgeKeys.folders(workspaceId, collectionId),
        });
      }
    },
  });
}

export function useRenameSourceMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      sourceId,
      data,
    }: {
      sourceId: string;
      data: SourceRenameRequest;
    }) => {
      if (!workspaceId || !collectionId)
        throw new Error("workspaceId and collectionId are required");
      return renameSource(workspaceId, collectionId, sourceId, data);
    },
    onSuccess: (_data, variables) => {
      if (workspaceId && collectionId) {
        void queryClient.invalidateQueries({
          queryKey: knowledgeKeys.source(
            workspaceId,
            collectionId,
            variables.sourceId,
          ),
        });
        void queryClient.invalidateQueries({
          queryKey: [
            ...knowledgeKeys.all,
            "sources",
            workspaceId,
            collectionId,
          ],
        });
      }
    },
  });
}

export function useMoveSourceMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      sourceId,
      data,
    }: {
      sourceId: string;
      data: SourceMoveRequest;
    }) => {
      if (!workspaceId || !collectionId)
        throw new Error("workspaceId and collectionId are required");
      return moveSource(workspaceId, collectionId, sourceId, data);
    },
    onSuccess: () => {
      if (workspaceId && collectionId) {
        void queryClient.invalidateQueries({
          queryKey: [
            ...knowledgeKeys.all,
            "sources",
            workspaceId,
            collectionId,
          ],
        });
        void queryClient.invalidateQueries({
          queryKey: knowledgeKeys.folders(workspaceId, collectionId),
        });
      }
    },
  });
}
