/**
 * HTTP requests for the Integration domain.
 */

import { v1Client } from "../v1-client";
import { integrationPaths } from "./endpoints";
import type {
  AppApiKey,
  AppApiKeyCreate,
  AppApiKeyRevokeRequest,
  AppApiKeyRotateRequest,
  AppApiKeySecret,
  AppApiKeyStatusUpdate,
  AppClient,
  AppClientCreate,
  AppRequestLog,
  IntegrationConfig,
} from "./types";

export async function getIntegrationConfig(options?: {
  signal?: AbortSignal;
}): Promise<IntegrationConfig> {
  return v1Client.get<IntegrationConfig>(integrationPaths.config, options);
}

export async function listAppClients(
  workspaceId: string,
  options?: { signal?: AbortSignal },
): Promise<AppClient[]> {
  return v1Client.get<AppClient[]>(integrationPaths.apps(workspaceId), options);
}

export async function createAppClient(
  workspaceId: string,
  data: AppClientCreate,
  options?: { signal?: AbortSignal },
): Promise<AppClient> {
  return v1Client.post<AppClient>(
    integrationPaths.apps(workspaceId),
    data,
    options,
  );
}

export async function listApiKeys(
  workspaceId: string,
  options?: { signal?: AbortSignal },
): Promise<AppApiKey[]> {
  return v1Client.get<AppApiKey[]>(integrationPaths.keys(workspaceId), options);
}

export async function createApiKey(
  workspaceId: string,
  data: AppApiKeyCreate,
  options?: { signal?: AbortSignal },
): Promise<AppApiKeySecret> {
  return v1Client.post<AppApiKeySecret>(
    integrationPaths.keys(workspaceId),
    data,
    options,
  );
}

export async function updateApiKeyStatus(
  workspaceId: string,
  keyId: string,
  data: AppApiKeyStatusUpdate,
  options?: { signal?: AbortSignal },
): Promise<AppApiKey> {
  return v1Client.put<AppApiKey>(
    integrationPaths.keyStatus(workspaceId, keyId),
    data,
    options,
  );
}

export async function rotateApiKey(
  workspaceId: string,
  keyId: string,
  data: AppApiKeyRotateRequest,
  options?: { signal?: AbortSignal },
): Promise<AppApiKeySecret> {
  return v1Client.post<AppApiKeySecret>(
    integrationPaths.keyRotate(workspaceId, keyId),
    data,
    options,
  );
}

export async function revokeApiKey(
  workspaceId: string,
  keyId: string,
  data?: AppApiKeyRevokeRequest,
  options?: { signal?: AbortSignal },
): Promise<AppApiKey> {
  if (data) {
    return v1Client.request<AppApiKey>(
      integrationPaths.keyRevoke(workspaceId, keyId),
      {
        method: "DELETE",
        body: data,
        signal: options?.signal,
      },
    );
  }
  return v1Client.delete<AppApiKey>(
    integrationPaths.keyRevoke(workspaceId, keyId),
    options,
  );
}

export async function listIntegrationLogs(
  workspaceId: string,
  limit = 50,
  options?: { signal?: AbortSignal },
): Promise<AppRequestLog[]> {
  return v1Client.get<AppRequestLog[]>(integrationPaths.logs(workspaceId), {
    ...options,
    searchParams: { limit },
  });
}
