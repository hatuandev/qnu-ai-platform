export const conversationPaths = {
  list: (workspaceId: string) => `/workspaces/${workspaceId}/conversations`,
  detail: (workspaceId: string, conversationId: string) =>
    `/workspaces/${workspaceId}/conversations/${conversationId}`,
  turns: (workspaceId: string, conversationId: string) =>
    `/workspaces/${workspaceId}/conversations/${conversationId}/turns`,
  turn: (workspaceId: string, conversationId: string, turnId: string) =>
    `/workspaces/${workspaceId}/conversations/${conversationId}/turns/${turnId}`,
  feedback: (workspaceId: string, conversationId: string, turnId: string) =>
    `/workspaces/${workspaceId}/conversations/${conversationId}/turns/${turnId}/feedback`,
} as const;
