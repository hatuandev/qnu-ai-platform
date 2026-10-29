export type ResourceKind =
  | "collection"
  | "source"
  | "document"
  | "assistant"
  | "conversation"
  | "job"
  | "index";
export type LifecycleOperation =
  | "archive"
  | "delete"
  | "restore"
  | "pause"
  | "resume"
  | "cancel"
  | "cleanup"
  | "replace";
export type CancellableJobKind =
  | "ocr"
  | "compiler"
  | "index"
  | "auto_review"
  | "review"
  | "spelling"
  | "turn";
export type LifecycleRequest = {
  kind: ResourceKind;
  resource_id: string;
  action: LifecycleOperation;
  reason: string;
  job_kind?: CancellableJobKind;
  replacement_version_id?: string;
};
export type LifecycleTarget = Omit<LifecycleRequest, "reason">;
export type LifecycleAction = {
  id: string;
  kind: ResourceKind;
  resource_id: string;
  action: LifecycleOperation;
  reason: string;
  impact: Record<string, unknown>;
  preview_sha256: string;
  status: string;
  result: Record<string, unknown> | null;
  error_code: string | null;
  expires_at: string;
  accepted_at: string | null;
  finished_at: string | null;
};
export function isSourcePurgeCompleted(action: LifecycleAction): boolean {
  return (
    action.kind === "source" &&
    action.action === "delete" &&
    action.status === "completed" &&
    action.result?.permanent === true &&
    action.result?.originals_retained === false &&
    action.result?.restore_available === false
  );
}
export type ArchivedResource = {
  kind: ResourceKind;
  resource_id: string;
  status: "archived" | "deleted";
  updated_at: string;
};
export type ResourcePage = {
  items: ArchivedResource[];
  limit: number;
  offset: number;
};
export const RESOURCE_LABEL: Record<ResourceKind, string> = {
  collection: "Kho tri thức",
  source: "Văn bản nguồn",
  document: "Tài liệu biên soạn",
  assistant: "Trợ lý",
  conversation: "Hội thoại",
  job: "Tác vụ",
  index: "Chỉ mục",
};
export type LegacyDeletedSource = { source_id: string; title: string };
export type LegacyDeletedSourcesPage = {
  items: LegacyDeletedSource[];
  total: number;
  limit: number;
  offset: number;
};

export const ACTION_LABEL: Record<LifecycleOperation, string> = {
  archive: "Lưu trữ",
  delete: "Đưa vào thùng rác",
  restore: "Khôi phục",
  pause: "Tạm dừng",
  resume: "Bật lại",
  cancel: "Hủy tác vụ",
  cleanup: "Dọn chỉ mục",
  replace: "Thay bản phục vụ",
};
