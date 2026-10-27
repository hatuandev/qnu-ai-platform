import type { CancellableJobKind } from "@/features/lifecycle/types";
export type JobKind = CancellableJobKind | "backup";
export type JobView = {
  kind: JobKind;
  id: string;
  workspace_id: string;
  collection_id: string | null;
  status: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  lease_expires_at: string | null;
  error_code: string | null;
  attempts: number | null;
  progress_done: number | null;
  progress_total: number | null;
  usage_tokens: number | null;
  provider_id: string | null;
  recovery_allowed: boolean;
  recovery_reason: string;
};
export type JobFilters = {
  page: number;
  pageSize?: number;
  kind?: JobKind;
  status?: string;
  collectionId?: string;
};
export type JobPage = {
  items: JobView[];
  total: number;
  limit: number;
  offset: number;
};
export type OperationAction = {
  id: string;
  workspace_id: string;
  kind: string;
  job_id: string;
  action: string;
  reason: string;
  preview_sha256: string;
  status: string;
  expires_at: string;
  dispatched_at: string | null;
};
export type OperationsSummary = {
  jobs: { kind: JobKind; status: string; count: number }[];
  usage: {
    status: string;
    records: number;
    observed_tokens: number | null;
    reserved_tokens: number | null;
    observed_cost_usd: number | string | null;
    cost_records: number;
  }[];
};
export type ReadinessCheck = {
  ok: boolean;
  code?: string;
  model?: string;
  provider_id?: string;
  schema_head?: string;
  remaining_tokens?: number | null;
  configured?: boolean;
  blocked?: boolean | null;
};
export type Readiness = {
  scope: string;
  ready: boolean;
  checks: Record<string, ReadinessCheck>;
  live_inference_verified: boolean;
  production_auth_configured: boolean;
  reconcile_enabled: boolean;
};
export const JOB_LABEL: Record<JobKind, string> = {
  ocr: "OCR",
  compiler: "Biên soạn",
  index: "Chỉ mục",
  auto_review: "Rà soát tự động",
  review: "Rà soát ngữ nghĩa",
  spelling: "Kiểm tra chính tả",
  turn: "Lượt hỏi",
  backup: "Sao lưu",
};
export const JOB_STATUSES = [
  "queued",
  "running",
  "completed",
  "failed",
  "uncertain",
  "cancelled",
] as const;
export function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    queued: "Đang chờ",
    dispatched: "Đã giao lại",
    running: "Đang chạy",
    completed: "Hoàn tất",
    failed: "Thất bại",
    uncertain: "Chưa rõ kết quả",
    cancelled: "Đã hủy",
    deleting: "Đang xóa",
    deleted: "Đã xóa",
    preview: "Chưa xác nhận",
    pending: "Chờ giao tác vụ",
    superseded: "Đã thay đổi, không còn áp dụng",
  };
  return labels[status] ?? status;
}
