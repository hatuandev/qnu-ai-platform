/**
 * TanStack Query hooks for OCR & Text Review domain.
 */

import {
  type QueryClient,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  acknowledgeOcrWarnings,
  bulkIgnoreTextReviewSuggestions,
  type DetectionResponse,
  type DetectRequest,
  detectTextReview,
  getSpellingStatus,
  getTextReview,
  getTextReviewCheck,
  getTextReviewJson,
  getTextReviewMarkdown,
  listTextReviewChecks,
  listTextReviewVersions,
  type RerunReviewRequest,
  rerunTextReview,
  type SaveReview,
  type SpellingDisposition,
  type SpellingDispositionBatch,
  saveTextReview,
  setTextReviewDisposition,
} from "./requests";

export const ocrReviewKeys = {
  all: ["v1", "ocr-review"] as const,

  review: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
    version?: number,
  ) =>
    [
      ...ocrReviewKeys.all,
      "review",
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
      version ?? "latest",
    ] as const,

  markdown: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
    version?: number,
  ) =>
    [
      ...ocrReviewKeys.all,
      "markdown",
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
      version ?? "latest",
    ] as const,

  json: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
    version?: number,
  ) =>
    [
      ...ocrReviewKeys.all,
      "json",
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
      version ?? "latest",
    ] as const,

  checks: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
    version?: number,
  ) =>
    [
      ...ocrReviewKeys.all,
      "checks",
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
      version ?? "latest",
    ] as const,

  check: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
    checkId: string,
  ) =>
    [
      ...ocrReviewKeys.all,
      "check",
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
      checkId,
    ] as const,

  checksAll: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
  ) =>
    [
      ...ocrReviewKeys.all,
      "checks",
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
    ] as const,

  checkAll: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
  ) =>
    [
      ...ocrReviewKeys.all,
      "check",
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
    ] as const,

  versions: (
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
  ) =>
    [
      ...ocrReviewKeys.all,
      "versions",
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
    ] as const,
};

export function useTextReviewQuery(
  workspaceId?: string | null,
  collectionId?: string | null,
  sourceId?: string | null,
  revisionId?: string | null,
  runId?: string | null,
  version?: number,
) {
  const enabled = Boolean(
    workspaceId && collectionId && sourceId && revisionId && runId,
  );
  return useQuery({
    queryKey: enabled
      ? ocrReviewKeys.review(
          workspaceId as string,
          collectionId as string,
          sourceId as string,
          revisionId as string,
          runId as string,
          version,
        )
      : [...ocrReviewKeys.all, "review", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !collectionId || !sourceId || !revisionId || !runId) {
        throw new Error("Missing required parameters for text review");
      }
      return getTextReview(
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId,
        version,
        { signal },
      );
    },
    enabled,
    staleTime: 30_000,
  });
}

export function useTextReviewMarkdownQuery(
  workspaceId?: string | null,
  collectionId?: string | null,
  sourceId?: string | null,
  revisionId?: string | null,
  runId?: string | null,
  version?: number,
) {
  const enabled = Boolean(
    workspaceId && collectionId && sourceId && revisionId && runId,
  );
  return useQuery({
    queryKey: enabled
      ? ocrReviewKeys.markdown(
          workspaceId as string,
          collectionId as string,
          sourceId as string,
          revisionId as string,
          runId as string,
          version,
        )
      : [...ocrReviewKeys.all, "markdown", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !collectionId || !sourceId || !revisionId || !runId) {
        throw new Error("Missing required parameters for text review markdown");
      }
      return getTextReviewMarkdown(
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId,
        version,
        { signal },
      );
    },
    enabled,
    staleTime: 30_000,
  });
}

export function useTextReviewJsonQuery(
  workspaceId?: string | null,
  collectionId?: string | null,
  sourceId?: string | null,
  revisionId?: string | null,
  runId?: string | null,
  version?: number,
) {
  const enabled = Boolean(
    workspaceId && collectionId && sourceId && revisionId && runId,
  );
  return useQuery({
    queryKey: enabled
      ? ocrReviewKeys.json(
          workspaceId as string,
          collectionId as string,
          sourceId as string,
          revisionId as string,
          runId as string,
          version,
        )
      : [...ocrReviewKeys.all, "json", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !collectionId || !sourceId || !revisionId || !runId) {
        throw new Error("Missing required parameters for text review json");
      }
      return getTextReviewJson(
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId,
        version,
        { signal },
      );
    },
    enabled,
    staleTime: 30_000,
  });
}

export function useTextReviewChecksQuery(
  workspaceId?: string | null,
  collectionId?: string | null,
  sourceId?: string | null,
  revisionId?: string | null,
  runId?: string | null,
  version?: number,
  options?: {
    shouldPoll?: (checks: DetectionResponse[] | undefined) => boolean;
  },
) {
  const enabled = Boolean(
    workspaceId && collectionId && sourceId && revisionId && runId,
  );
  return useQuery({
    queryKey: enabled
      ? ocrReviewKeys.checks(
          workspaceId as string,
          collectionId as string,
          sourceId as string,
          revisionId as string,
          runId as string,
          version,
        )
      : [...ocrReviewKeys.all, "checks", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !collectionId || !sourceId || !revisionId || !runId) {
        throw new Error("Missing required parameters for text review checks");
      }
      return listTextReviewChecks(
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId,
        version,
        { signal },
      );
    },
    enabled,
    staleTime: 10_000,
    refetchInterval: (query) =>
      options?.shouldPoll?.(query.state.data) ? 5000 : false,
  });
}

export function useSpellingStatusQuery(
  workspaceId: string | null | undefined,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  version: number,
  isPreparing: boolean,
) {
  return useQuery({
    queryKey: [
      ...ocrReviewKeys.all,
      "spelling-summary",
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
      version,
    ],
    queryFn: ({ signal }) => {
      if (!workspaceId)
        throw new Error("Missing workspace for spelling status");
      return getSpellingStatus(
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId,
        version,
        { signal },
      );
    },
    enabled: Boolean(
      workspaceId && collectionId && sourceId && revisionId && runId,
    ),
    staleTime: 5_000,
    refetchInterval: (query) => {
      const status = query.state.data;
      return status?.running || (isPreparing && !status?.check) ? 5000 : false;
    },
  });
}

export function useTextReviewCheckQuery(
  workspaceId?: string | null,
  collectionId?: string | null,
  sourceId?: string | null,
  revisionId?: string | null,
  runId?: string | null,
  checkId?: string | null,
) {
  const enabled = Boolean(
    workspaceId && collectionId && sourceId && revisionId && runId && checkId,
  );
  return useQuery({
    queryKey: enabled
      ? ocrReviewKeys.check(
          workspaceId as string,
          collectionId as string,
          sourceId as string,
          revisionId as string,
          runId as string,
          checkId as string,
        )
      : [...ocrReviewKeys.all, "check", "empty"],
    queryFn: ({ signal }) => {
      if (
        !workspaceId ||
        !collectionId ||
        !sourceId ||
        !revisionId ||
        !runId ||
        !checkId
      ) {
        throw new Error("Missing required parameters for text review check");
      }
      return getTextReviewCheck(
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId,
        checkId,
        { signal },
      );
    },
    enabled,
    staleTime: 30_000,
  });
}

export function useTextReviewVersionsQuery(
  workspaceId?: string | null,
  collectionId?: string | null,
  sourceId?: string | null,
  revisionId?: string | null,
  runId?: string | null,
) {
  const enabled = Boolean(
    workspaceId && collectionId && sourceId && revisionId && runId,
  );
  return useQuery({
    queryKey: enabled
      ? ocrReviewKeys.versions(
          workspaceId as string,
          collectionId as string,
          sourceId as string,
          revisionId as string,
          runId as string,
        )
      : [...ocrReviewKeys.all, "versions", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !collectionId || !sourceId || !revisionId || !runId) {
        throw new Error("Missing required parameters for text review versions");
      }
      return listTextReviewVersions(
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId,
        { signal },
      );
    },
    enabled,
    staleTime: 30_000,
  });
}

export function useSaveTextReviewMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
  sourceId?: string | null,
  revisionId?: string | null,
  runId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      body,
      idempotencyKey,
    }: {
      body: SaveReview;
      idempotencyKey: string;
    }) => {
      if (!workspaceId || !collectionId || !sourceId || !revisionId || !runId) {
        throw new Error("Missing required parameters to save text review");
      }
      return saveTextReview(
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId,
        body,
        idempotencyKey,
      );
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ocrReviewKeys.all });
    },
  });
}

export function useDetectTextReviewMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
  sourceId?: string | null,
  revisionId?: string | null,
  runId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      body,
      idempotencyKey,
    }: {
      body: DetectRequest;
      idempotencyKey: string;
    }) => {
      if (!workspaceId || !collectionId || !sourceId || !revisionId || !runId) {
        throw new Error("Missing required parameters to detect text review");
      }
      return detectTextReview(
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId,
        body,
        idempotencyKey,
      );
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ocrReviewKeys.all });
    },
  });
}

export function useRerunTextReviewMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
  sourceId?: string | null,
  revisionId?: string | null,
  runId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: RerunReviewRequest) => {
      if (!workspaceId || !collectionId || !sourceId || !revisionId || !runId) {
        throw new Error("Missing required parameters to rerun text review");
      }
      return rerunTextReview(
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId,
        body,
      );
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ocrReviewKeys.all });
    },
  });
}

function storeUpdatedCheck(
  queryClient: QueryClient,
  scope: {
    workspaceId: string;
    collectionId: string;
    sourceId: string;
    revisionId: string;
    runId: string;
  },
  updated: DetectionResponse,
) {
  queryClient.setQueryData(
    ocrReviewKeys.check(
      scope.workspaceId,
      scope.collectionId,
      scope.sourceId,
      scope.revisionId,
      scope.runId,
      updated.id,
    ),
    updated,
  );
  const replaceCheck = (
    checks: DetectionResponse[] | undefined,
  ): DetectionResponse[] | undefined =>
    checks?.map((check) => (check.id === updated.id ? updated : check));
  queryClient.setQueriesData<DetectionResponse[]>(
    {
      queryKey: ocrReviewKeys.checksAll(
        scope.workspaceId,
        scope.collectionId,
        scope.sourceId,
        scope.revisionId,
        scope.runId,
      ),
    },
    replaceCheck,
  );
  void queryClient.invalidateQueries({
    queryKey: [
      ...ocrReviewKeys.all,
      "spelling-summary",
      scope.workspaceId,
      scope.collectionId,
      scope.sourceId,
      scope.revisionId,
      scope.runId,
    ],
  });
}

export function useSetTextReviewDispositionMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
  sourceId?: string | null,
  revisionId?: string | null,
  runId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      checkId,
      body,
    }: {
      checkId: string;
      body: SpellingDisposition;
    }) => {
      if (!workspaceId || !collectionId || !sourceId || !revisionId || !runId) {
        throw new Error(
          "Missing required parameters to set a spelling disposition",
        );
      }
      return setTextReviewDisposition(
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId,
        checkId,
        body,
      );
    },
    onSuccess: (updated) => {
      if (!workspaceId || !collectionId || !sourceId || !revisionId || !runId) {
        return;
      }
      storeUpdatedCheck(
        queryClient,
        { workspaceId, collectionId, sourceId, revisionId, runId },
        updated,
      );
    },
  });
}

export function useBulkIgnoreTextReviewSuggestionsMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
  sourceId?: string | null,
  revisionId?: string | null,
  runId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      checkId,
      body,
    }: {
      checkId: string;
      body: SpellingDispositionBatch;
    }) => {
      if (!workspaceId || !collectionId || !sourceId || !revisionId || !runId) {
        throw new Error(
          "Missing required parameters to ignore spelling suggestions",
        );
      }
      return bulkIgnoreTextReviewSuggestions(
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId,
        checkId,
        body,
      );
    },
    onSuccess: (updated) => {
      if (!workspaceId || !collectionId || !sourceId || !revisionId || !runId) {
        return;
      }
      storeUpdatedCheck(
        queryClient,
        { workspaceId, collectionId, sourceId, revisionId, runId },
        updated,
      );
    },
  });
}

export function useAcknowledgeOcrWarningsMutation(
  workspaceId?: string | null,
  collectionId?: string | null,
  sourceId?: string | null,
  revisionId?: string | null,
  runId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { reason: string }) => {
      if (!workspaceId || !collectionId || !sourceId || !revisionId || !runId) {
        throw new Error(
          "Missing required parameters to acknowledge OCR warnings",
        );
      }
      return acknowledgeOcrWarnings(
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId,
        body,
      );
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ocrReviewKeys.all });
    },
  });
}
