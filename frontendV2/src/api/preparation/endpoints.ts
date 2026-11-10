/**
 * Server-recorded preparation intents chain source → OCR → compiler and stop
 * at a draft awaiting review. Mirrors `backendV1/qnu/domains/knowledge/preparation/router.py`.
 */
export const preparationPaths = {
  intents: (workspaceId: string, collectionId: string, sourceId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/preparation-intents`,
  intent: (workspaceId: string, collectionId: string, intentId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/preparation-intents/${intentId}`,
  cancel: (workspaceId: string, collectionId: string, intentId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/preparation-intents/${intentId}/cancel`,
} as const;
