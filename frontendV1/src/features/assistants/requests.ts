import type { V1Client } from "@/app/api/v1";
import { assistantPaths } from "@/app/api/v1";
import type {
  Assistant,
  AssistantCreateInput,
  AssistantListParams,
  AssistantUpdateInput,
} from "@/features/assistants/types";
import { DEFAULT_RAG_POLICY } from "@/features/rag/types";

/**
 * Lists assistants in a workspace.
 * Endpoint returns a raw array `Assistant[]` using limit and offset.
 */
export function listAssistants(
  client: V1Client,
  workspaceId: string,
  params?: AssistantListParams,
  options?: { signal?: AbortSignal },
): Promise<Assistant[]> {
  return client.get<Assistant[]>(assistantPaths.list(workspaceId), {
    searchParams: {
      limit: params?.limit ?? 20,
      offset: params?.offset ?? 0,
    },
    signal: options?.signal,
  });
}

/**
 * Retrieves details of a single assistant.
 */
export function getAssistant(
  client: V1Client,
  workspaceId: string,
  assistantId: string,
  options?: { signal?: AbortSignal },
): Promise<Assistant> {
  return client.get<Assistant>(
    assistantPaths.detail(workspaceId, assistantId),
    {
      signal: options?.signal,
    },
  );
}

/**
 * Creates a new assistant in the workspace.
 * Requires workspace admin privileges.
 */
export function createAssistant(
  client: V1Client,
  workspaceId: string,
  input: AssistantCreateInput,
  options?: { signal?: AbortSignal },
): Promise<Assistant> {
  return client.post<Assistant>(
    assistantPaths.list(workspaceId),
    {
      name: input.name.trim(),
      description: input.description ?? "",
      persona: input.persona ?? "",
      collection_id: input.collection_id,
      chat_provider_id: input.chat_provider_id ?? null,
      top_k: input.top_k ?? 5,
      history_turns: input.history_turns ?? 3,
      max_output_tokens: input.max_output_tokens ?? null,
      is_active: input.is_active ?? true,
      // Backend default when omitted; sending it explicitly keeps the payload
      // self-describing without upgrading an existing assistant.
      rag_policy: input.rag_policy ?? DEFAULT_RAG_POLICY,
    },
    { signal: options?.signal },
  );
}

/**
 * Completely updates an assistant's configuration with optimistic concurrency check.
 * Requires `expected_revision`.
 */
export function updateAssistant(
  client: V1Client,
  workspaceId: string,
  assistantId: string,
  input: AssistantUpdateInput,
  options?: { signal?: AbortSignal },
): Promise<Assistant> {
  return client.put<Assistant>(
    assistantPaths.detail(workspaceId, assistantId),
    {
      name: input.name.trim(),
      description: input.description ?? "",
      persona: input.persona ?? "",
      collection_id: input.collection_id,
      chat_provider_id: input.chat_provider_id ?? null,
      top_k: input.top_k,
      history_turns: input.history_turns,
      max_output_tokens: input.max_output_tokens,
      is_active: input.is_active,
      rag_policy: input.rag_policy,
      expected_revision: input.expected_revision,
    },
    { signal: options?.signal },
  );
}
