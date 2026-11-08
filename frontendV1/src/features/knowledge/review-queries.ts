import {
  type QueryClient,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { inboxKeys } from "@/features/inbox/inbox-queries";
import type { Page } from "@/features/workspaces/types";
import {
  commitSubmission,
  createSubmissionPreview,
  listSubmissions,
} from "./review-requests";
import type {
  SubmissionCommitRequest,
  SubmissionListParams,
  SubmissionOutcome,
  SubmissionPreviewRequest,
  SubmissionPreviewResponse,
  SubmissionResponse,
} from "./review-types";

export const reviewKeys = {
  submissionsRoot: (
    workspaceId: string,
    collectionId: string,
    sessionId?: number,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "review-submissions",
    ] as const,
  submissions: (
    workspaceId: string,
    collectionId: string,
    params: SubmissionListParams,
    sessionId?: number,
  ) =>
    [
      ...reviewKeys.submissionsRoot(workspaceId, collectionId, sessionId),
      {
        status: params.status ?? null,
        documentId: params.document_id ?? null,
        versionId: params.version_id ?? null,
        page: params.page,
        pageSize: params.pageSize,
      },
    ] as const,
};

/** Submission changes also change what the workspace inbox must show. */
export function invalidateSubmissionScopes(
  queryClient: QueryClient,
  sessionId: number | undefined,
  workspaceId: string,
  collectionId: string,
) {
  void queryClient.invalidateQueries({
    queryKey: reviewKeys.submissionsRoot(workspaceId, collectionId, sessionId),
  });
  void queryClient.invalidateQueries({
    queryKey: inboxKeys.all(workspaceId, sessionId),
  });
}

export function useVersionSubmissionsQuery(
  workspaceId: string,
  collectionId: string,
  documentId: string,
  versionId: string,
) {
  const { sessionId } = useV1Auth();
  return useQuery<Page<SubmissionResponse>>({
    queryKey: reviewKeys.submissions(
      workspaceId,
      collectionId,
      {
        document_id: documentId,
        version_id: versionId,
        page: 1,
        pageSize: 20,
      },
      sessionId,
    ),
    queryFn: ({ signal }) =>
      listSubmissions(
        v1Client,
        workspaceId,
        collectionId,
        {
          document_id: documentId,
          version_id: versionId,
          page: 1,
          pageSize: 20,
        },
        { signal },
      ),
    enabled: Boolean(workspaceId && collectionId && documentId && versionId),
  });
}

export function useSubmissionPreviewMutation(
  workspaceId: string,
  collectionId: string,
) {
  return useMutation<
    SubmissionPreviewResponse,
    Error,
    { input: SubmissionPreviewRequest }
  >({
    mutationFn: ({ input }) =>
      createSubmissionPreview(v1Client, workspaceId, collectionId, input),
    retry: 0,
  });
}

export function useCommitSubmissionMutation(
  workspaceId: string,
  collectionId: string,
) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation<
    SubmissionOutcome,
    Error,
    { input: SubmissionCommitRequest; idempotencyKey: string }
  >({
    mutationFn: ({ input, idempotencyKey }) =>
      commitSubmission(
        v1Client,
        workspaceId,
        collectionId,
        input,
        idempotencyKey,
      ),
    retry: 0,
    onSuccess: () => {
      invalidateSubmissionScopes(
        queryClient,
        sessionId,
        workspaceId,
        collectionId,
      );
    },
  });
}
