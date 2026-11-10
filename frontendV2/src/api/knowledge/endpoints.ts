export const knowledgePaths = {
  answers: (workspaceId: string, collectionId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/answers`,
  collections: (workspaceId: string) =>
    `/workspaces/${workspaceId}/collections`,
  collection: (workspaceId: string, collectionId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}`,
  sources: (workspaceId: string, collectionId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources`,
  source: (workspaceId: string, collectionId: string, sourceId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}`,
  sourceSummary: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/summary`,
  sourceMove: (workspaceId: string, collectionId: string, sourceId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/move`,
  sourceRename: (workspaceId: string, collectionId: string, sourceId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}`,
  revisions: (workspaceId: string, collectionId: string, sourceId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/revisions`,
  revisionContent: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/revisions/${revisionId}/content`,
  folders: (workspaceId: string, collectionId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/folders`,
  folder: (workspaceId: string, collectionId: string, folderId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/folders/${folderId}`,
  folderMove: (workspaceId: string, collectionId: string, folderId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/folders/${folderId}/move`,
  folderImpact: (workspaceId: string, collectionId: string, folderId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/folders/${folderId}/impact`,
  folderRestore: (
    workspaceId: string,
    collectionId: string,
    folderId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/folders/${folderId}/restore`,
} as const;
