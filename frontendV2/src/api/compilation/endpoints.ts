export const compilationPaths = {
  progressSummary: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/progress/summary`,
  runs: (workspaceId: string, collectionId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs`,
  run: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}`,
  draft: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/draft`,
  draftFile: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/draft.json`,
  markdown: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/markdown`,
  raw: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/raw`,
  autoReview: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/auto-review`,
  reviews: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/reviews`,
  review: (
    workspaceId: string,
    collectionId: string,
    runId: string,
    reviewId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/reviews/${reviewId}`,
  reviewReport: (
    workspaceId: string,
    collectionId: string,
    runId: string,
    reviewId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/reviews/${reviewId}/report`,
  reviewMarkdown: (
    workspaceId: string,
    collectionId: string,
    runId: string,
    reviewId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/reviews/${reviewId}/markdown`,
  reviewRaw: (
    workspaceId: string,
    collectionId: string,
    runId: string,
    reviewId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/reviews/${reviewId}/raw`,
  editContext: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/edit-context`,
  editPreviews: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/edit-previews`,
  edits: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/edits`,
} as const;
