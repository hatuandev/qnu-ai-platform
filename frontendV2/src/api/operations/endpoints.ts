export const operationsPaths = {
  backups: (workspaceId: string) =>
    `/workspaces/${workspaceId}/operations/backups`,
  backup: (workspaceId: string, id: string) =>
    `/workspaces/${workspaceId}/operations/backups/${id}`,
  backupVerify: (workspaceId: string, id: string) =>
    `/workspaces/${workspaceId}/operations/backups/${id}/verify`,
  backupDownload: (workspaceId: string, id: string) =>
    `/workspaces/${workspaceId}/operations/backups/${id}/download`,
  backupDeletePreview: (workspaceId: string, id: string) =>
    `/workspaces/${workspaceId}/operations/backups/${id}/delete-preview`,
  retention: (workspaceId: string) =>
    `/workspaces/${workspaceId}/operations/retention`,
  cleanupPreviews: (workspaceId: string) =>
    `/workspaces/${workspaceId}/operations/storage-cleanups/previews`,
  cleanupActions: (workspaceId: string) =>
    `/workspaces/${workspaceId}/operations/storage-cleanups/actions`,
  cleanupAction: (workspaceId: string, id: string) =>
    `/workspaces/${workspaceId}/operations/storage-cleanups/actions/${id}`,
  jobs: (workspaceId: string) => `/workspaces/${workspaceId}/operations/jobs`,
  job: (workspaceId: string, kind: string, id: string) =>
    `/workspaces/${workspaceId}/operations/jobs/${kind}/${id}`,
  recoveryPreview: (workspaceId: string, kind: string, id: string) =>
    `/workspaces/${workspaceId}/operations/jobs/${kind}/${id}/recovery-preview`,
  summary: (workspaceId: string) =>
    `/workspaces/${workspaceId}/operations/summary`,
  readiness: (workspaceId: string) =>
    `/workspaces/${workspaceId}/operations/readiness`,
  actions: (workspaceId: string) =>
    `/workspaces/${workspaceId}/operations/actions`,
  action: (workspaceId: string, id: string) =>
    `/workspaces/${workspaceId}/operations/actions/${id}`,
} as const;
