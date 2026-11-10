/**
 * HTTP request functions for Knowledge domain.
 * Mirrors `backendV1/qnu/domains/knowledge/`.
 */

import type { BlobResponse } from "../client";
import { v1Client } from "../v1-client";
import type { Page, PageParams } from "../workspaces/types";
import { knowledgePaths } from "./endpoints";
import type {
  CollectionCreateRequest,
  CollectionResponse,
  CollectionUpdateRequest,
  FolderCreateRequest,
  FolderDetailResponse,
  FolderMoveRequest,
  FolderResponse,
  FolderUpdateRequest,
  RevisionResponse,
  SourceListParams,
  SourceMoveRequest,
  SourceRenameRequest,
  SourceResponse,
  SourceSummaryResponse,
  SourceUploadResponse,
} from "./types";

// ==========================================
// Collections
// ==========================================

export async function listCollections(
  workspaceId: string,
  params?: Partial<PageParams>,
  options?: { signal?: AbortSignal },
): Promise<Page<CollectionResponse>> {
  return v1Client.get<Page<CollectionResponse>>(
    knowledgePaths.collections(workspaceId),
    {
      searchParams: {
        page: params?.page ?? 1,
        page_size: params?.pageSize ?? 50,
      },
      signal: options?.signal,
    },
  );
}

export async function getCollection(
  workspaceId: string,
  collectionId: string,
  options?: { signal?: AbortSignal },
): Promise<CollectionResponse> {
  return v1Client.get<CollectionResponse>(
    knowledgePaths.collection(workspaceId, collectionId),
    options,
  );
}

export async function createCollection(
  workspaceId: string,
  data: CollectionCreateRequest,
  options?: { signal?: AbortSignal },
): Promise<CollectionResponse> {
  return v1Client.post<CollectionResponse>(
    knowledgePaths.collections(workspaceId),
    data,
    options,
  );
}

export async function updateCollection(
  workspaceId: string,
  collectionId: string,
  data: CollectionUpdateRequest,
  options?: { signal?: AbortSignal },
): Promise<CollectionResponse> {
  return v1Client.patch<CollectionResponse>(
    knowledgePaths.collection(workspaceId, collectionId),
    data,
    options,
  );
}

// ==========================================
// Folders
// ==========================================

export async function listFolders(
  workspaceId: string,
  collectionId: string,
  options?: { signal?: AbortSignal },
): Promise<FolderResponse[]> {
  return v1Client.get<FolderResponse[]>(
    knowledgePaths.folders(workspaceId, collectionId),
    options,
  );
}

export async function getFolder(
  workspaceId: string,
  collectionId: string,
  folderId: string,
  options?: { signal?: AbortSignal },
): Promise<FolderDetailResponse> {
  return v1Client.get<FolderDetailResponse>(
    knowledgePaths.folder(workspaceId, collectionId, folderId),
    options,
  );
}

export async function createFolder(
  workspaceId: string,
  collectionId: string,
  data: FolderCreateRequest,
  options?: { signal?: AbortSignal },
): Promise<FolderResponse> {
  return v1Client.post<FolderResponse>(
    knowledgePaths.folders(workspaceId, collectionId),
    data,
    options,
  );
}

export async function updateFolder(
  workspaceId: string,
  collectionId: string,
  folderId: string,
  data: FolderUpdateRequest,
  options?: { signal?: AbortSignal },
): Promise<FolderResponse> {
  return v1Client.patch<FolderResponse>(
    knowledgePaths.folder(workspaceId, collectionId, folderId),
    data,
    options,
  );
}

export async function moveFolder(
  workspaceId: string,
  collectionId: string,
  folderId: string,
  data: FolderMoveRequest,
  options?: { signal?: AbortSignal },
): Promise<FolderResponse> {
  return v1Client.post<FolderResponse>(
    knowledgePaths.folderMove(workspaceId, collectionId, folderId),
    data,
    options,
  );
}

export async function deleteFolder(
  workspaceId: string,
  collectionId: string,
  folderId: string,
  options?: { signal?: AbortSignal },
): Promise<void> {
  return v1Client.delete<void>(
    knowledgePaths.folder(workspaceId, collectionId, folderId),
    options,
  );
}

// ==========================================
// Sources & Revisions
// ==========================================

export async function listSources(
  workspaceId: string,
  collectionId: string,
  params?: SourceListParams,
  options?: { signal?: AbortSignal },
): Promise<Page<SourceResponse>> {
  const searchParams: Record<string, string | number | boolean> = {
    page: params?.page ?? 1,
    page_size: params?.pageSize ?? 20,
  };

  if (params?.allFolders) {
    searchParams.all_folders = true;
  } else if (params?.folderId) {
    searchParams.folder_id = params.folderId;
  } else {
    // Root folder documents
    searchParams.folder_id = "root";
  }

  return v1Client.get<Page<SourceResponse>>(
    knowledgePaths.sources(workspaceId, collectionId),
    {
      searchParams,
      signal: options?.signal,
    },
  );
}

export async function uploadSource(
  workspaceId: string,
  collectionId: string,
  formData: FormData,
  idempotencyKey?: string,
  options?: { signal?: AbortSignal },
): Promise<SourceUploadResponse> {
  return v1Client.upload<SourceUploadResponse>(
    knowledgePaths.sources(workspaceId, collectionId),
    formData,
    {
      idempotencyKey,
      signal: options?.signal,
    },
  );
}

export async function getSource(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  options?: { signal?: AbortSignal },
): Promise<SourceResponse> {
  return v1Client.get<SourceResponse>(
    knowledgePaths.source(workspaceId, collectionId, sourceId),
    options,
  );
}

export async function getSourceSummary(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  options?: { signal?: AbortSignal },
): Promise<SourceSummaryResponse> {
  return v1Client.get<SourceSummaryResponse>(
    knowledgePaths.sourceSummary(workspaceId, collectionId, sourceId),
    options,
  );
}

export async function renameSource(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  data: SourceRenameRequest,
  options?: { signal?: AbortSignal },
): Promise<SourceResponse> {
  return v1Client.patch<SourceResponse>(
    knowledgePaths.sourceRename(workspaceId, collectionId, sourceId),
    data,
    options,
  );
}

export async function moveSource(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  data: SourceMoveRequest,
  options?: { signal?: AbortSignal },
): Promise<SourceResponse> {
  return v1Client.post<SourceResponse>(
    knowledgePaths.sourceMove(workspaceId, collectionId, sourceId),
    data,
    options,
  );
}

export async function listRevisions(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  options?: { signal?: AbortSignal },
): Promise<RevisionResponse[]> {
  return v1Client.get<RevisionResponse[]>(
    knowledgePaths.revisions(workspaceId, collectionId, sourceId),
    options,
  );
}

export async function getRevisionContentBlob(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  options?: { signal?: AbortSignal },
): Promise<BlobResponse> {
  return v1Client.requestBlob(
    knowledgePaths.revisionContent(
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
    ),
    options,
  );
}
