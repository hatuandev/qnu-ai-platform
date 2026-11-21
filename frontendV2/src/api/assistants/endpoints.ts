export const assistantPaths = {
  list: (workspaceId: string) => `/workspaces/${workspaceId}/assistants`,
  craftPersona: (workspaceId: string) =>
    `/workspaces/${workspaceId}/assistants/craft-persona`,
  detail: (workspaceId: string, assistantId: string) =>
    `/workspaces/${workspaceId}/assistants/${assistantId}`,
  readiness: (workspaceId: string, assistantId: string) =>
    `/workspaces/${workspaceId}/assistants/${assistantId}/readiness`,
  answerReviews: (workspaceId: string, assistantId: string) =>
    `/workspaces/${workspaceId}/assistants/${assistantId}/answer-reviews`,
  answerReview: (workspaceId: string, assistantId: string, reviewId: string) =>
    `/workspaces/${workspaceId}/assistants/${assistantId}/answer-reviews/${reviewId}`,
  answerReviewItem: (
    workspaceId: string,
    assistantId: string,
    reviewId: string,
    itemId: string,
  ) =>
    `/workspaces/${workspaceId}/assistants/${assistantId}/answer-reviews/${reviewId}/items/${itemId}`,
} as const;
