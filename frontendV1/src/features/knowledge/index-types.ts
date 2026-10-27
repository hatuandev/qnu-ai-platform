import type {
  MetadataFilter,
  RagPolicy,
  RetrievalMode,
} from "@/features/rag/types";

/**
 * Index generation and search contracts mirrored from
 * `backendV1/qnu/domains/knowledge/index/schemas.py`.
 */

export type IndexRunStatus =
  | "queued"
  | "dispatched"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export type IndexRun = {
  id: string;
  workspace_id: string;
  collection_id: string;
  generation: number;
  status: IndexRunStatus | string;
  is_active: boolean;
  provider_id: string;
  dimension: number;
  input_sha256: string;
  requested_at: string;
  dispatched_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  attempt_count: number;
  error_code: string | null;
  chunks_total: number;
  manifest_sha256: string | null;
};

export type IndexCreated = {
  run: IndexRun;
  created: boolean;
  dispatched: boolean;
};

export type SearchHit = {
  chunk_id: string;
  document_id: string;
  version_id: string;
  publication_decision_id: string;
  score: number;
  kind: string;
  text: string;
  citations: Record<string, unknown>;
  structure: Record<string, unknown> | null;
};

export type SearchResponse = {
  index_run_id: string;
  generation: number;
  status: string;
  hits: SearchHit[];
  eligible_documents: number;
  skipped_documents: Record<string, unknown>[];
  trace: Record<string, unknown>;
};

export type SearchRequestInput = {
  query: string;
  top_k: number;
  document_ids?: string[] | null;
  mode: RetrievalMode;
  candidate_k: number;
  rrf_k: number;
  rerank_provider_id?: string | null;
  metadata_filter?: MetadataFilter;
};

/** Search defaults must match `SearchRequest` so an empty form is valid. */
export const DEFAULT_SEARCH_INPUT: Omit<SearchRequestInput, "query"> = {
  top_k: 5,
  mode: "dense",
  candidate_k: 30,
  rrf_k: 60,
  rerank_provider_id: null,
  metadata_filter: {},
};

/** Builds a search body from a policy so the test mirrors the assistant. */
export function searchInputFromPolicy(
  query: string,
  policy: RagPolicy,
  topK: number,
): SearchRequestInput {
  return {
    query,
    top_k: topK,
    mode: policy.retrieval_mode,
    candidate_k: policy.candidate_k,
    rrf_k: policy.rrf_k,
    rerank_provider_id:
      policy.retrieval_mode === "hybrid_rerank"
        ? policy.rerank_provider_id
        : null,
    metadata_filter: policy.metadata_filter,
  };
}
