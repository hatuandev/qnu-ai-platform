import type { BlobResponse, V1Client, V1RequestOptions } from "@/app/api/v1";
import { ocrPaths } from "@/app/api/v1";
import type {
  DetectionResponse,
  DetectRequestInput,
  EvidenceSnapshotResponse,
  ProcessingRunCreatedResponse,
  ProcessingRunDetailResponse,
  ProcessingRunListResponse,
  ProcessingRunRequest,
  ProcessingRunResponse,
  ReviewDocument,
  SaveReviewInput,
} from "@/features/knowledge/ocr-types";

// ============================================================================
// OCR Processing Runs Requests
// ============================================================================

export async function listProcessingRuns(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  params?: { page?: number; page_size?: number },
  options?: V1RequestOptions,
): Promise<ProcessingRunListResponse> {
  const query: Record<string, string | number> = {};
  if (params?.page) query.page = params.page;
  if (params?.page_size) query.page_size = params.page_size;

  return client.get<ProcessingRunListResponse>(
    ocrPaths.processingRuns(workspaceId, collectionId, sourceId, revisionId),
    {
      ...options,
      searchParams: query,
    },
  );
}

export async function requestProcessingRun(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  body?: ProcessingRunRequest,
  options?: V1RequestOptions,
): Promise<ProcessingRunCreatedResponse> {
  return client.post<ProcessingRunCreatedResponse>(
    ocrPaths.processingRuns(workspaceId, collectionId, sourceId, revisionId),
    body ?? {},
    options,
  );
}

export async function getProcessingRun(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  options?: V1RequestOptions,
): Promise<ProcessingRunDetailResponse> {
  return client.get<ProcessingRunDetailResponse>(
    ocrPaths.processingRun(
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
    ),
    options,
  );
}

export async function dispatchProcessingRun(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  options?: V1RequestOptions,
): Promise<ProcessingRunResponse> {
  return client.post<ProcessingRunResponse>(
    ocrPaths.dispatchRun(
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
    ),
    {},
    options,
  );
}

export async function readRunDocumentBlob(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  options?: V1RequestOptions,
): Promise<BlobResponse> {
  return client.requestBlob(
    ocrPaths.document(workspaceId, collectionId, sourceId, revisionId, runId),
    {
      ...options,
      headers: {
        Accept: "application/json",
        ...options?.headers,
      },
    },
  );
}

export async function readRunMarkdownBlob(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  options?: V1RequestOptions,
): Promise<BlobResponse> {
  return client.requestBlob(
    ocrPaths.markdown(workspaceId, collectionId, sourceId, revisionId, runId),
    {
      ...options,
      headers: {
        Accept: "text/markdown",
        ...options?.headers,
      },
    },
  );
}

export async function downloadRunBundleBlob(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  options?: V1RequestOptions,
): Promise<BlobResponse> {
  return client.requestBlob(
    ocrPaths.bundle(workspaceId, collectionId, sourceId, revisionId, runId),
    {
      ...options,
      headers: {
        Accept: "application/zip",
        ...options?.headers,
      },
    },
  );
}

export async function readRunManifest(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  options?: V1RequestOptions,
): Promise<Record<string, unknown>> {
  return client.get<Record<string, unknown>>(
    ocrPaths.manifest(workspaceId, collectionId, sourceId, revisionId, runId),
    options,
  );
}

export async function readRunEvidence(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  options?: V1RequestOptions,
): Promise<EvidenceSnapshotResponse> {
  return client.get<EvidenceSnapshotResponse>(
    ocrPaths.evidence(workspaceId, collectionId, sourceId, revisionId, runId),
    options,
  );
}

export async function readPageRawBlob(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  pageNumber: number,
  options?: V1RequestOptions,
): Promise<BlobResponse> {
  return client.requestBlob(
    ocrPaths.pageRaw(
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
      pageNumber,
    ),
    {
      ...options,
      headers: {
        Accept: "application/octet-stream",
        ...options?.headers,
      },
    },
  );
}

export async function readPageImageBlob(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  pageNumber: number,
  options?: V1RequestOptions,
): Promise<BlobResponse> {
  return client.requestBlob(
    ocrPaths.pageImage(
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
      pageNumber,
    ),
    {
      ...options,
      headers: {
        Accept: "image/png",
        ...options?.headers,
      },
    },
  );
}

export async function readRenderedPdfBlob(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  options?: V1RequestOptions,
): Promise<BlobResponse> {
  return client.requestBlob(
    ocrPaths.renderedPdf(
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
    ),
    {
      ...options,
      headers: {
        Accept: "application/pdf",
        ...options?.headers,
      },
    },
  );
}

// ============================================================================
// Text Review & Spell Check Requests
// ============================================================================

export async function readTextReview(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  version?: number | null,
  options?: V1RequestOptions,
): Promise<ReviewDocument> {
  const query: Record<string, number> = {};
  if (version !== undefined && version !== null) {
    query.version = version;
  }

  return client.get<ReviewDocument>(
    ocrPaths.textReview(workspaceId, collectionId, sourceId, revisionId, runId),
    {
      ...options,
      searchParams: query,
    },
  );
}

export async function saveTextReview(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  body: SaveReviewInput,
  idempotencyKey: string,
  options?: V1RequestOptions,
): Promise<ReviewDocument> {
  return client.post<ReviewDocument>(
    ocrPaths.textReview(workspaceId, collectionId, sourceId, revisionId, runId),
    body,
    {
      ...options,
      headers: {
        "Idempotency-Key": idempotencyKey,
        ...options?.headers,
      },
    },
  );
}

export async function downloadReviewDocumentBlob(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  version?: number | null,
  options?: V1RequestOptions,
): Promise<BlobResponse> {
  const query: Record<string, number> = {};
  if (version !== undefined && version !== null) {
    query.version = version;
  }

  return client.requestBlob(
    ocrPaths.textReviewDocument(
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
    ),
    {
      ...options,
      searchParams: query,
      headers: {
        Accept: "application/json",
        ...options?.headers,
      },
    },
  );
}

export async function downloadReviewMarkdownBlob(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  version?: number | null,
  options?: V1RequestOptions,
): Promise<BlobResponse> {
  const query: Record<string, number> = {};
  if (version !== undefined && version !== null) {
    query.version = version;
  }

  return client.requestBlob(
    ocrPaths.textReviewMarkdown(
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
    ),
    {
      ...options,
      searchParams: query,
      headers: {
        Accept: "text/markdown",
        ...options?.headers,
      },
    },
  );
}

export async function createDetectCheck(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  body: DetectRequestInput,
  idempotencyKey: string,
  options?: V1RequestOptions,
): Promise<DetectionResponse> {
  return client.post<DetectionResponse>(
    ocrPaths.textReviewChecks(
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
    ),
    body,
    {
      ...options,
      headers: {
        "Idempotency-Key": idempotencyKey,
        ...options?.headers,
      },
    },
  );
}

export async function getDetectCheck(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  checkId: string,
  options?: V1RequestOptions,
): Promise<DetectionResponse> {
  return client.get<DetectionResponse>(
    ocrPaths.textReviewCheck(
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
      checkId,
    ),
    options,
  );
}
