/**
 * HTTP request functions for Lifecycle domain.
 */

import { v1Client } from "../v1-client";
import { lifecyclePaths } from "./endpoints";
import type {
  LifecycleActionReceipt,
  LifecycleActionRequest,
  LifecyclePreviewRequest,
} from "./types";

export async function createLifecyclePreview(
  workspaceId: string,
  data: LifecyclePreviewRequest,
  options?: { signal?: AbortSignal },
): Promise<LifecycleActionReceipt> {
  return v1Client.post<LifecycleActionReceipt>(
    lifecyclePaths.previews(workspaceId),
    data,
    options,
  );
}

export async function commitLifecycleAction(
  workspaceId: string,
  data: LifecycleActionRequest,
  idempotencyKey?: string,
  options?: { signal?: AbortSignal },
): Promise<LifecycleActionReceipt> {
  return v1Client.post<LifecycleActionReceipt>(
    lifecyclePaths.actions(workspaceId),
    data,
    {
      idempotencyKey,
      signal: options?.signal,
    },
  );
}

export async function getLifecycleAction(
  workspaceId: string,
  actionId: string,
  options?: { signal?: AbortSignal },
): Promise<LifecycleActionReceipt> {
  return v1Client.get<LifecycleActionReceipt>(
    lifecyclePaths.action(workspaceId, actionId),
    options,
  );
}
