/**
 * HTTP request functions for Preparation domain.
 */

import { v1Client } from "../v1-client";
import { preparationPaths } from "./endpoints";
import type {
  PreparationCreatedResponse,
  PreparationIntent,
  PreparationRequestInput,
} from "./types";

export async function createPreparationIntent(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  input: PreparationRequestInput,
  idempotencyKey?: string,
  options?: { signal?: AbortSignal },
): Promise<PreparationCreatedResponse> {
  return v1Client.post<PreparationCreatedResponse>(
    preparationPaths.intents(workspaceId, collectionId, sourceId),
    input,
    {
      idempotencyKey,
      signal: options?.signal,
    },
  );
}

export async function listPreparationIntents(
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  limit = 20,
  options?: { signal?: AbortSignal },
): Promise<PreparationIntent[]> {
  return v1Client.get<PreparationIntent[]>(
    preparationPaths.intents(workspaceId, collectionId, sourceId),
    {
      searchParams: { limit },
      signal: options?.signal,
    },
  );
}

export async function getPreparationIntent(
  workspaceId: string,
  collectionId: string,
  intentId: string,
  options?: { signal?: AbortSignal },
): Promise<PreparationIntent> {
  return v1Client.get<PreparationIntent>(
    preparationPaths.intent(workspaceId, collectionId, intentId),
    options,
  );
}

export async function cancelPreparationIntent(
  workspaceId: string,
  collectionId: string,
  intentId: string,
  options?: { signal?: AbortSignal },
): Promise<PreparationIntent> {
  return v1Client.post<PreparationIntent>(
    preparationPaths.cancel(workspaceId, collectionId, intentId),
    {},
    options,
  );
}
