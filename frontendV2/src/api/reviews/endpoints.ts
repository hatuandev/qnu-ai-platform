/**
 * Review handoff commands and reads. Mirrors
 * `backendV1/qnu/domains/knowledge/review/router.py`.
 */
export const reviewSubmissionPaths = {
  submissions: (workspaceId: string, collectionId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/review-submissions`,
  submission: (
    workspaceId: string,
    collectionId: string,
    submissionId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/review-submissions/${submissionId}`,
  previews: (workspaceId: string, collectionId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/review-submissions/previews`,
} as const;
