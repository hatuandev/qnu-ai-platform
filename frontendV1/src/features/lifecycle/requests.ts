import { lifecyclePaths, type V1Client } from "@/app/api/v1";
import type { LifecycleAction, LifecycleRequest, ResourcePage } from "./types";

export function previewLifecycle(
  client: V1Client,
  workspaceId: string,
  input: LifecycleRequest,
) {
  return client.post<LifecycleAction>(
    lifecyclePaths.previews(workspaceId),
    input,
  );
}
export function lifecycleKey(previewId: string): string {
  return `lifecycle:${previewId}`;
}
export function acceptLifecycle(
  client: V1Client,
  workspaceId: string,
  preview: Pick<LifecycleAction, "id" | "preview_sha256">,
) {
  return client.post<LifecycleAction>(
    lifecyclePaths.actions(workspaceId),
    { preview_id: preview.id, preview_sha256: preview.preview_sha256 },
    { idempotencyKey: lifecycleKey(preview.id) },
  );
}
export function getLifecycleAction(
  client: V1Client,
  workspaceId: string,
  id: string,
  signal?: AbortSignal,
) {
  return client.get<LifecycleAction>(lifecyclePaths.action(workspaceId, id), {
    signal,
  });
}
export function listArchivedResources(
  client: V1Client,
  workspaceId: string,
  page: number,
  signal?: AbortSignal,
) {
  return client.get<ResourcePage>(lifecyclePaths.resources(workspaceId), {
    searchParams: { limit: 21, offset: (page - 1) * 20 },
    signal,
  });
}
