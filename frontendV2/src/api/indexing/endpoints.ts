/**
 * Index generations and source-bearing search.
 * Mirrors `backendV1/qnu/domains/knowledge/index/router.py` (Context673).
 */
export const indexingPaths = {
  evaluations: (workspaceId: string, collectionId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/retrieval-evaluations`,
  runs: (workspaceId: string, collectionId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/indexing-runs`,
  run: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/indexing-runs/${runId}`,
  manifest: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/indexing-runs/${runId}/manifest`,
  search: (workspaceId: string, collectionId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/search`,
} as const;
