import type { BlobResponse, V1Client } from "@/app/api/v1";
import { knowledgePaths } from "@/app/api/v1";
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

export async function listCollections(
  client: V1Client,
  workspaceId: string,
  params: PageParams = {},
): Promise<PageResponse<KBCollection>> {
  return client.get<PageResponse<KBCollection>>(
    knowledgePaths.collections(workspaceId),
    {
      searchParams: {
        page: params.page ?? 1,
        page_size: params.pageSize ?? 20,
      },
    },
  );
}

export async function createCollection(
  client: V1Client,
  workspaceId: string,
  input: CollectionCreateInput,
): Promise<KBCollection> {
  const body: Record<string, unknown> = {
    name: input.name.trim(),
  };
  if (input.description !== undefined) {
    body.description = input.description ? input.description.trim() : null;
  }
  return client.post<KBCollection>(
    knowledgePaths.collections(workspaceId),
    body,
  );
}

export async function getCollection(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
): Promise<KBCollection> {
  return client.get<KBCollection>(
    knowledgePaths.collection(workspaceId, collectionId),
  );
}

export async function updateCollection(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  input: CollectionUpdateInput,
): Promise<KBCollection> {
  const body: Record<string, unknown> = {};
  if (input.name !== undefined) body.name = input.name.trim();
  if (input.description !== undefined) {
    body.description = input.description ? input.description.trim() : null;
  }
  return client.patch<KBCollection>(
    knowledgePaths.collection(workspaceId, collectionId),
    body,
  );
}

export async function listSources(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  params: SourceListParams = {},
): Promise<PageResponse<KBSource>> {
  const searchParams: Record<string, string | number | boolean> = {
    page: params.page ?? 1,
    page_size: params.pageSize ?? 20,
  };
  if (params.folderId !== undefined && params.folderId !== null) {
    searchParams.folder_id = params.folderId;
  }
  if (params.allFolders) {
    searchParams.all_folders = true;
  }
  return client.get<PageResponse<KBSource>>(
    knowledgePaths.sources(workspaceId, collectionId),
    { searchParams },
  );
}

export async function uploadSource(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  file: File,
  title?: string,
  idempotencyKey?: string,
  folderId?: string | null,
): Promise<SourceUploadResult> {
  const formData = new FormData();
  formData.append("file", file);
  if (title?.trim()) {
    formData.append("title", title.trim());
  }
  if (folderId) {
    formData.append("folder_id", folderId);
  }
  return client.upload<SourceUploadResult>(
    knowledgePaths.sources(workspaceId, collectionId),
    formData,
    { idempotencyKey },
  );
}

export async function moveSource(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  targetFolderId: string | null,
): Promise<KBSource> {
  return client.post<KBSource>(
    knowledgePaths.sourceMove(workspaceId, collectionId, sourceId),
    { target_folder_id: targetFolderId },
  );
}

export async function renameSource(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  title: string,
): Promise<KBSource> {
  return client.patch<KBSource>(
    knowledgePaths.sourceRename(workspaceId, collectionId, sourceId),
    { title: title.trim() },
  );
}

export async function getSource(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
): Promise<KBSource> {
  return client.get<KBSource>(
    knowledgePaths.source(workspaceId, collectionId, sourceId),
  );
}

export async function listRevisions(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
): Promise<KBRevision[]> {
  return client.get<KBRevision[]>(
    knowledgePaths.revisions(workspaceId, collectionId, sourceId),
  );
}

export async function addRevision(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  file: File,
  idempotencyKey?: string,
  staged?: boolean,
): Promise<SourceUploadResult> {
  const formData = new FormData();
  formData.append("file", file);
  if (staged !== undefined) formData.append("staged", String(staged));
  // NEVER append title: backend rejects it with 422 revision_title_not_supported
  return client.upload<SourceUploadResult>(
    knowledgePaths.revisions(workspaceId, collectionId, sourceId),
    formData,
    { idempotencyKey },
  );
}

export async function downloadRevisionContent(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
): Promise<BlobResponse> {
  return client.requestBlob(
    knowledgePaths.revisionContent(
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
    ),
  );
}

export async function listFolders(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
): Promise<KBFolder[]> {
  return client.get<KBFolder[]>(
    knowledgePaths.folders(workspaceId, collectionId),
  );
}

export async function createFolder(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  input: FolderCreateInput,
): Promise<KBFolder> {
  return client.post<KBFolder>(
    knowledgePaths.folders(workspaceId, collectionId),
    { name: input.name.trim(), parent_id: input.parent_id ?? null },
  );
}

export async function getFolder(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  folderId: string,
): Promise<KBFolderDetail> {
  return client.get<KBFolderDetail>(
    knowledgePaths.folder(workspaceId, collectionId, folderId),
  );
}

export async function updateFolder(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  folderId: string,
  input: FolderUpdateInput,
): Promise<KBFolder> {
  return client.patch<KBFolder>(
    knowledgePaths.folder(workspaceId, collectionId, folderId),
    { name: input.name.trim() },
  );
}

export async function moveFolder(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  folderId: string,
  input: FolderMoveInput,
): Promise<KBFolder> {
  return client.post<KBFolder>(
    knowledgePaths.folderMove(workspaceId, collectionId, folderId),
    { target_parent_id: input.target_parent_id ?? null },
  );
}

export async function getFolderImpact(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  folderId: string,
): Promise<FolderImpact> {
  return client.get<FolderImpact>(
    knowledgePaths.folderImpact(workspaceId, collectionId, folderId),
  );
}

export async function deleteFolder(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  folderId: string,
): Promise<FolderImpact> {
  return client.delete<FolderImpact>(
    knowledgePaths.folder(workspaceId, collectionId, folderId),
  );
}

export async function restoreFolder(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  folderId: string,
): Promise<KBFolder> {
  return client.post<KBFolder>(
    knowledgePaths.folderRestore(workspaceId, collectionId, folderId),
    {},
  );
}
