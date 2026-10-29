import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import {
  createDetectCheck,
  dispatchProcessingRun,
  getDetectCheck,
  getProcessingRun,
  listProcessingRuns,
  readPageImageBlob,
  readPageRawBlob,
  readRenderedPdfBlob,
  readRunEvidence,
  readRunManifest,
  readTextReview,
  requestProcessingRun,
  saveTextReview,
} from "@/features/knowledge/ocr-requests";
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
// Query Key Factory
// ============================================================================

export const ocrQueryKeys = {
  root: (
    sessionId: number | undefined,
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "sources",
      sourceId,
      "revisions",
      revisionId,
      "ocr",
    ] as const,

  runs: (
    sessionId: number | undefined,
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    page = 1,
    pageSize = 20,
  ) =>
    [
      ...ocrQueryKeys.root(
        sessionId,
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
      ),
      "runs",
      { page, pageSize },
    ] as const,

  run: (
    sessionId: number | undefined,
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
  ) =>
    [
      ...ocrQueryKeys.root(
        sessionId,
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
      ),
      "run",
      runId,
    ] as const,

  manifest: (
    sessionId: number | undefined,
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
  ) =>
    [
      ...ocrQueryKeys.root(
        sessionId,
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
      ),
      "manifest",
      runId,
    ] as const,

  evidence: (
    sessionId: number | undefined,
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
  ) =>
    [
      ...ocrQueryKeys.root(
        sessionId,
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
      ),
      "evidence",
      runId,
    ] as const,

  review: (
    sessionId: number | undefined,
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
    version?: number | null,
  ) =>
    [
      ...ocrQueryKeys.root(
        sessionId,
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
      ),
      "review",
      runId,
      version ?? "latest",
    ] as const,

  check: (
    sessionId: number | undefined,
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    revisionId: string,
    runId: string,
    checkId: string,
  ) =>
    [
      ...ocrQueryKeys.root(
        sessionId,
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
      ),
      "checks",
      runId,
      checkId,
    ] as const,
};

// ============================================================================
// OCR Processing Runs Queries & Mutations
// ============================================================================

export function useProcessingRunsQuery(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  page = 1,
  pageSize = 20,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();

  return useQuery<ProcessingRunListResponse>({
    queryKey: ocrQueryKeys.runs(
      sessionId,
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      page,
      pageSize,
    ),
    queryFn: ({ signal }) =>
      listProcessingRuns(
        v1Client,
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        { page, page_size: pageSize },
        { signal },
      ),
    enabled:
      Boolean(workspaceId && collectionId && sourceId && revisionId) &&
      (options?.enabled ?? true),
    refetchInterval: (query) =>
      query.state.data?.items.some(
        (run) => run.status === "queued" || run.status === "running",
      )
        ? 2500
        : false,
  });
}

export function useProcessingRunDetailQuery(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string | null | undefined,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();

  return useQuery<ProcessingRunDetailResponse>({
    queryKey: ocrQueryKeys.run(
      sessionId,
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId ?? "",
    ),
    queryFn: ({ signal }) =>
      getProcessingRun(
        v1Client,
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId as string,
        { signal },
      ),
    enabled:
      Boolean(workspaceId && collectionId && sourceId && revisionId && runId) &&
      (options?.enabled ?? true),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "queued" || status === "running") {
        return 2500;
      }
      return false;
    },
  });
}

export function useRunManifestQuery(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string | null | undefined,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();

  return useQuery<Record<string, unknown>>({
    queryKey: ocrQueryKeys.manifest(
      sessionId,
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId ?? "",
    ),
    queryFn: ({ signal }) =>
      readRunManifest(
        v1Client,
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId as string,
        { signal },
      ),
    enabled:
      Boolean(workspaceId && collectionId && sourceId && revisionId && runId) &&
      (options?.enabled ?? true),
  });
}

export function useRunEvidenceQuery(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string | null | undefined,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();

  return useQuery<EvidenceSnapshotResponse>({
    queryKey: ocrQueryKeys.evidence(
      sessionId,
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId ?? "",
    ),
    queryFn: ({ signal }) =>
      readRunEvidence(
        v1Client,
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId as string,
        { signal },
      ),
    enabled:
      Boolean(workspaceId && collectionId && sourceId && revisionId && runId) &&
      (options?.enabled ?? true),
  });
}

export function useRequestProcessingRunMutation(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<
    ProcessingRunCreatedResponse,
    Error,
    ProcessingRunRequest | undefined
  >({
    mutationFn: (body) =>
      requestProcessingRun(
        v1Client,
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        body,
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ocrQueryKeys.root(
          sessionId,
          workspaceId,
          collectionId,
          sourceId,
          revisionId,
        ),
      });
    },
  });
}

export function useDispatchProcessingRunMutation(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<ProcessingRunResponse, Error, string>({
    mutationFn: (runId) =>
      dispatchProcessingRun(
        v1Client,
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId,
      ),
    onSuccess: (_data, runId) => {
      void queryClient.invalidateQueries({
        queryKey: ocrQueryKeys.run(
          sessionId,
          workspaceId,
          collectionId,
          sourceId,
          revisionId,
          runId,
        ),
      });
      void queryClient.invalidateQueries({
        queryKey: ocrQueryKeys.root(
          sessionId,
          workspaceId,
          collectionId,
          sourceId,
          revisionId,
        ),
      });
    },
  });
}

// ============================================================================
// Text Review Queries & Mutations
// ============================================================================

export function useTextReviewQuery(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string | null | undefined,
  version?: number | null,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();

  return useQuery<ReviewDocument>({
    queryKey: ocrQueryKeys.review(
      sessionId,
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId ?? "",
      version,
    ),
    queryFn: ({ signal }) =>
      readTextReview(
        v1Client,
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId as string,
        version,
        { signal },
      ),
    enabled:
      Boolean(workspaceId && collectionId && sourceId && revisionId && runId) &&
      (options?.enabled ?? true),
  });
}

export function useSaveTextReviewMutation(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<
    ReviewDocument,
    Error,
    { body: SaveReviewInput; idempotencyKey: string }
  >({
    mutationFn: ({ body, idempotencyKey }) =>
      saveTextReview(
        v1Client,
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId,
        body,
        idempotencyKey,
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ocrQueryKeys.root(
          sessionId,
          workspaceId,
          collectionId,
          sourceId,
          revisionId,
        ),
      });
    },
  });
}

export function useDetectCheckMutation(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
) {
  return useMutation<
    DetectionResponse,
    Error,
    { body: DetectRequestInput; idempotencyKey: string }
  >({
    mutationFn: ({ body, idempotencyKey }) =>
      createDetectCheck(
        v1Client,
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId,
        body,
        idempotencyKey,
      ),
  });
}

export function useDetectCheckQuery(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string,
  checkId: string | null | undefined,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();

  return useQuery<DetectionResponse>({
    queryKey: ocrQueryKeys.check(
      sessionId,
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
      checkId ?? "",
    ),
    queryFn: ({ signal }) =>
      getDetectCheck(
        v1Client,
        workspaceId,
        collectionId,
        sourceId,
        revisionId,
        runId,
        checkId as string,
        { signal },
      ),
    retry: false,
    refetchInterval: (q) => (q.state.data?.status === "running" ? 2500 : false),
    enabled:
      Boolean(
        workspaceId &&
          collectionId &&
          sourceId &&
          revisionId &&
          runId &&
          checkId,
      ) &&
      (options?.enabled ?? true),
  });
}

// ============================================================================
// Blob Hooks (with Safe Lifecycle & URL Revocation)
// ============================================================================

export function usePageImageBlobUrl(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string | null | undefined,
  pageNumber: number | null | undefined,
  runStatus?: string | null,
) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  const refetch = useCallback(() => {
    setRetryKey((k) => k + 1);
  }, []);

  useEffect(() => {
    if (!runId || !pageNumber || pageNumber < 1 || runStatus === "failed") {
      setBlobUrl(null);
      setIsLoading(false);
      setError(null);
      return;
    }
    void retryKey;
    let isSubscribed = true;
    setIsLoading(true);
    setError(null);

    readPageImageBlob(
      v1Client,
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
      pageNumber,
    )
      .then((res) => {
        if (!isSubscribed) return;
        const url = URL.createObjectURL(res.blob);
        setBlobUrl(url);
        setIsLoading(false);
      })
      .catch((err: unknown) => {
        if (!isSubscribed) return;
        setIsLoading(false);
        setError(
          err instanceof Error
            ? err.message
            : "Không tải được ảnh trang của lượt xử lý này.",
        );
      });

    return () => {
      isSubscribed = false;
      setBlobUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return null;
      });
    };
  }, [
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
    runId,
    pageNumber,
    runStatus,
    retryKey,
  ]);

  return { blobUrl, isLoading, error, refetch };
}

export function useRenderedPdfBlobUrl(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string | null | undefined,
  enabled = true,
) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  const refetch = useCallback(() => {
    setRetryKey((k) => k + 1);
  }, []);

  useEffect(() => {
    void retryKey;
    if (!enabled || !runId) {
      setBlobUrl(null);
      setIsLoading(false);
      setError(null);
      return;
    }

    let isSubscribed = true;
    setIsLoading(true);
    setError(null);

    readRenderedPdfBlob(
      v1Client,
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
    )
      .then((res) => {
        if (!isSubscribed) return;
        const url = URL.createObjectURL(res.blob);
        setBlobUrl(url);
        setIsLoading(false);
      })
      .catch((err: unknown) => {
        if (!isSubscribed) return;
        setIsLoading(false);
        setError(
          err instanceof Error
            ? err.message
            : "Không tải được bản PDF kết xuất.",
        );
      });

    return () => {
      isSubscribed = false;
      setBlobUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return null;
      });
    };
  }, [
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
    runId,
    enabled,
    retryKey,
  ]);

  return { blobUrl, isLoading, error, refetch };
}

export function usePageRawText(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  runId: string | null | undefined,
  pageNumber: number | null | undefined,
  enabled: boolean,
) {
  const [rawText, setRawText] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled || !runId || !pageNumber || pageNumber < 1) {
      setRawText(null);
      setIsLoading(false);
      setError(null);
      return;
    }

    let isSubscribed = true;
    setIsLoading(true);
    setError(null);

    readPageRawBlob(
      v1Client,
      workspaceId,
      collectionId,
      sourceId,
      revisionId,
      runId,
      pageNumber,
    )
      .then(async (res) => {
        if (!isSubscribed) return;
        const text = await res.blob.text();
        setRawText(text);
        setIsLoading(false);
      })
      .catch((err: unknown) => {
        if (!isSubscribed) return;
        setIsLoading(false);
        setError(
          err instanceof Error
            ? err.message
            : "Không tải được raw response của trang.",
        );
      });

    return () => {
      isSubscribed = false;
    };
  }, [
    enabled,
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
    runId,
    pageNumber,
  ]);

  return { rawText, isLoading, error };
}
