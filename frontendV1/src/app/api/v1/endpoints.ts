/**
 * Single source of truth for the QNU AI v1 API surface.
 *
 * Paths are copied from the routers under `backendV1/qnu/domains`; a screen must
 * never invent an endpoint. `API_V1_PREFIX` matches `Settings.API_PREFIX` in
 * `backendV1/qnu/platform/config.py`.
 */

export const API_V1_PREFIX = "/platform/v1alpha1";

/** Default backendV1 port; the Vite dev proxy forwards the prefix here. */
export const API_V1_DEFAULT_TARGET = "http://127.0.0.1:8002";

export const lifecyclePaths = {
  previews: (workspaceId: string) =>
    `/workspaces/${workspaceId}/lifecycle/previews`,
  actions: (workspaceId: string) =>
    `/workspaces/${workspaceId}/lifecycle/actions`,
  action: (workspaceId: string, id: string) =>
    `/workspaces/${workspaceId}/lifecycle/actions/${id}`,
  resources: (workspaceId: string) =>
    `/workspaces/${workspaceId}/lifecycle/resources`,
} as const;

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

export const authPaths = {
  login: "/auth/login",
  me: "/auth/me",
  logout: "/auth/logout",
} as const;

export const workspacePaths = {
  list: "/workspaces",
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

export const modelopsPaths = {
  providers: "/modelops/providers",
  provider: (providerId: string) => `/modelops/providers/${providerId}`,
  diagnostics: (providerId: string) =>
    `/modelops/providers/${providerId}/diagnostics`,
  discover: (providerId: string) =>
    `/modelops/providers/${providerId}/discover`,
  probe: (providerId: string) => `/modelops/providers/${providerId}/probe`,
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
} as const;

export const knowledgePaths = {
  answers: (workspaceId: string, collectionId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/answers`,
  collections: (workspaceId: string) =>
    `/workspaces/${workspaceId}/collections`,
  collection: (workspaceId: string, collectionId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}`,
  sources: (workspaceId: string, collectionId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources`,
  source: (workspaceId: string, collectionId: string, sourceId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}`,
  revisions: (workspaceId: string, collectionId: string, sourceId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/revisions`,
  revisionContent: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/revisions/${revisionId}/content`,
} as const;

export const assistantPaths = {
  list: (workspaceId: string) => `/workspaces/${workspaceId}/assistants`,
  detail: (workspaceId: string, assistantId: string) =>
    `/workspaces/${workspaceId}/assistants/${assistantId}`,
} as const;

export const conversationPaths = {
  list: (workspaceId: string) => `/workspaces/${workspaceId}/conversations`,
  detail: (workspaceId: string, conversationId: string) =>
    `/workspaces/${workspaceId}/conversations/${conversationId}`,
  turns: (workspaceId: string, conversationId: string) =>
    `/workspaces/${workspaceId}/conversations/${conversationId}/turns`,
  turn: (workspaceId: string, conversationId: string, turnId: string) =>
    `/workspaces/${workspaceId}/conversations/${conversationId}/turns/${turnId}`,
} as const;

export const ocrPaths = {
  processingRuns: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/revisions/${revisionId}/processing-runs`,
  processingRun: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/revisions/${revisionId}/processing-runs/${runId}`,
  dispatchRun: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/revisions/${revisionId}/processing-runs/${runId}/dispatch`,
  document: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/revisions/${revisionId}/processing-runs/${runId}/document`,
  markdown: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/revisions/${revisionId}/processing-runs/${runId}/markdown`,
  manifest: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/revisions/${revisionId}/processing-runs/${runId}/manifest`,
  evidence: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/revisions/${revisionId}/processing-runs/${runId}/evidence`,
  pageRaw: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
    pageNumber: number,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/revisions/${revisionId}/processing-runs/${runId}/pages/${pageNumber}/raw`,
  pageImage: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
    pageNumber: number,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/revisions/${revisionId}/processing-runs/${runId}/pages/${pageNumber}/image`,
  textReview: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/revisions/${revisionId}/processing-runs/${runId}/text-review`,
  textReviewDocument: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/revisions/${revisionId}/processing-runs/${runId}/text-review/document`,
  textReviewMarkdown: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/revisions/${revisionId}/processing-runs/${runId}/text-review/markdown`,
  textReviewChecks: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/revisions/${revisionId}/processing-runs/${runId}/text-review/checks`,
  textReviewCheck: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
    checkId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/revisions/${revisionId}/processing-runs/${runId}/text-review/checks/${checkId}`,
} as const;

export const compilationPaths = {
  runs: (workspaceId: string, collectionId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs`,
  run: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}`,
  draft: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/draft`,
  markdown: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/markdown`,
  raw: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/raw`,
  autoReview: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/auto-review`,
  reviews: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/reviews`,
  review: (
    workspaceId: string,
    collectionId: string,
    runId: string,
    reviewId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/reviews/${reviewId}`,
  reviewReport: (
    workspaceId: string,
    collectionId: string,
    runId: string,
    reviewId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/reviews/${reviewId}/report`,
  reviewMarkdown: (
    workspaceId: string,
    collectionId: string,
    runId: string,
    reviewId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/reviews/${reviewId}/markdown`,
  reviewRaw: (
    workspaceId: string,
    collectionId: string,
    runId: string,
    reviewId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/reviews/${reviewId}/raw`,
  editContext: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/edit-context`,
  editPreviews: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/edit-previews`,
  edits: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compilation-runs/${runId}/edits`,
} as const;

/**
 * Index generations and source-bearing search.
 * Mirrors `backendV1/qnu/domains/knowledge/index/router.py` (Context673).
 */
export const indexingPaths = {
  evaluations: (workspaceId: string, collectionId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/retrieval-evaluations`,
  runs: (workspaceId: string, collectionId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/indexing-runs`,
  run: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/indexing-runs/${runId}`,
  manifest: (workspaceId: string, collectionId: string, runId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/indexing-runs/${runId}/manifest`,
  search: (workspaceId: string, collectionId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/search`,
} as const;

export const compiledDocumentPaths = {
  documents: (workspaceId: string, collectionId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents`,
  document: (workspaceId: string, collectionId: string, documentId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents/${documentId}`,
  versions: (workspaceId: string, collectionId: string, documentId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents/${documentId}/versions`,
  version: (
    workspaceId: string,
    collectionId: string,
    documentId: string,
    versionId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents/${documentId}/versions/${versionId}`,
  versionDraft: (
    workspaceId: string,
    collectionId: string,
    documentId: string,
    versionId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents/${documentId}/versions/${versionId}/draft`,
  versionReviewGate: (
    workspaceId: string,
    collectionId: string,
    documentId: string,
    versionId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents/${documentId}/versions/${versionId}/review-gate`,
  decisionPreview: (
    workspaceId: string,
    collectionId: string,
    documentId: string,
    versionId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents/${documentId}/versions/${versionId}/decision-preview`,
  decisions: (
    workspaceId: string,
    collectionId: string,
    documentId: string,
    versionId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents/${documentId}/versions/${versionId}/decisions`,
  history: (workspaceId: string, collectionId: string, documentId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents/${documentId}/history`,
  published: (workspaceId: string, collectionId: string, documentId: string) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/compiled-documents/${documentId}/published`,
} as const;

/** Permissions enforced by backendV1 for the screens in this batch. */
export const QNU_PERMISSIONS = {
  workspacesManage: "ai.workspaces.manage",
  modelsManage: "ai.models.manage",
} as const;

/** Routes owned by the v1 client; everything else stays on the KTX template. */
export const V1_ROUTE_PREFIXES = [
  "/workspaces",
  "/modelops",
  "/dashboard",
] as const;

export function isV1Route(pathname: string): boolean {
  return V1_ROUTE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}
