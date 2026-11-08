import type { V1Client } from "../../app/api/v1/client.ts";
import { reviewSubmissionPaths } from "../../app/api/v1/endpoints.ts";
import type { Page } from "../workspaces/types.ts";
import type {
  SubmissionCommitRequest,
  SubmissionListParams,
  SubmissionOutcome,
  SubmissionPreviewRequest,
  SubmissionPreviewResponse,
  SubmissionResponse,
} from "./review-types.ts";

export function createSubmissionPreview(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  input: SubmissionPreviewRequest,
  options?: { signal?: AbortSignal },
): Promise<SubmissionPreviewResponse> {
  return client.post<SubmissionPreviewResponse>(
    reviewSubmissionPaths.previews(workspaceId, collectionId),
    input,
    { signal: options?.signal },
  );
}

export function commitSubmission(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  input: SubmissionCommitRequest,
  idempotencyKey: string,
  options?: { signal?: AbortSignal },
): Promise<SubmissionOutcome> {
  return client.post<SubmissionOutcome>(
    reviewSubmissionPaths.submissions(workspaceId, collectionId),
    input,
    { idempotencyKey, signal: options?.signal },
  );
}

export function listSubmissions(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  params: SubmissionListParams,
  options?: { signal?: AbortSignal },
): Promise<Page<SubmissionResponse>> {
  return client.get<Page<SubmissionResponse>>(
    reviewSubmissionPaths.submissions(workspaceId, collectionId),
    {
      searchParams: {
        status: params.status,
        document_id: params.document_id,
        version_id: params.version_id,
        page: params.page,
        page_size: params.pageSize,
      },
      signal: options?.signal,
    },
  );
}
