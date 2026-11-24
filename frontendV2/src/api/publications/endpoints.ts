export const publicationPaths = {
  admin: (workspaceId: string, assistantId: string) =>
    `/workspaces/${workspaceId}/assistants/${assistantId}/publication`,
  adminStats: (workspaceId: string, assistantId: string, days: number) =>
    `/workspaces/${workspaceId}/assistants/${assistantId}/publication/stats?days=${days}`,
  publicList: "/public/chatbots",
  publicInfo: (slug: string) => `/public/chatbots/${encodeURIComponent(slug)}`,
  publicSessions: (slug: string) =>
    `/public/chatbots/${encodeURIComponent(slug)}/sessions`,
  publicTurns: (slug: string) =>
    `/public/chatbots/${encodeURIComponent(slug)}/turns`,
  publicExport: (slug: string, draftId: string) =>
    `/public/chatbots/${encodeURIComponent(slug)}/exports/${encodeURIComponent(draftId)}`,
} as const;
