import type { BlobResponse, V1Client } from "@/app/api/v1";
import { knowledgePaths } from "@/app/api/v1";
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
  if (input.name !== undefined) {
    const trimmed = input.name.trim();
    if (trimmed) body.name = trimmed;
  }
  if (input.description !== undefined) {
    body.description =
      input.description === null ? null : input.description.trim();
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
  params: PageParams = {},
): Promise<PageResponse<KBSource>> {
  return client.get<PageResponse<KBSource>>(
    knowledgePaths.sources(workspaceId, collectionId),
    {
      searchParams: {
        page: params.page ?? 1,
        page_size: params.pageSize ?? 20,
      },
    },
  );
}

export async function uploadSource(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  file: File,
  title?: string,
  idempotencyKey?: string,
): Promise<SourceUploadResult> {
  const formData = new FormData();
  formData.append("file", file);
  if (title?.trim()) {
    formData.append("title", title.trim());
  }
  return client.upload<SourceUploadResult>(
    knowledgePaths.sources(workspaceId, collectionId),
    formData,
    { idempotencyKey },
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
