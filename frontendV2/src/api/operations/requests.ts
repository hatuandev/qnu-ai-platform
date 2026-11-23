import { v1Client } from "../v1-client";
import { operationsPaths } from "./endpoints";
import type {
  OperationJobListResponse,
  SystemResetRequest,
  SystemResetResponse,
  WorkspaceBackupListResponse,
} from "./types";

export async function systemResetAndSeed(
  payload: SystemResetRequest,
): Promise<SystemResetResponse> {
  return v1Client.post<SystemResetResponse>(
    operationsPaths.systemResetAndSeed(),
    payload,
    { timeoutMs: 120_000 },
  );
}

export async function listOperationsJobs(
  workspaceId: string,
  params?: {
    kind?: string;
    status?: string;
    collection_id?: string;
    limit?: number;
    offset?: number;
  },
  options?: { signal?: AbortSignal },
): Promise<OperationJobListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.kind) queryParams.set("kind", params.kind);
  if (params?.status) queryParams.set("status", params.status);
  if (params?.collection_id)
    queryParams.set("collection_id", params.collection_id);
  if (params?.limit !== undefined)
    queryParams.set("limit", String(params.limit));
  if (params?.offset !== undefined)
    queryParams.set("offset", String(params.offset));

  const qs = queryParams.toString();
  const url = `${operationsPaths.jobs(workspaceId)}${qs ? `?${qs}` : ""}`;
  return v1Client.get<OperationJobListResponse>(url, {
    signal: options?.signal,
  });
}

export async function getOperationsSummary(
  workspaceId: string,
  options?: { signal?: AbortSignal },
): Promise<Record<string, unknown>> {
  return v1Client.get<Record<string, unknown>>(
    operationsPaths.summary(workspaceId),
    {
      signal: options?.signal,
    },
  );
}

export async function listWorkspaceBackups(
  workspaceId: string,
  params?: { limit?: number; offset?: number },
  options?: { signal?: AbortSignal },
): Promise<WorkspaceBackupListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.limit !== undefined)
    queryParams.set("limit", String(params.limit));
  if (params?.offset !== undefined)
    queryParams.set("offset", String(params.offset));

  const qs = queryParams.toString();
  const url = `${operationsPaths.backups(workspaceId)}${qs ? `?${qs}` : ""}`;
  return v1Client.get<WorkspaceBackupListResponse>(url, {
    signal: options?.signal,
  });
}
