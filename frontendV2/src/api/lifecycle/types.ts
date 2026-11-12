/**
 * TypeScript types for Lifecycle operations (source purge, delete preview, receipts).
 * Mirrors `backendV1/qnu/domains/lifecycle/`.
 */

export type ResourceKind =
  | "collection"
  | "source"
  | "document"
  | "assistant"
  | "conversation"
  | "job";

export type LifecycleOperation =
  | "archive"
  | "delete"
  | "restore"
  | "cancel"
  | "replace"
  | "withdraw";

export type LifecyclePreviewRequest = {
  kind: ResourceKind;
  resource_id: string;
  action: LifecycleOperation;
  reason: string;
};

export type LifecycleActionRequest = {
  preview_id: string;
  preview_sha256: string;
};

export type LifecycleProgress = {
  step?: string | null;
  percent?: number | null;
};

export type LifecycleActionReceipt = {
  id: string;
  kind: ResourceKind;
  resource_id: string;
  action: LifecycleOperation;
  status: "preview" | "pending" | "completed" | "failed";
  phase?: string | null;
  progress?: LifecycleProgress | null;
  error_code?: string | null;
  result?: {
    permanent?: boolean;
    originals_retained?: boolean;
    restore_available?: boolean;
    [key: string]: unknown;
  } | null;
  preview_sha256: string;
  impact: Record<string, unknown>;
  expires_at: string;
  finished_at?: string | null;
};

export function isSourcePurgeCompleted(
  receipt: LifecycleActionReceipt,
): boolean {
  return (
    receipt.kind === "source" &&
    receipt.action === "delete" &&
    receipt.status === "completed" &&
    receipt.result?.permanent === true
  );
}
