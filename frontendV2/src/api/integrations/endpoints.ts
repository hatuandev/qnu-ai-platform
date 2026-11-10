export const integrationPaths = {
  config: "/integrations/config",
  apps: (workspaceId: string) => `/workspaces/${workspaceId}/integrations/apps`,
  keys: (workspaceId: string) => `/workspaces/${workspaceId}/integrations/keys`,
  keyStatus: (workspaceId: string, keyId: string) =>
    `/workspaces/${workspaceId}/integrations/keys/${keyId}/status`,
  keyRotate: (workspaceId: string, keyId: string) =>
    `/workspaces/${workspaceId}/integrations/keys/${keyId}/rotate`,
  keyRevoke: (workspaceId: string, keyId: string) =>
    `/workspaces/${workspaceId}/integrations/keys/${keyId}`,
  logs: (workspaceId: string) => `/workspaces/${workspaceId}/integrations/logs`,
} as const;
