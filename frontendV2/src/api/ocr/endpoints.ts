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
  renderedPdf: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/revisions/${revisionId}/processing-runs/${runId}/pdf`,
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
  bundle: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/revisions/${revisionId}/processing-runs/${runId}/bundle`,
  image: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
    assetNo: number,
  ) =>
    `/workspaces/${workspaceId}/collections/${collectionId}/sources/${sourceId}/revisions/${revisionId}/processing-runs/${runId}/images/${assetNo}`,
} as const;
