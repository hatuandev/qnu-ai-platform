import type { BlobResponse } from "../client";
import { v1Client } from "../v1-client";
import { operationsPaths } from "./endpoints";
import type {
  OperationJobListResponse,
  SystemBackupRestoreReport,
  SystemBackupTarget,
  SystemResetRequest,
  SystemResetResponse,
  WorkspaceBackupItem,
  WorkspaceBackupListResponse,
} from "./types";

export function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function createWorkspaceBackup(
  workspaceId: string,
  options?: { retention_days?: number | null; idempotencyKey?: string },
): Promise<WorkspaceBackupItem> {
  const key =
    options?.idempotencyKey ??
    `bak-ui-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  return v1Client.post<WorkspaceBackupItem>(
    operationsPaths.backups(workspaceId),
    { retention_days: options?.retention_days ?? 30 },
    { idempotencyKey: key },
  );
}

export async function getWorkspaceBackup(
  workspaceId: string,
  backupId: string,
): Promise<WorkspaceBackupItem> {
  return v1Client.get<WorkspaceBackupItem>(
    operationsPaths.backup(workspaceId, backupId),
  );
}

export async function downloadWorkspaceBackup(
  workspaceId: string,
  backupId: string,
): Promise<BlobResponse> {
  const result = await v1Client.requestBlob(
    operationsPaths.backupDownload(workspaceId, backupId),
    { timeoutMs: 180_000 },
  );
  triggerBlobDownload(result.blob, result.fileName || `${backupId}.zip`);
  return result;
}

export async function exportSystemBackup(
  target: SystemBackupTarget = "all",
): Promise<BlobResponse> {
  const result = await v1Client.request<BlobResponse>(
    operationsPaths.systemBackupExport(),
    {
      method: "POST",
      searchParams: { target },
      responseType: "blob",
      timeoutMs: 300_000,
    },
  );
  triggerBlobDownload(
    result.blob,
    result.fileName || `qnu-system-backup-${Date.now()}.tar.gz`,
  );
  return result;
}

export async function restoreSystemBackup(
  file: File,
  options?: { target?: SystemBackupTarget; confirm?: boolean },
): Promise<SystemBackupRestoreReport> {
  const formData = new FormData();
  formData.append("file", file, file.name);
  formData.append("target", options?.target ?? "all");
  formData.append("confirm", options?.confirm ? "true" : "false");
  return v1Client.upload<SystemBackupRestoreReport>(
    operationsPaths.systemBackupRestore(),
    formData,
    { timeoutMs: 300_000 },
  );
}

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
