export const compiledDocumentPaths = {
  documents: (workspaceId: string, collectionId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents`,
  registrationMetadata: (
    workspaceId: string,
    collectionId: string,
    runId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents/registration-metadata/${runId}`,
  document: (workspaceId: string, collectionId: string, documentId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents/${documentId}`,
  versions: (workspaceId: string, collectionId: string, documentId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents/${documentId}/versions`,
  version: (
    workspaceId: string,
    collectionId: string,
    documentId: string,
    versionId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents/${documentId}/versions/${versionId}`,
  versionDraft: (
    workspaceId: string,
    collectionId: string,
    documentId: string,
    versionId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents/${documentId}/versions/${versionId}/draft`,
  versionReviewGate: (
    workspaceId: string,
    collectionId: string,
    documentId: string,
    versionId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents/${documentId}/versions/${versionId}/review-gate`,
  decisionPreview: (
    workspaceId: string,
    collectionId: string,
    documentId: string,
    versionId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents/${documentId}/versions/${versionId}/decision-preview`,
  decisions: (
    workspaceId: string,
    collectionId: string,
    documentId: string,
    versionId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents/${documentId}/versions/${versionId}/decisions`,
  history: (workspaceId: string, collectionId: string, documentId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents/${documentId}/history`,
  published: (workspaceId: string, collectionId: string, documentId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents/${documentId}/published`,
  summary: (workspaceId: string, collectionId: string, documentId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents/${documentId}/summary`,
} as const;
