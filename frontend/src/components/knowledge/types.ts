export const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  approved: {
    label: "Hiệu lực",
    className: "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 border-emerald-200",
  },
  completed: {
    label: "Hiệu lực",
    className: "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 border-emerald-200",
  },
  pending: {
    label: "Chờ duyệt",
    className: "bg-amber-500/10 text-amber-600 border-amber-500/30",
  },
  processing: {
    label: "Đang xử lý",
    className: "bg-sky-500/10 text-sky-600 border-sky-500/30",
  },
  archived: {
    label: "Lưu trữ",
    className: "bg-muted text-muted-foreground border-border",
  },
  failed: {
    label: "Lỗi",
    className: "bg-rose-500/10 text-rose-600 border-rose-500/30",
  },
};

export const TASK_STATUS_BADGE: Record<string, { label: string; className: string }> = {
  completed: {
    label: "Hoàn tất",
    className: "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 border-emerald-300",
  },
  processing: {
    label: "Đang xử lý",
    className: "bg-sky-500/10 text-sky-600 border-sky-500/30",
  },
  failed: {
    label: "Thất bại",
    className: "bg-rose-500/10 text-rose-600 border-rose-500/30",
  },
  cancelled: {
    label: "Đã hủy",
    className: "bg-muted text-muted-foreground border-border",
  },
};

export interface SandboxSearchResult {
  id: string;
  title: string;
  clause: string;
  text: string;
  score: number;
  method: string;
}

export function formatFileSize(bytes: number): string {
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

export type CollectionSubView = "list" | "ingest" | "verify";

export type CollectionDetailTab = "documents" | "facts" | "tasks" | "playground";
