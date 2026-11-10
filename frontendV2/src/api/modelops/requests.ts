/**
 * Plain async request functions for ModelOps & AI Provider domain.
 */

import { v1Client } from "../v1-client";
import { modelopsPaths } from "./endpoints";
import type {
  Capability,
  CatalogItem,
  Connection,
  ConnectionInput,
  ConnectionModelCreateInput,
  ConnectionTestRequest,
  ConnectionTestResult,
  ConnectionUpdateInput,
  DefaultsUpdateRequest,
  DiagnosticCheck,
  KeyCreateRequest,
  ModelDefaults,
  ModelProvider,
  ProviderKey,
} from "./types";

export function buildConnectionModelPayload(input: ConnectionModelCreateInput) {
  const hasManualLimits =
    input.token_limits !== undefined && input.token_limits !== null;
  const hasManualDimension =
    input.embedding_dimension !== undefined &&
    input.embedding_dimension !== null;
  const hasDiscoveryCheckId = Boolean(input.discovery_check_id?.trim());

  if (hasDiscoveryCheckId && (hasManualLimits || hasManualDimension)) {
    throw new Error(
      "Không gửi đồng thời thông số giới hạn thủ công với discovery_check_id.",
    );
  }

  const payload: {
    model_name: string;
    capabilities: Capability[];
    token_limits?: ConnectionModelCreateInput["token_limits"];
    embedding_dimension?: number | null;
    discovery_check_id?: string;
  } = {
    model_name: input.model_name.trim(),
    capabilities: [...input.capabilities],
  };

  if (hasDiscoveryCheckId && input.discovery_check_id) {
    payload.discovery_check_id = input.discovery_check_id.trim();
  } else {
    if (hasManualLimits && input.token_limits) {
      payload.token_limits = input.token_limits;
    }
    if (hasManualDimension && typeof input.embedding_dimension === "number") {
      payload.embedding_dimension = input.embedding_dimension;
    }
  }

  return payload;
}

export async function listConnections(options?: {
  signal?: AbortSignal;
}): Promise<Connection[]> {
  return v1Client.get<Connection[]>(modelopsPaths.connections, options);
}

export async function getConnection(
  connectionId: string,
  options?: { signal?: AbortSignal },
): Promise<Connection> {
  return v1Client.get<Connection>(
    modelopsPaths.connection(connectionId),
    options,
  );
}

export async function createConnection(
  input: ConnectionInput,
): Promise<Connection> {
  return v1Client.post<Connection>(modelopsPaths.connections, input);
}

export async function updateConnection(
  connectionId: string,
  input: ConnectionUpdateInput,
): Promise<Connection> {
  return v1Client.patch<Connection>(
    modelopsPaths.connection(connectionId),
    input,
  );
}

export async function deleteConnection(connectionId: string): Promise<void> {
  await v1Client.delete(modelopsPaths.connection(connectionId));
}

export async function testConnection(
  connectionId: string,
  req: ConnectionTestRequest,
): Promise<ConnectionTestResult> {
  return v1Client.post<ConnectionTestResult>(
    modelopsPaths.connectionTest(connectionId),
    req,
    { timeoutMs: 310_000 },
  );
}

export async function listConnectionModels(
  connectionId: string,
  options?: { signal?: AbortSignal },
): Promise<ModelProvider[]> {
  return v1Client.get<ModelProvider[]>(
    modelopsPaths.connectionModels(connectionId),
    options,
  );
}

export async function createConnectionModel(
  connectionId: string,
  input: ConnectionModelCreateInput,
): Promise<ModelProvider> {
  return v1Client.post<ModelProvider>(
    modelopsPaths.connectionModels(connectionId),
    buildConnectionModelPayload(input),
  );
}

export async function deleteConnectionModel(
  connectionId: string,
  modelId: string,
): Promise<void> {
  await v1Client.delete(modelopsPaths.connectionModel(connectionId, modelId));
}

export async function listConnectionKeys(
  connectionId: string,
  options?: { signal?: AbortSignal },
): Promise<ProviderKey[]> {
  return v1Client.get<ProviderKey[]>(modelopsPaths.keys(connectionId), options);
}

export async function createConnectionKey(
  connectionId: string,
  input: KeyCreateRequest,
): Promise<ProviderKey> {
  return v1Client.post<ProviderKey>(modelopsPaths.keys(connectionId), input);
}

export async function deleteConnectionKey(
  connectionId: string,
  keyId: string,
): Promise<void> {
  await v1Client.delete(modelopsPaths.connectionKey(connectionId, keyId));
}

export async function probeModel(
  providerId: string,
  capability: Capability,
): Promise<DiagnosticCheck> {
  return v1Client.post<DiagnosticCheck>(
    modelopsPaths.probe(providerId),
    { capability },
    { timeoutMs: 70_000 },
  );
}

export async function listProviders(options?: {
  signal?: AbortSignal;
}): Promise<ModelProvider[]> {
  return v1Client.get<ModelProvider[]>(modelopsPaths.providers, options);
}

export async function getModelDefaults(options?: {
  signal?: AbortSignal;
}): Promise<ModelDefaults> {
  return v1Client.get<ModelDefaults>(modelopsPaths.defaults, options);
}

export async function updateModelDefaults(
  body: DefaultsUpdateRequest,
  options?: { signal?: AbortSignal },
): Promise<ModelDefaults> {
  return v1Client.put<ModelDefaults>(modelopsPaths.defaults, body, options);
}

export async function getCatalog(
  params?: { workspaceId?: string | null },
  options?: { signal?: AbortSignal },
): Promise<CatalogItem[]> {
  const query = params?.workspaceId
    ? `?workspace_id=${encodeURIComponent(params.workspaceId)}`
    : "";
  return v1Client.get<CatalogItem[]>(
    `${modelopsPaths.catalog}${query}`,
    options,
  );
}
