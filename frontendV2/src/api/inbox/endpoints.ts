export const inboxPaths = {
  list: (workspaceId: string) => `/workspaces/${workspaceId}/inbox`,
} as const;
