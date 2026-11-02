import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import {
  getDocumentIndexReadiness,
  getIndexRun,
  listIndexRuns,
  requestIndex,
  searchCollection,
} from "./index-requests";
import type {
  IndexCreated,
  IndexReadiness,
  IndexRun,
  SearchRequestInput,
  SearchResponse,
} from "./index-types";
import { readArrayPage } from "./list-pagination";

const TERMINAL: ReadonlySet<string> = new Set([
  "completed",
  "failed",
  "cancelled",
]);

/** A run that has not reached a terminal state yet keeps polling. */
export function isIndexRunActive(run: IndexRun | undefined): boolean {
  return Boolean(run && !TERMINAL.has(run.status));
}

export const indexingKeys = {
  all: (sessionId: number) => ["v1", sessionId, "indexing"] as const,
  runs: (sessionId: number, workspaceId: string, collectionId: string) =>
    ["v1", sessionId, "indexing", workspaceId, collectionId, "runs"] as const,
  run: (
    sessionId: number,
    workspaceId: string,
    collectionId: string,
    runId: string,
  ) =>
    [
      "v1",
      sessionId,
      "indexing",
      workspaceId,
      collectionId,
      "run",
      runId,
    ] as const,
};

export function useIndexRunsQuery(
  workspaceId: string,
  collectionId: string,
  options?: { enabled?: boolean; page?: number; pageSize?: number },
) {
  const { sessionId } = useV1Auth();
  return useQuery<IndexRun[]>({
    queryKey: [
      ...indexingKeys.runs(sessionId, workspaceId, collectionId),
      { page: options?.page, pageSize: options?.pageSize },
    ],
    queryFn: ({ signal }) => {
      const loadRows = (limit: number, offset: number) =>
        listIndexRuns(
          v1Client,
          workspaceId,
          collectionId,
          { limit, offset },
          { signal },
        );
      return options?.page
        ? readArrayPage(
            loadRows,
            options.pageSize ?? 20,
            (options.page - 1) * (options.pageSize ?? 20),
          )
        : loadRows(20, 0);
    },
    enabled: Boolean(workspaceId && collectionId) && (options?.enabled ?? true),
    // Real state only: poll while a generation is still being built.
    refetchInterval: (query) => {
      const runs = query.state.data;
      return runs?.some((run) => isIndexRunActive(run)) ? 3000 : false;
    },
  });
}

export function useDocumentIndexReadinessQuery(
  workspaceId: string,
  collectionId: string,
  documentId: string,
  publicationDecisionId: string | undefined,
  activeIndexId: string | undefined,
) {
  const { sessionId } = useV1Auth();
  return useQuery<IndexReadiness>({
    queryKey: [
      ...indexingKeys.all(sessionId),
      workspaceId,
      collectionId,
      "readiness",
      documentId,
      publicationDecisionId,
      activeIndexId,
    ],
    queryFn: ({ signal }) =>
      getDocumentIndexReadiness(
        v1Client,
        workspaceId,
        collectionId,
        documentId,
        { signal },
      ),
    enabled: Boolean(
      workspaceId && collectionId && documentId && publicationDecisionId,
    ),
    retry: false,
  });
}

export function useIndexRunQuery(
  workspaceId: string,
  collectionId: string,
  runId: string | null | undefined,
) {
  const { sessionId } = useV1Auth();
  return useQuery<IndexRun>({
    queryKey: indexingKeys.run(
      sessionId,
      workspaceId,
      collectionId,
      runId ?? "",
    ),
    queryFn: ({ signal }) =>
      getIndexRun(v1Client, workspaceId, collectionId, runId ?? "", { signal }),
    enabled: Boolean(workspaceId && collectionId && runId),
    refetchInterval: (query) =>
      isIndexRunActive(query.state.data) ? 3000 : false,
  });
}

/**
 * Requests a generation. `created: false` is a normal idempotent replay and is
 * surfaced to the caller instead of being treated as a fresh build.
 */
export function useRequestIndexMutation(
  workspaceId: string,
  collectionId: string,
) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation<
    IndexCreated,
    Error,
    {
      providerId: string | null;
      idempotencyKey: string;
      contextualSearch?: boolean;
    }
  >({
    mutationFn: ({ providerId, idempotencyKey, contextualSearch }) =>
      requestIndex(
        v1Client,
        workspaceId,
        collectionId,
        providerId,
        idempotencyKey,
        { contextualSearch },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: indexingKeys.runs(sessionId, workspaceId, collectionId),
      });
    },
  });
}

export function useSearchMutation(workspaceId: string, collectionId: string) {
  return useMutation<SearchResponse, Error, SearchRequestInput>({
    mutationFn: (input) =>
      searchCollection(v1Client, workspaceId, collectionId, input),
  });
}
