export const workspacePaths = {
  list: "/workspaces",
  resolveRoute: (code: string) =>
    `/workspaces/resolve-route?code=${encodeURIComponent(code)}`,
  detail: (workspaceId: string) => `/workspaces/${workspaceId}`,
  members: (workspaceId: string) => `/workspaces/${workspaceId}/members`,
  member: (workspaceId: string, memberId: string) =>
    `/workspaces/${workspaceId}/members/${memberId}`,
  events: (workspaceId: string) => `/workspaces/${workspaceId}/events`,
  allowedProviders: (workspaceId: string) =>
    `/workspaces/${workspaceId}/allowed-providers`,
  modelDefaults: (workspaceId: string) =>
    `/workspaces/${workspaceId}/model-defaults`,
  quota: (workspaceId: string) => `/workspaces/${workspaceId}/quota`,
  usage: (workspaceId: string) => `/workspaces/${workspaceId}/usage`,
} as const;
