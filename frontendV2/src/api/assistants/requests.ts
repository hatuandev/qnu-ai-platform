/**
 * HTTP request functions for the Assistants domain.
 * Mirrors `backendV1/qnu/domains/assistants/router.py`.
 */

import { v1Client } from "../v1-client";
import { assistantPaths } from "./endpoints";
import type {
  AssistantCreateRequest,
  AssistantReadiness,
  AssistantResponse,
  AssistantUpdateRequest,
} from "./types";

export async function listAssistants(
  workspaceId: string,
  params?: { limit?: number; offset?: number },
  options?: { signal?: AbortSignal },
): Promise<AssistantResponse[]> {
  return v1Client.get<AssistantResponse[]>(assistantPaths.list(workspaceId), {
    searchParams: {
      limit: params?.limit ?? 50,
      offset: params?.offset ?? 0,
    },
    signal: options?.signal,
  });
}

export async function getAssistant(
  workspaceId: string,
  assistantId: string,
  options?: { signal?: AbortSignal },
): Promise<AssistantResponse> {
  return v1Client.get<AssistantResponse>(
    assistantPaths.detail(workspaceId, assistantId),
    options,
  );
}

export async function createAssistant(
  workspaceId: string,
  data: AssistantCreateRequest,
  options?: { signal?: AbortSignal },
): Promise<AssistantResponse> {
  return v1Client.post<AssistantResponse>(
    assistantPaths.list(workspaceId),
    data,
    options,
  );
}

export async function updateAssistant(
  workspaceId: string,
  assistantId: string,
  data: AssistantUpdateRequest,
  options?: { signal?: AbortSignal },
): Promise<AssistantResponse> {
  return v1Client.put<AssistantResponse>(
    assistantPaths.detail(workspaceId, assistantId),
    data,
    options,
  );
}

export async function deleteAssistant(
  workspaceId: string,
  assistantId: string,
  options?: { signal?: AbortSignal },
): Promise<void> {
  return v1Client.delete<void>(
    assistantPaths.detail(workspaceId, assistantId),
    options,
  );
}

export async function getAssistantReadiness(
  workspaceId: string,
  assistantId: string,
  options?: { signal?: AbortSignal },
): Promise<AssistantReadiness> {
  return v1Client.get<AssistantReadiness>(
    assistantPaths.readiness(workspaceId, assistantId),
    options,
  );
}
