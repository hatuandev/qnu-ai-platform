import type { V1Client } from "@/app/api/v1";
import { compiledDocumentPaths, knowledgePaths } from "@/app/api/v1/endpoints";
import type {
  DocumentSummaryResponse,
  SourceSummaryResponse,
} from "./summary-types";

/** Read-only summary transport; GET never creates runs or enqueues work. */

export function getSourceSummary(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  params: {
    revisionId?: string;
    runsLimit?: number;
    derivationsLimit?: number;
  } = {},
  options?: { signal?: AbortSignal },
): Promise<SourceSummaryResponse> {
  return client.get<SourceSummaryResponse>(
    knowledgePaths.sourceSummary(workspaceId, collectionId, sourceId),
    {
      searchParams: {
        revision_id: params.revisionId,
        runs_limit: params.runsLimit,
        derivations_limit: params.derivationsLimit,
      },
      signal: options?.signal,
    },
  );
}

export function getCompiledDocumentSummary(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  documentId: string,
  params: { page?: number; pageSize?: number } = {},
  options?: { signal?: AbortSignal },
): Promise<DocumentSummaryResponse> {
  return client.get<DocumentSummaryResponse>(
    compiledDocumentPaths.summary(workspaceId, collectionId, documentId),
    {
      searchParams: {
        page: params.page ?? 1,
        page_size: params.pageSize ?? 20,
      },
      signal: options?.signal,
    },
  );
}
