/**
 * TypeScript types for the Assistants domain.
 * Mirrors `backendV1/qnu/domains/assistants/schemas.py`.
 */

export type RagPolicy = {
  retrieval_mode: "dense" | "hybrid" | "hybrid_rerank";
  candidate_k: number;
  rrf_k: number;
  rerank_provider_id: string | null;
  metadata_filter: Record<string, unknown>;
  scope_resolution: "explicit" | "catalog";
  context_window: number;
  context_max_bytes: number;
  verification_mode: "off" | "observe" | "enforce";
  verification_provider_id: string | null;
  verification_max_output_tokens: number | null;
};

export type AssistantResponse = {
  id: string;
  workspace_id: string;
  name: string;
  description: string;
  persona: string;
  /** Mirrors `collection_ids[0]`; null when no collection is attached. */
  collection_id: string | null;
  collection_ids: string[];
  chat_provider_id: string | null;
  top_k: number;
  history_turns: number;
  max_output_tokens: number | null;
  is_active: boolean;
  rag_policy: RagPolicy;
  revision: number;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type AssistantCreateRequest = {
  name: string;
  description: string;
  persona: string;
  collection_id: string | null;
  collection_ids: string[];
  chat_provider_id: string | null;
  top_k: number;
  history_turns: number;
  max_output_tokens: number | null;
  is_active: boolean;
  rag_policy: RagPolicy;
};

export type AssistantUpdateRequest = AssistantCreateRequest & {
  expected_revision: number;
};

export type AssistantReadinessStatus =
  | "empty"
  | "syncing"
  | "ready"
  | "outdated"
  | "not_indexed"
  | "failed"
  | "uncertain";

export type AssistantCollectionReadiness = {
  collection_id: string;
  collection_name: string;
  status: AssistantReadinessStatus;
  published_document_count: number;
  served_document_count: number;
  index_run_id: string | null;
  index_generation: number | null;
  sync_status: string;
  sync_error_code: string | null;
};

/** Scalar fields describe the first collection; `collections` covers all. */
export type AssistantReadiness = {
  assistant_id: string;
  /** null when the assistant has no collection attached yet. */
  collection_id: string | null;
  collection_name: string;
  status: AssistantReadinessStatus;
  published_document_count: number;
  served_document_count: number;
  index_run_id: string | null;
  index_generation: number | null;
  sync_status: string;
  sync_error_code: string | null;
  collections: AssistantCollectionReadiness[];
  checked_at: string;
};
