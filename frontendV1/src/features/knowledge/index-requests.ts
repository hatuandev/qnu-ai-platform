import type { V1Client } from "@/app/api/v1";
import { indexingPaths } from "@/app/api/v1";
import type {
  IndexCreated,
  IndexReadiness,
  IndexRun,
  SearchRequestInput,
  SearchResponse,
} from "./index-types";

/**
 * Index generation and search transport.
 * Mirrors `backendV1/qnu/domains/knowledge/index/router.py`; no invented fields.
 */

export async function listIndexRuns(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  params: { limit?: number; offset?: number } = {},
  options?: { signal?: AbortSignal },
): Promise<IndexRun[]> {
  return client.get<IndexRun[]>(indexingPaths.runs(workspaceId, collectionId), {
    searchParams: {
      limit: params.limit ?? 20,
      offset: params.offset ?? 0,
    },
    signal: options?.signal,
  });
}

export async function getDocumentIndexReadiness(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  documentId: string,
  options?: { signal?: AbortSignal },
): Promise<IndexReadiness> {
  return client.get<IndexReadiness>(
    `/workspaces/${encodeURIComponent(workspaceId)}/collections/${encodeURIComponent(collectionId)}/compiled-documents/${encodeURIComponent(documentId)}/index-readiness`,
    { signal: options?.signal },
  );
}

export async function getIndexRun(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  runId: string,
  options?: { signal?: AbortSignal },
): Promise<IndexRun> {
  return client.get<IndexRun>(
    indexingPaths.run(workspaceId, collectionId, runId),
    { signal: options?.signal },
  );
}

/**
 * Requests a new index generation. The backend returns `created: false` when the
 * idempotency key was already used, so the caller must reuse the same key for a
 * retry of the same intent and a new key for a genuinely new request.
 */
export async function requestIndex(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  providerId: string | null,
  idempotencyKey: string,
  options?: { signal?: AbortSignal; contextualSearch?: boolean },
): Promise<IndexCreated> {
  return client.post<IndexCreated>(
    indexingPaths.runs(workspaceId, collectionId),
    {
      provider_id: providerId,
      ...(options?.contextualSearch ? { contextual_search: true } : {}),
    },
    { idempotencyKey, signal: options?.signal },
  );
}

export async function searchCollection(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  input: SearchRequestInput,
  options?: { signal?: AbortSignal },
): Promise<SearchResponse> {
  const body: Record<string, unknown> = {
    query: input.query.trim(),
    top_k: input.top_k,
    mode: input.mode,
    candidate_k: input.candidate_k,
    rrf_k: input.rrf_k,
  };
  if (input.rerank_provider_id)
    body.rerank_provider_id = input.rerank_provider_id;
  if (input.document_ids && input.document_ids.length > 0) {
    body.document_ids = input.document_ids;
  }
  if (input.metadata_filter && Object.keys(input.metadata_filter).length > 0) {
    body.metadata_filter = input.metadata_filter;
  }
  if (input.scope_resolution === "catalog") body.scope_resolution = "catalog";
  return client.post<SearchResponse>(
    indexingPaths.search(workspaceId, collectionId),
    body,
    { signal: options?.signal },
  );
}
