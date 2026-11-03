import {
  ApiProblemError,
  type BlobResponse,
  type V1Client,
} from "../../app/api/v1/client.ts";
import { compilationPaths } from "../../app/api/v1/endpoints.ts";
import { validateReviewIdempotencyKey } from "./compilation-schemas.ts";
import type {
  AcceptEditRequest,
  AutoReviewResponse,
  CompilationCreatedResponse,
  CompilationRequestInput,
  CompilationReviewResponse,
  CompilationRunResponse,
  DraftDocumentResponse,
  EditContextResponse,
  EditPreviewRequest,
  EditPreviewResponse,
  ReviewProgressResponse,
  ReviewReportResponse,
  ReviewRequestInput,
} from "./compilation-types";

// ==========================================
// Compilation Runs API
// ==========================================

export async function createCompilationRun(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  input: CompilationRequestInput,
  idempotencyKey: string,
  options?: { signal?: AbortSignal },
): Promise<CompilationCreatedResponse> {
  const path = compilationPaths.runs(workspaceId, collectionId);
  return client.post<CompilationCreatedResponse>(path, input, {
    idempotencyKey,
    signal: options?.signal,
  });
}

export async function listCompilationRuns(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  limit = 20,
  options?: { signal?: AbortSignal; offset?: number },
): Promise<CompilationRunResponse[]> {
  const path = compilationPaths.runs(workspaceId, collectionId);
  return client.get<CompilationRunResponse[]>(path, {
    searchParams: { limit, offset: options?.offset },
    signal: options?.signal,
  });
}

export async function getCompilationRun(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  runId: string,
  options?: { signal?: AbortSignal },
): Promise<CompilationRunResponse> {
  const path = compilationPaths.run(workspaceId, collectionId, runId);
  return client.get<CompilationRunResponse>(path, {
    signal: options?.signal,
  });
}

export async function getCompilationDraft(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  runId: string,
  options?: { signal?: AbortSignal },
): Promise<DraftDocumentResponse> {
  const path = compilationPaths.draft(workspaceId, collectionId, runId);
  return client.get<DraftDocumentResponse>(path, {
    signal: options?.signal,
  });
}

export async function downloadCompilationMarkdownBlob(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  runId: string,
  options?: { signal?: AbortSignal },
): Promise<BlobResponse> {
  const path = compilationPaths.markdown(workspaceId, collectionId, runId);
  return client.requestBlob(path, {
    method: "GET",
    signal: options?.signal,
  });
}

export async function getCompilationRaw(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  runId: string,
  options?: { signal?: AbortSignal },
): Promise<BlobResponse> {
  const path = compilationPaths.raw(workspaceId, collectionId, runId);
  return client.requestBlob(path, {
    method: "GET",
    signal: options?.signal,
  });
}

// ==========================================
// Auto-review API
// ==========================================

export async function getAutoReviewStatus(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  runId: string,
  options?: { signal?: AbortSignal },
): Promise<AutoReviewResponse> {
  const path = compilationPaths.autoReview(workspaceId, collectionId, runId);
  try {
    return await client.get<AutoReviewResponse>(path, {
      signal: options?.signal,
    });
  } catch (err) {
    if (
      err instanceof ApiProblemError &&
      err.status === 404 &&
      (err.code === "compilation_auto_review_not_found" ||
        (err.code === "http_404" &&
          err.problem?.type?.split("/").at(-1) ===
            "compilation_auto_review_not_found"))
    ) {
      return {
        compilation_run_id: runId,
        status: "none",
        review_id: null,
        error_code: null,
        created_at: "",
        finished_at: null,
        notScheduled: true,
      };
    }
    throw err;
  }
}

// ==========================================
// Manual Review API
// ==========================================

export async function createCompilationReview(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  runId: string,
  input: ReviewRequestInput,
  idempotencyKey: string,
  options?: { signal?: AbortSignal; background?: boolean },
): Promise<CompilationReviewResponse> {
  if (!validateReviewIdempotencyKey(idempotencyKey)) {
    throw new Error(
      "Idempotency-Key không hợp lệ hoặc dùng tiền tố bị cấm (auto:, edit:).",
    );
  }
  const path = compilationPaths.reviews(workspaceId, collectionId, runId);
  return client.post<CompilationReviewResponse>(
    options?.background ? `${path}?background=true` : path,
    input,
    {
      idempotencyKey,
      signal: options?.signal,
    },
  );
}

export function cancelCompilationReview(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  runId: string,
  reviewId: string,
) {
  const path = compilationPaths.review(
    workspaceId,
    collectionId,
    runId,
    reviewId,
  );
  return client.post<CompilationReviewResponse>(`${path}/cancel`, {});
}

export async function listCompilationReviews(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  runId: string,
  limit = 20,
  offset = 0,
  options?: { signal?: AbortSignal },
): Promise<CompilationReviewResponse[]> {
  const path = compilationPaths.reviews(workspaceId, collectionId, runId);
  return client.get<CompilationReviewResponse[]>(path, {
    searchParams: { limit, offset },
    signal: options?.signal,
  });
}

export async function getCompilationReview(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  runId: string,
  reviewId: string,
  options?: { signal?: AbortSignal },
): Promise<CompilationReviewResponse> {
  const path = compilationPaths.review(
    workspaceId,
    collectionId,
    runId,
    reviewId,
  );
  return client.get<CompilationReviewResponse>(path, {
    signal: options?.signal,
  });
}

export async function getCompilationReviewProgress(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  runId: string,
  reviewId: string,
  options?: { signal?: AbortSignal },
): Promise<ReviewProgressResponse> {
  const path = compilationPaths.review(
    workspaceId,
    collectionId,
    runId,
    reviewId,
  );
  return client.get<ReviewProgressResponse>(`${path}/progress`, {
    signal: options?.signal,
  });
}

export async function getCompilationReviewReport(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  runId: string,
  reviewId: string,
  options?: { signal?: AbortSignal },
): Promise<ReviewReportResponse> {
  const path = compilationPaths.reviewReport(
    workspaceId,
    collectionId,
    runId,
    reviewId,
  );
  return client.get<ReviewReportResponse>(path, {
    signal: options?.signal,
  });
}

export async function downloadCompilationReviewMarkdownBlob(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  runId: string,
  reviewId: string,
  options?: { signal?: AbortSignal },
): Promise<BlobResponse> {
  const path = compilationPaths.reviewMarkdown(
    workspaceId,
    collectionId,
    runId,
    reviewId,
  );
  return client.requestBlob(path, {
    method: "GET",
    signal: options?.signal,
  });
}

export async function getCompilationReviewRaw(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  runId: string,
  reviewId: string,
  options?: { signal?: AbortSignal },
): Promise<BlobResponse> {
  const path = compilationPaths.reviewRaw(
    workspaceId,
    collectionId,
    runId,
    reviewId,
  );
  return client.requestBlob(path, {
    method: "GET",
    signal: options?.signal,
  });
}

// ==========================================
// Editing Workflow API
// ==========================================

export async function getEditContext(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  runId: string,
  options?: { signal?: AbortSignal },
): Promise<EditContextResponse> {
  const path = compilationPaths.editContext(workspaceId, collectionId, runId);
  return client.get<EditContextResponse>(path, {
    signal: options?.signal,
  });
}

export async function createEditPreview(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  runId: string,
  input: EditPreviewRequest,
  options?: { signal?: AbortSignal },
): Promise<EditPreviewResponse> {
  const path = compilationPaths.editPreviews(workspaceId, collectionId, runId);
  return client.post<EditPreviewResponse>(path, input, {
    signal: options?.signal,
  });
}

export async function acceptEdit(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  runId: string,
  input: AcceptEditRequest,
  idempotencyKey: string,
  options?: { signal?: AbortSignal },
): Promise<CompilationCreatedResponse> {
  const path = compilationPaths.edits(workspaceId, collectionId, runId);
  return client.post<CompilationCreatedResponse>(path, input, {
    idempotencyKey,
    signal: options?.signal,
  });
}
