export const lifecyclePaths = {
  previews: (workspaceId: string) =>
    `/workspaces/${workspaceId}/lifecycle/previews`,
  actions: (workspaceId: string) =>
    `/workspaces/${workspaceId}/lifecycle/actions`,
  action: (workspaceId: string, id: string) =>
    `/workspaces/${workspaceId}/lifecycle/actions/${id}`,
  resources: (workspaceId: string) =>
    `/workspaces/${workspaceId}/lifecycle/resources`,
  sourceDeletions: (workspaceId: string) =>
    `/workspaces/${encodeURIComponent(workspaceId)}/lifecycle/source-deletions`,
  legacyDeletedSources: (workspaceId: string) =>
    `/workspaces/${encodeURIComponent(workspaceId)}/lifecycle/source-deletions/legacy`,
} as const;
