import { type QueryClient, useQuery } from "@tanstack/react-query";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import {
  getCompiledDocumentSummary,
  getSourceSummary,
} from "./summary-requests";
import type {
  DocumentSummaryResponse,
  SourceSummaryResponse,
} from "./summary-types";

const ACTIVE_TASK_POLL_MS = 3000;

const TERMINAL_PROCESSING_STATUSES = new Set([
  "completed",
  "failed",
  "uncertain",
  "cancelled",
]);

const ACTIVE_COMPILATION_STATUSES = new Set(["queued", "running"]);

/**
 * A source summary keeps polling only while a real task can still change it.
 * A later OCR run that merely exists is not treated as active proof.
 */
export function hasActiveSourceTask(
  summary: SourceSummaryResponse | undefined,
): boolean {
  if (!summary) return false;
  if (summary.active_run_id) return true;
  return (
    summary.processing_runs.some(
      (run) => !TERMINAL_PROCESSING_STATUSES.has(run.status),
    ) ||
    summary.derivations.some((item) =>
      ACTIVE_COMPILATION_STATUSES.has(item.compilation_status),
    )
  );
}

export function isSourceSummaryKey(
  key: readonly unknown[],
  sessionId: number,
  workspaceId: string,
  collectionId: string,
): boolean {
  return (
    key[0] === "v1" &&
    key[1] === sessionId &&
    key[2] === "workspaces" &&
    key[3] === workspaceId &&
    key[4] === "collections" &&
    key[5] === collectionId &&
    key[6] === "sources" &&
    typeof key[7] === "string" &&
    key[8] === "summary"
  );
}

/** Lineage changes without a known source id (new compilation, registration, decision). */
export function invalidateSourceSummaries(
  queryClient: QueryClient,
  sessionId: number,
  workspaceId: string,
  collectionId: string,
): void {
  void queryClient.invalidateQueries({
    predicate: (query) =>
      isSourceSummaryKey(query.queryKey, sessionId, workspaceId, collectionId),
  });
}

export const summaryKeys = {
  sourceBase: (
    sessionId: number,
    workspaceId: string,
    collectionId: string,
    sourceId: string,
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
      "summary",
    ] as const,

  source: (
    sessionId: number,
    workspaceId: string,
    collectionId: string,
    sourceId: string,
    params: {
      revisionId?: string;
      runsLimit?: number;
      derivationsLimit?: number;
    },
  ) =>
    [
      ...summaryKeys.sourceBase(sessionId, workspaceId, collectionId, sourceId),
      params,
    ] as const,

  documentBase: (
    sessionId: number,
    workspaceId: string,
    collectionId: string,
    documentId: string,
  ) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "collections",
      collectionId,
      "compiled-documents",
      documentId,
      "summary",
    ] as const,

  document: (
    sessionId: number,
    workspaceId: string,
    collectionId: string,
    documentId: string,
    params: { page: number; pageSize: number },
  ) =>
    [
      ...summaryKeys.documentBase(
        sessionId,
        workspaceId,
        collectionId,
        documentId,
      ),
      params,
    ] as const,
};

export function useSourceSummaryQuery(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  revisionId: string,
  options?: {
    enabled?: boolean;
    runsLimit?: number;
    derivationsLimit?: number;
  },
) {
  const { sessionId } = useV1Auth();
  const runsLimit = options?.runsLimit ?? 10;
  const derivationsLimit = options?.derivationsLimit ?? 20;
  return useQuery<SourceSummaryResponse>({
    queryKey: summaryKeys.source(
      sessionId,
      workspaceId,
      collectionId,
      sourceId,
      {
        revisionId,
        runsLimit,
        derivationsLimit,
      },
    ),
    queryFn: ({ signal }) =>
      getSourceSummary(
        v1Client,
        workspaceId,
        collectionId,
        sourceId,
        { revisionId, runsLimit, derivationsLimit },
        { signal },
      ),
    enabled:
      Boolean(workspaceId && collectionId && sourceId && revisionId) &&
      (options?.enabled ?? true),
    refetchInterval: (query) =>
      hasActiveSourceTask(query.state.data) ? ACTIVE_TASK_POLL_MS : false,
  });
}

export function useCompiledDocumentSummaryQuery(
  workspaceId: string,
  collectionId: string,
  documentId: string,
  page = 1,
  pageSize = 20,
  options?: { enabled?: boolean; isActiveTask?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery<DocumentSummaryResponse>({
    queryKey: summaryKeys.document(
      sessionId,
      workspaceId,
      collectionId,
      documentId,
      { page, pageSize },
    ),
    queryFn: ({ signal }) =>
      getCompiledDocumentSummary(
        v1Client,
        workspaceId,
        collectionId,
        documentId,
        { page, pageSize },
        { signal },
      ),
    enabled:
      Boolean(workspaceId && collectionId && documentId) &&
      (options?.enabled ?? true),
    // The page's existing search-sync query owns the active-task signal; this
    // summary stops as soon as that task reaches a terminal state.
    refetchInterval: options?.isActiveTask ? ACTIVE_TASK_POLL_MS : false,
  });
}
