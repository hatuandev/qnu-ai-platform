import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import {
  acceptEdit,
  createCompilationReview,
  createCompilationRun,
  createEditPreview,
  getAutoReviewStatus,
  getCompilationDraft,
  getCompilationReview,
  getCompilationReviewReport,
  getCompilationRun,
  getEditContext,
  listCompilationReviews,
  listCompilationRuns,
} from "./compilation-requests";
import type {
  AcceptEditRequest,
  AutoReviewResponse,
  CompilationRequestInput,
  CompilationReviewResponse,
  DraftDocumentResponse,
  EditContextResponse,
  EditPreviewRequest,
  ReviewReportResponse,
  ReviewRequestInput,
} from "./compilation-types";
import { readArrayPage } from "./list-pagination";

// ==========================================
// Scoped Query Keys
// ==========================================

export const compilationKeys = {
  all: (sessionId?: number) => ["v1", sessionId, "compilations"] as const,
  runsRoot: (workspaceId: string, collectionId: string, sessionId?: number) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "compilation-runs",
    ] as const,
  reviewsRoot: (
    workspaceId: string,
    collectionId: string,
    runId: string,
    sessionId?: number,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "compilation-runs",
      runId,
      "reviews",
    ] as const,

  runs: (
    workspaceId: string,
    collectionId: string,
    limit?: number,
    sessionId?: number,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "compilation-runs",
      { limit },
    ] as const,

  run: (
    workspaceId: string,
    collectionId: string,
    runId: string,
    sessionId?: number,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "compilation-runs",
      runId,
    ] as const,

  draft: (
    workspaceId: string,
    collectionId: string,
    runId: string,
    sessionId?: number,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "compilation-runs",
      runId,
      "draft",
    ] as const,

  autoReview: (
    workspaceId: string,
    collectionId: string,
    runId: string,
    sessionId?: number,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "compilation-runs",
      runId,
      "auto-review",
    ] as const,

  reviews: (
    workspaceId: string,
    collectionId: string,
    runId: string,
    limit?: number,
    offset?: number,
    sessionId?: number,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "compilation-runs",
      runId,
      "reviews",
      { limit, offset },
    ] as const,

  review: (
    workspaceId: string,
    collectionId: string,
    runId: string,
    reviewId: string,
    sessionId?: number,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "compilation-runs",
      runId,
      "reviews",
      reviewId,
    ] as const,

  reviewReport: (
    workspaceId: string,
    collectionId: string,
    runId: string,
    reviewId: string,
    sessionId?: number,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "compilation-runs",
      runId,
      "reviews",
      reviewId,
      "report",
    ] as const,

  editContext: (
    workspaceId: string,
    collectionId: string,
    runId: string,
    sessionId?: number,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "compilation-runs",
      runId,
      "edit-context",
    ] as const,
};

// ==========================================
// Query Hooks
// ==========================================

export function useCompilationRunsQuery(
  workspaceId: string,
  collectionId: string,
  limit = 20,
  options?: { enabled?: boolean; lookahead?: boolean; offset?: number },
) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: [
      ...compilationKeys.runs(workspaceId, collectionId, limit, sessionId),
      { offset: options?.offset ?? 0, lookahead: options?.lookahead ?? false },
    ],
    queryFn: ({ signal }) => {
      const loadRows = (count: number, start: number) =>
        listCompilationRuns(v1Client, workspaceId, collectionId, count, {
          signal,
          offset: start,
        });
      return options?.lookahead
        ? readArrayPage(loadRows, limit, options.offset ?? 0)
        : loadRows(limit, options?.offset ?? 0);
    },
    enabled: Boolean(workspaceId && collectionId) && (options?.enabled ?? true),
  });
}

export function useCompilationRunQuery(
  workspaceId: string,
  collectionId: string,
  runId: string | null | undefined,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: compilationKeys.run(
      workspaceId,
      collectionId,
      runId ?? "",
      sessionId,
    ),
    queryFn: ({ signal }) => {
      if (!runId) throw new Error("runId is required");
      return getCompilationRun(v1Client, workspaceId, collectionId, runId, {
        signal,
      });
    },
    enabled:
      Boolean(workspaceId && collectionId && runId) &&
      (options?.enabled ?? true),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "queued" || status === "running") {
        return 3000;
      }
      return false;
    },
  });
}

export function useCompilationDraftQuery(
  workspaceId: string,
  collectionId: string,
  runId: string | null | undefined,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery<DraftDocumentResponse>({
    queryKey: compilationKeys.draft(
      workspaceId,
      collectionId,
      runId ?? "",
      sessionId,
    ),
    queryFn: ({ signal }) => {
      if (!runId) throw new Error("runId is required");
      return getCompilationDraft(v1Client, workspaceId, collectionId, runId, {
        signal,
      });
    },
    enabled:
      Boolean(workspaceId && collectionId && runId) &&
      (options?.enabled ?? true),
  });
}

export type AutoReviewQueryResult = AutoReviewResponse;

export function useAutoReviewQuery(
  workspaceId: string,
  collectionId: string,
  runId: string | null | undefined,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();
  const queryClient = useQueryClient();
  const query = useQuery<AutoReviewQueryResult>({
    queryKey: compilationKeys.autoReview(
      workspaceId,
      collectionId,
      runId ?? "",
      sessionId,
    ),
    queryFn: ({ signal }) => {
      if (!runId) throw new Error("runId is required");
      return getAutoReviewStatus(v1Client, workspaceId, collectionId, runId, {
        signal,
      });
    },
    enabled:
      Boolean(workspaceId && collectionId && runId) &&
      (options?.enabled ?? true),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (query.state.error) return false;
      // Intent can appear just after Compiler completes; do not poll an absent intent forever.
      if (data?.notScheduled && query.state.dataUpdateCount < 10) return 3000;
      if (data?.status === "queued" || data?.status === "running") {
        return 3000;
      }
      return false;
    },
  });
  const reviewId = query.data?.review_id;
  const status = query.data?.status;
  useEffect(() => {
    if (runId && reviewId && status) {
      void queryClient.invalidateQueries({
        queryKey: compilationKeys.reviewsRoot(
          workspaceId,
          collectionId,
          runId,
          sessionId,
        ),
      });
    }
  }, [
    queryClient,
    workspaceId,
    collectionId,
    runId,
    sessionId,
    reviewId,
    status,
  ]);
  return query;
}

export function useCompilationReviewsQuery(
  workspaceId: string,
  collectionId: string,
  runId: string | null | undefined,
  limit = 20,
  offset = 0,
  options?: { enabled?: boolean; lookahead?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery<CompilationReviewResponse[]>({
    queryKey: [
      ...compilationKeys.reviews(
        workspaceId,
        collectionId,
        runId ?? "",
        limit,
        offset,
        sessionId,
      ),
      { lookahead: options?.lookahead ?? false },
    ],
    queryFn: ({ signal }) => {
      if (!runId) throw new Error("runId is required");
      const loadRows = (count: number, start: number) =>
        listCompilationReviews(
          v1Client,
          workspaceId,
          collectionId,
          runId,
          count,
          start,
          { signal },
        );
      return options?.lookahead
        ? readArrayPage(loadRows, limit, offset)
        : loadRows(limit, offset);
    },
    enabled:
      Boolean(workspaceId && collectionId && runId) &&
      (options?.enabled ?? true),
  });
}

export function useCompilationReviewQuery(
  workspaceId: string,
  collectionId: string,
  runId: string | null | undefined,
  reviewId: string | null | undefined,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery<CompilationReviewResponse>({
    queryKey: compilationKeys.review(
      workspaceId,
      collectionId,
      runId ?? "",
      reviewId ?? "",
      sessionId,
    ),
    queryFn: ({ signal }) => {
      if (!runId || !reviewId) throw new Error("runId and reviewId required");
      return getCompilationReview(
        v1Client,
        workspaceId,
        collectionId,
        runId,
        reviewId,
        { signal },
      );
    },
    enabled:
      Boolean(workspaceId && collectionId && runId && reviewId) &&
      (options?.enabled ?? true),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "queued" || status === "running") {
        return 3000;
      }
      return false;
    },
  });
}

export function useCompilationReviewReportQuery(
  workspaceId: string,
  collectionId: string,
  runId: string | null | undefined,
  reviewId: string | null | undefined,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery<ReviewReportResponse>({
    queryKey: compilationKeys.reviewReport(
      workspaceId,
      collectionId,
      runId ?? "",
      reviewId ?? "",
      sessionId,
    ),
    queryFn: ({ signal }) => {
      if (!runId || !reviewId) throw new Error("runId and reviewId required");
      return getCompilationReviewReport(
        v1Client,
        workspaceId,
        collectionId,
        runId,
        reviewId,
        { signal },
      );
    },
    enabled:
      Boolean(workspaceId && collectionId && runId && reviewId) &&
      (options?.enabled ?? true),
  });
}

export function useEditContextQuery(
  workspaceId: string,
  collectionId: string,
  runId: string | null | undefined,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery<EditContextResponse>({
    queryKey: compilationKeys.editContext(
      workspaceId,
      collectionId,
      runId ?? "",
      sessionId,
    ),
    queryFn: ({ signal }) => {
      if (!runId) throw new Error("runId is required");
      return getEditContext(v1Client, workspaceId, collectionId, runId, {
        signal,
      });
    },
    enabled:
      Boolean(workspaceId && collectionId && runId) &&
      (options?.enabled ?? true),
  });
}

// ==========================================
// Mutation Hooks (retry: 0 for single submit)
// ==========================================

export function useCreateCompilationMutation(
  workspaceId: string,
  collectionId: string,
) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation({
    mutationFn: (args: {
      input: CompilationRequestInput;
      idempotencyKey: string;
    }) =>
      createCompilationRun(
        v1Client,
        workspaceId,
        collectionId,
        args.input,
        args.idempotencyKey,
      ),
    retry: 0,
    onSuccess: (data) => {
      void queryClient.invalidateQueries({
        queryKey: compilationKeys.runsRoot(
          workspaceId,
          collectionId,
          sessionId,
        ),
      });
      if (data.run?.id) {
        queryClient.setQueryData(
          compilationKeys.run(
            workspaceId,
            collectionId,
            data.run.id,
            sessionId,
          ),
          data.run,
        );
      }
    },
  });
}

export function useCreateReviewMutation(
  workspaceId: string,
  collectionId: string,
  runId: string,
) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation({
    mutationFn: (args: { input: ReviewRequestInput; idempotencyKey: string }) =>
      createCompilationReview(
        v1Client,
        workspaceId,
        collectionId,
        runId,
        args.input,
        args.idempotencyKey,
      ),
    retry: 0,
    onSuccess: (review) => {
      void queryClient.invalidateQueries({
        queryKey: compilationKeys.reviewsRoot(
          workspaceId,
          collectionId,
          runId,
          sessionId,
        ),
      });
      if (review?.id) {
        queryClient.setQueryData(
          compilationKeys.review(
            workspaceId,
            collectionId,
            runId,
            review.id,
            sessionId,
          ),
          review,
        );
      }
    },
  });
}

export function useCreateEditPreviewMutation(
  workspaceId: string,
  collectionId: string,
  runId: string,
) {
  return useMutation({
    mutationFn: (input: EditPreviewRequest) =>
      createEditPreview(v1Client, workspaceId, collectionId, runId, input),
    retry: 0,
  });
}

export function useAcceptEditMutation(
  workspaceId: string,
  collectionId: string,
  runId: string,
) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation({
    mutationFn: (args: { input: AcceptEditRequest; idempotencyKey: string }) =>
      acceptEdit(
        v1Client,
        workspaceId,
        collectionId,
        runId,
        args.input,
        args.idempotencyKey,
      ),
    retry: 0,
    onSuccess: (data) => {
      void queryClient.invalidateQueries({
        queryKey: compilationKeys.runsRoot(
          workspaceId,
          collectionId,
          sessionId,
        ),
      });
      if (data.run?.id) {
        queryClient.setQueryData(
          compilationKeys.run(
            workspaceId,
            collectionId,
            data.run.id,
            sessionId,
          ),
          data.run,
        );
      }
    },
  });
}
