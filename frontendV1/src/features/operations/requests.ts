import { operationsPaths, type V1Client } from "@/app/api/v1";
import type {
  JobFilters,
  JobKind,
  JobPage,
  JobView,
  OperationAction,
  OperationsSummary,
  Readiness,
} from "./types";
export function listJobs(
  client: V1Client,
  workspaceId: string,
  filters: JobFilters,
  signal?: AbortSignal,
) {
  const limit = filters.pageSize ?? 20;
  return client.get<JobPage>(operationsPaths.jobs(workspaceId), {
    searchParams: {
      limit,
      offset: (filters.page - 1) * limit,
      kind: filters.kind,
      status: filters.status,
      collection_id: filters.collectionId,
    },
    signal,
  });
}
export function getJob(
  client: V1Client,
  workspaceId: string,
  kind: JobKind,
  id: string,
  signal?: AbortSignal,
) {
  return client.get<JobView>(operationsPaths.job(workspaceId, kind, id), {
    signal,
  });
}
export function getSummary(
  client: V1Client,
  workspaceId: string,
  signal?: AbortSignal,
) {
  return client.get<OperationsSummary>(operationsPaths.summary(workspaceId), {
    signal,
  });
}
export function getReadiness(
  client: V1Client,
  workspaceId: string,
  signal?: AbortSignal,
) {
  return client.get<Readiness>(operationsPaths.readiness(workspaceId), {
    signal,
  });
}
export function previewRecovery(
  client: V1Client,
  workspaceId: string,
  kind: JobKind,
  id: string,
  reason: string,
) {
  return client.post<OperationAction>(
    operationsPaths.recoveryPreview(workspaceId, kind, id),
    { reason },
  );
}
export function acceptRecovery(
  client: V1Client,
  workspaceId: string,
  preview: Pick<OperationAction, "id" | "preview_sha256">,
) {
  return client.post<OperationAction>(
    operationsPaths.actions(workspaceId),
    { preview_id: preview.id, preview_sha256: preview.preview_sha256 },
    { idempotencyKey: `operations:${preview.id}` },
  );
}
export function getOperationAction(
  client: V1Client,
  workspaceId: string,
  id: string,
  signal?: AbortSignal,
) {
  return client.get<OperationAction>(operationsPaths.action(workspaceId, id), {
    signal,
  });
}
