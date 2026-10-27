/**
 * Assistant types matching `backendV1/qnu/domains/assistants/schemas.py`.
 */

import type { RagPolicy } from "@/features/rag/types";

export type Assistant = {
  id: string;
  workspace_id: string;
  name: string;
  description: string;
  persona: string;
  collection_id: string;
  chat_provider_id: string | null;
  top_k: number;
  history_turns: number;
  max_output_tokens: number;
  is_active: boolean;
  /**
   * Retrieval/verification policy snapshot source. Older responses may omit it;
   * treat a missing value as the backend-compatible default (dense, no context
   * window, verification off) instead of guessing a richer policy.
   */
  rag_policy?: RagPolicy;
  revision: number;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type AssistantCreateInput = {
  name: string;
  description?: string;
  persona?: string;
  collection_id: string;
  chat_provider_id?: string | null;
  top_k?: number;
  history_turns?: number;
  max_output_tokens?: number;
  is_active?: boolean;
  rag_policy?: RagPolicy;
};

/**
 * PUT /workspaces/:workspaceId/assistants/:assistantId requires full configuration
 * plus `expected_revision`.
 *
 * `rag_policy` is always sent: the backend keeps the stored policy only when the
 * field is absent, so omitting it would make "reset to defaults" impossible and
 * hide accidental drift from the user.
 */
export type AssistantUpdateInput = {
  name: string;
  description: string;
  persona: string;
  collection_id: string;
  chat_provider_id: string | null;
  top_k: number;
  history_turns: number;
  max_output_tokens: number;
  is_active: boolean;
  rag_policy: RagPolicy;
  expected_revision: number;
};

export type AssistantListParams = {
  limit?: number;
  offset?: number;
};
