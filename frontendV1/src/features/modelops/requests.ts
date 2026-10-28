/**
 * HTTP contract for ModelOps screens.
 *
 * One function per route in `backendV1/qnu/domains/modelops/router.py`. A
 * provider record remains endpoint + one model. Discovery/probe have dedicated,
 * admin-only endpoints; listing models never silently updates configuration.
 */

import type { V1Client } from "../../app/api/v1/client.ts";
import { modelopsPaths } from "../../app/api/v1/endpoints.ts";
import type {
  CatalogItem,
  DefaultsUpdateInput,
  KeyAudit,
  KeyCreateInput,
  KeyRevokeInput,
  KeyRotateInput,
  ModelDefaults,
  ModelOpsEvent,
  Provider,
  ProviderCreateInput,
  ProviderKey,
  ProviderUpdateInput,
} from "./types.ts";

export function listProviders(
  client: V1Client,
  options?: { signal?: AbortSignal },
): Promise<Provider[]> {
  return client.get<Provider[]>(modelopsPaths.providers, options);
}

export function getProvider(
  client: V1Client,
  providerId: string,
  options?: { signal?: AbortSignal },
): Promise<Provider> {
  return client.get<Provider>(modelopsPaths.provider(providerId), options);
}

export function createProvider(
  client: V1Client,
  input: ProviderCreateInput,
): Promise<Provider> {
  return client.post<Provider>(modelopsPaths.providers, input);
}

export function updateProvider(
  client: V1Client,
  providerId: string,
  patch: ProviderUpdateInput,
): Promise<Provider> {
  return client.patch<Provider>(modelopsPaths.provider(providerId), patch);
}

export function listProviderKeys(
  client: V1Client,
  providerId: string,
  options?: { signal?: AbortSignal },
): Promise<ProviderKey[]> {
  return client.get<ProviderKey[]>(modelopsPaths.keys(providerId), options);
}

export function createProviderKey(
  client: V1Client,
  providerId: string,
  input: KeyCreateInput,
): Promise<ProviderKey> {
  return client.post<ProviderKey>(modelopsPaths.keys(providerId), input);
}

export function rotateProviderKey(
  client: V1Client,
  providerId: string,
  keyId: string,
  input: KeyRotateInput,
): Promise<ProviderKey> {
  return client.post<ProviderKey>(
    modelopsPaths.keyRotate(providerId, keyId),
    input,
  );
}

export function revokeProviderKey(
  client: V1Client,
  providerId: string,
  keyId: string,
  input: KeyRevokeInput,
): Promise<ProviderKey> {
  return client.post<ProviderKey>(
    modelopsPaths.keyRevoke(providerId, keyId),
    input,
  );
}

export function listKeyEvents(
  client: V1Client,
  providerId: string,
  limit = 50,
  options?: { signal?: AbortSignal },
): Promise<KeyAudit[]> {
  return client.get<KeyAudit[]>(modelopsPaths.keyEvents(providerId), {
    searchParams: { limit },
    signal: options?.signal,
  });
}

export function getDefaults(
  client: V1Client,
  options?: { signal?: AbortSignal },
): Promise<ModelDefaults> {
  return client.get<ModelDefaults>(modelopsPaths.defaults, options);
}

export function putDefaults(
  client: V1Client,
  input: DefaultsUpdateInput,
): Promise<ModelDefaults> {
  return client.put<ModelDefaults>(modelopsPaths.defaults, input);
}

export function listModelOpsEvents(
  client: V1Client,
  limit = 50,
  options?: { signal?: AbortSignal },
): Promise<ModelOpsEvent[]> {
  return client.get<ModelOpsEvent[]>(modelopsPaths.events, {
    searchParams: { limit },
    signal: options?.signal,
  });
}

export function getCatalog(
  client: V1Client,
  workspaceId: string,
  options?: { signal?: AbortSignal },
): Promise<CatalogItem[]> {
  return client.get<CatalogItem[]>(modelopsPaths.catalog, {
    searchParams: { workspace_id: workspaceId },
    signal: options?.signal,
  });
}

/**
 * Defaults for one capability, expressed as a full replacement payload.
 *
 * `PUT /modelops/defaults` merges by capability server-side, but the UI always
 * sends provider+model together so the pair can never drift apart.
 */
export function defaultsPatchFor(
  provider: Provider,
  capability: "chat" | "embedding" | "rerank" | "ocr",
): DefaultsUpdateInput {
  switch (capability) {
    case "chat":
      return { chat_provider_id: provider.id, chat_model: provider.model_name };
    case "embedding":
      return {
        embedding_provider_id: provider.id,
        embedding_model: provider.model_name,
      };
    case "rerank":
      return {
        rerank_provider_id: provider.id,
        rerank_model: provider.model_name,
      };
    case "ocr":
      return { ocr_provider_id: provider.id, ocr_model: provider.model_name };
  }
}

export function clearDefaultFor(
  capability: "chat" | "embedding" | "rerank" | "ocr",
): DefaultsUpdateInput {
  switch (capability) {
    case "chat":
      return { chat_provider_id: null, chat_model: null };
    case "embedding":
      return { embedding_provider_id: null, embedding_model: null };
    case "rerank":
      return { rerank_provider_id: null, rerank_model: null };
    case "ocr":
      return { ocr_provider_id: null, ocr_model: null };
  }
}
