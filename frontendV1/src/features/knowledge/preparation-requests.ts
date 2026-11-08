import type { V1Client, V1RequestOptions } from "@/app/api/v1";
import { preparationPaths } from "@/app/api/v1";
import type {
  PreparationCreatedResponse,
  PreparationIntent,
  PreparationRequestInput,
} from "./preparation-types";

export async function createPreparationIntent(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  input: PreparationRequestInput,
  idempotencyKey: string,
  options?: V1RequestOptions,
): Promise<PreparationCreatedResponse> {
  return client.post<PreparationCreatedResponse>(
    preparationPaths.intents(workspaceId, collectionId, sourceId),
    input,
    { ...options, idempotencyKey },
  );
}

export async function listPreparationIntents(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  sourceId: string,
  limit = 20,
  options?: V1RequestOptions,
): Promise<PreparationIntent[]> {
  return client.get<PreparationIntent[]>(
    preparationPaths.intents(workspaceId, collectionId, sourceId),
    { ...options, searchParams: { limit } },
  );
}

export async function getPreparationIntent(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  intentId: string,
  options?: V1RequestOptions,
): Promise<PreparationIntent> {
  return client.get<PreparationIntent>(
    preparationPaths.intent(workspaceId, collectionId, intentId),
    options,
  );
}

export async function cancelPreparationIntent(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  intentId: string,
  options?: V1RequestOptions,
): Promise<PreparationIntent> {
  return client.post<PreparationIntent>(
    preparationPaths.cancel(workspaceId, collectionId, intentId),
    {},
    options,
  );
}
