import { operationsPaths, type V1Client } from "@/app/api/v1";
import type {
  Backup,
  BackupPage,
  BackupVerification,
  CleanupAction,
  Retention,
} from "./maintenance-types";
import type { OperationAction } from "./types";

export function listBackups(
  client: V1Client,
  workspaceId: string,
  page: number,
  signal?: AbortSignal,
  pageSize = 20,
) {
  return client.get<BackupPage>(operationsPaths.backups(workspaceId), {
    searchParams: { limit: pageSize, offset: (page - 1) * pageSize },
    signal,
  });
}
export function createBackup(
  client: V1Client,
  workspaceId: string,
  retentionDays: number | null,
  idempotencyKey: string,
) {
  return client.post<Backup>(
    operationsPaths.backups(workspaceId),
    { retention_days: retentionDays },
    { idempotencyKey },
  );
}
export function getBackup(
  client: V1Client,
  workspaceId: string,
  id: string,
  signal?: AbortSignal,
) {
  return client.get<Backup>(operationsPaths.backup(workspaceId, id), {
    signal,
  });
}
export function getRetention(
  client: V1Client,
  workspaceId: string,
  signal?: AbortSignal,
) {
  return client.get<Retention>(operationsPaths.retention(workspaceId), {
    signal,
  });
}
export function verifyBackup(
  client: V1Client,
  workspaceId: string,
  id: string,
  signal?: AbortSignal,
) {
  return client.get<BackupVerification>(
    operationsPaths.backupVerify(workspaceId, id),
    { signal },
  );
}
export function downloadBackup(
  client: V1Client,
  workspaceId: string,
  id: string,
) {
  return client.requestBlob(operationsPaths.backupDownload(workspaceId, id));
}
export function previewBackupDeletion(
  client: V1Client,
  workspaceId: string,
  id: string,
  reason: string,
) {
  return client.post<OperationAction>(
    operationsPaths.backupDeletePreview(workspaceId, id),
    { reason },
  );
}
export function previewCleanup(
  client: V1Client,
  workspaceId: string,
  reason: string,
  minAgeHours: number,
) {
  return client.post<CleanupAction>(
    operationsPaths.cleanupPreviews(workspaceId),
    { reason, min_age_hours: minAgeHours },
  );
}
export function getCleanup(
  client: V1Client,
  workspaceId: string,
  id: string,
  signal?: AbortSignal,
) {
  return client.get<CleanupAction>(
    operationsPaths.cleanupAction(workspaceId, id),
    { signal },
  );
}
export function acceptCleanup(
  client: V1Client,
  workspaceId: string,
  preview: Pick<CleanupAction, "id" | "preview_sha256">,
) {
  return client.post<CleanupAction>(
    operationsPaths.cleanupActions(workspaceId),
    { preview_id: preview.id, preview_sha256: preview.preview_sha256 },
    { idempotencyKey: `storage-cleanup:${preview.id}` },
  );
}
