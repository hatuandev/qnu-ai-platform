export const modelopsPaths = {
  connections: "/modelops/connections",
  connection: (id: string) => `/modelops/connections/${encodeURIComponent(id)}`,
  connectionTest: (id: string) =>
    `/modelops/connections/${encodeURIComponent(id)}/test`,
  connectionModels: (id: string) =>
    `/modelops/connections/${encodeURIComponent(id)}/models`,
  connectionModel: (id: string, modelId: string) =>
    `/modelops/connections/${encodeURIComponent(id)}/models/${encodeURIComponent(modelId)}`,
  connectionKeys: (id: string) =>
    `/modelops/connections/${encodeURIComponent(id)}/keys`,
  connectionKey: (id: string, keyId: string) =>
    `/modelops/connections/${encodeURIComponent(id)}/keys/${encodeURIComponent(keyId)}`,
  connectionSyncCapacity: (id: string) =>
    `/modelops/connections/${encodeURIComponent(id)}/sync-capacity`,

  executions: (providerId: string) =>
    `/modelops/providers/${encodeURIComponent(providerId)}/executions`,
  registry: "/modelops/registry",
  resilience: (providerId: string) =>
    `/modelops/providers/${encodeURIComponent(providerId)}/resilience`,
  providers: "/modelops/providers",
  provider: (providerId: string) => `/modelops/providers/${providerId}`,
  diagnostics: (providerId: string) =>
    `/modelops/providers/${providerId}/diagnostics`,
  discover: (providerId: string) =>
    `/modelops/providers/${providerId}/discover`,
  probe: (providerId: string) => `/modelops/providers/${providerId}/probe`,
  reasoning: (providerId: string) =>
    `/modelops/providers/${providerId}/reasoning`,
  keys: (providerId: string) => `/modelops/providers/${providerId}/keys`,
  keyRotate: (providerId: string, keyId: string) =>
    `/modelops/providers/${providerId}/keys/${keyId}/rotate`,
  keyRevoke: (providerId: string, keyId: string) =>
    `/modelops/providers/${providerId}/keys/${keyId}/revoke`,
  keyEvents: (providerId: string) =>
    `/modelops/providers/${providerId}/key-events`,
  defaults: "/modelops/defaults",
  events: "/modelops/events",
  catalog: "/modelops/catalog",
  providersSummary: "/modelops/providers-summary",
} as const;
