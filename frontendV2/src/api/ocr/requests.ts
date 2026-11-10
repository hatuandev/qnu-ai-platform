import { v1Client } from "../v1-client";
import { ocrPaths } from "./endpoints";

export type ProcessingProgressResponse = {
  id: string;
  status: string;
  pages_total: number | null;
  pages_done: number;
  pagination: "page" | "document";
};

export function getProcessingProgress(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  options?: { signal?: AbortSignal },
) {
  return v1Client.get<ProcessingProgressResponse>(
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

// ---------------------------------------------------------------------------
// Text Review / Spelling Contracts
// ---------------------------------------------------------------------------

export type TextUnit = {
  evidence_id: string;
  page: number;
  kind: string;
  text: string;
  original_text: string;
  bbox: Record<string, unknown>;
  row?: number | null;
  column?: number | null;
};

export type ReviewDocument = {
  run_id: string;
  version: number;
  version_id: string | null;
  canonical_sha256: string;
  original_sha256: string;
  markdown_sha256: string;
  units: TextUnit[];
  saved_at?: string | null;
};

export type TextChange = {
  evidence_id: string;
  before: string;
  after: string;
};

export type SaveReview = {
  expected_version: number;
  expected_sha256: string;
  changes: TextChange[];
};

export type Suggestion = {
  evidence_id: string;
  start: number;
  end: number;
  original: string;
  replacement: string;
  reason: string;
  context_before?: string | null;
  context_after?: string | null;
  review_reason?: string | null;
};

export type DetectionResponse = {
  id: string;
  status:
    | "running"
    | "completed"
    | "failed"
    | "uncertain"
    | "cancelled"
    | string;
  version: number;
  canonical_sha256: string;
  suggestions: Suggestion[];
  withheld_suggestions?: Suggestion[];
  checked_evidence_ids: string[];
  total_evidence_count?: number | null;
  error_code?: string | null;
  usage_id?: string | null;
  created_at: string;
};

export type DetectRequest = {
  source_version?: number | null;
  expected_version: number;
  expected_sha256: string;
  evidence_ids: string[];
  provider_id?: string | null;
  max_output_tokens?: number | null;
};

export function getTextReview(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  version?: number,
  options?: { signal?: AbortSignal },
) {
  const query = version !== undefined ? `?version=${version}` : "";
  return v1Client.get<ReviewDocument>(
    `${ocrPaths.textReview(workspaceId, collectionId, sourceId, revisionId, runId)}${query}`,
    options,
  );
}

export function saveTextReview(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  body: SaveReview,
  idempotencyKey: string,
  options?: { signal?: AbortSignal },
) {
  return v1Client.post<ReviewDocument>(
    ocrPaths.textReview(workspaceId, collectionId, sourceId, revisionId, runId),
    body,
    {
      ...options,
      headers: {
        "idempotency-key": idempotencyKey,
      },
    },
  );
}

export function getTextReviewMarkdown(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  version?: number,
  options?: { signal?: AbortSignal },
) {
  const query = version !== undefined ? `?version=${version}` : "";
  return v1Client.get<string>(
    `${ocrPaths.textReviewMarkdown(workspaceId, collectionId, sourceId, revisionId, runId)}${query}`,
    options,
  );
}

export function getTextReviewJson(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  version?: number,
  options?: { signal?: AbortSignal },
) {
  const query = version !== undefined ? `?version=${version}` : "";
  return v1Client.get<Record<string, unknown>>(
    `${ocrPaths.textReviewDocument(workspaceId, collectionId, sourceId, revisionId, runId)}${query}`,
    options,
  );
}

export function listTextReviewChecks(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  version?: number,
  options?: { signal?: AbortSignal },
) {
  const query = version !== undefined ? `?version=${version}` : "";
  return v1Client.get<DetectionResponse[]>(
    `${ocrPaths.textReviewChecks(workspaceId, collectionId, sourceId, revisionId, runId)}${query}`,
    options,
  );
}

export function getTextReviewCheck(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  checkId: string,
  options?: { signal?: AbortSignal },
) {
  return v1Client.get<DetectionResponse>(
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

export function detectTextReview(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  body: DetectRequest,
  idempotencyKey: string,
  options?: { signal?: AbortSignal },
) {
  return v1Client.post<DetectionResponse>(
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
        "idempotency-key": idempotencyKey,
      },
    },
  );
}
