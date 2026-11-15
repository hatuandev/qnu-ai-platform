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

export type WarningsAcknowledgement = {
  fingerprint: string;
  by: string;
  at: string;
  reason: string;
  images_failed: number;
};

export type WarningsAckResponse = {
  run: ProcessingProgressResponse;
  acknowledged: WarningsAcknowledgement;
  created: boolean;
};

export function acknowledgeOcrWarnings(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  body: { reason: string },
  options?: { signal?: AbortSignal },
) {
  return v1Client.post<WarningsAckResponse>(
    ocrPaths.acknowledgeWarnings(
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
    ),
    body,
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

export type ImageOcrFailure = {
  image_asset_no: number;
  page: number;
  bbox: number[] | null;
  error_code: string;
  attempts: number;
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
  image_ocr_failures: ImageOcrFailure[];
  image_ocr_acknowledged: boolean;
};

export type TextChange = {
  evidence_id: string;
  before: string;
  after: string;
  spelling_edits?: { start: number; end: number; replacement: string }[];
};

export type SaveReview = {
  expected_version: number;
  expected_sha256: string;
  changes: TextChange[];
  review_check_id?: string | null;
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

export type IgnoredSuggestion = {
  evidence_id: string;
  start: number;
  end: number;
};

export type SpellingDisposition = IgnoredSuggestion & {
  ignored: boolean;
};

export type SpellingDispositionBatch = {
  suggestions: IgnoredSuggestion[];
};

export type TextVersionSummary = {
  version: number;
  version_id: string | null;
  saved_at: string | null;
  change_count: number;
  is_current: boolean;
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
  ignored_suggestions?: IgnoredSuggestion[];
  checked_evidence_ids: string[];
  total_evidence_count?: number | null;
  error_code?: string | null;
  usage_id?: string | null;
  created_at: string;
  reviewed_at?: string | null;
  reviewed_version?: number | null;
  reviewed_sha256?: string | null;
  reviewed_by?: string | null;
};

export type SpellingStatusSummary = {
  running: boolean;
  check: {
    status: string;
    reviewed_at: string | null;
    checked_count: number;
    total_evidence_count: number | null;
    pending_count: number;
    ignored_count: number;
  } | null;
};

export type DetectRequest = {
  source_version?: number | null;
  expected_version: number;
  expected_sha256: string;
  evidence_ids: string[];
  provider_id?: string | null;
  max_output_tokens?: number | null;
};

export type RerunReviewRequest = {
  version: number;
  retry?: boolean;
};

export type RerunReviewResponse = {
  run_id: string;
  version: number;
  status: string;
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

export function getSpellingStatus(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  version: number,
  options?: { signal?: AbortSignal },
) {
  const checksPath = ocrPaths.textReviewChecks(
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
    runId,
  );
  return v1Client.get<SpellingStatusSummary>(
    `${checksPath}/summary?version=${version}`,
    options,
  );
}

export function listTextReviewVersions(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  options?: { signal?: AbortSignal },
) {
  return v1Client.get<TextVersionSummary[]>(
    ocrPaths.textReviewVersions(
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
    ),
    options,
  );
}

export function setTextReviewDisposition(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  checkId: string,
  body: SpellingDisposition,
  options?: { signal?: AbortSignal },
) {
  return v1Client.post<DetectionResponse>(
    ocrPaths.textReviewCheckDispositions(
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
      checkId,
    ),
    body,
    options,
  );
}

export function bulkIgnoreTextReviewSuggestions(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  checkId: string,
  body: SpellingDispositionBatch,
  options?: { signal?: AbortSignal },
) {
  return v1Client.post<DetectionResponse>(
    ocrPaths.textReviewCheckDispositionsBulk(
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
      checkId,
    ),
    body,
    options,
  );
}

export function rerunTextReview(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  body: RerunReviewRequest,
  options?: { signal?: AbortSignal },
) {
  return v1Client.post<RerunReviewResponse>(
    ocrPaths.textReviewChecksRerun(
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
    ),
    body,
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
