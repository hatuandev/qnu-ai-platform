export const STATUS_BADGE: Record<
  string,
  { label: string; className: string }
> = {
  approved: {
    label: "Hiệu lực",
    className: "bg-success/10 text-success border-success/30",
  },
  completed: {
    label: "Hiệu lực",
    className: "bg-success/10 text-success border-success/30",
  },
  ready: {
    label: "Hiệu lực",
    className: "bg-success/10 text-success border-success/30",
  },
  indexed: {
    label: "Hiệu lực",
    className: "bg-success/10 text-success border-success/30",
  },
  pending: {
    label: "Chờ duyệt",
    className: "bg-warning/10 text-warning border-warning/30",
  },
  processing: {
    label: "Đang xử lý",
    className: "bg-info/10 text-info border-info/30",
  },
  archived: {
    label: "Lưu trữ",
    className: "bg-muted text-muted-foreground border-border",
  },
  failed: {
    label: "Lỗi",
    className: "bg-destructive/10 text-destructive border-destructive/30",
  },
};

export const TASK_STATUS_BADGE: Record<
  string,
  { label: string; className: string }
> = {
  completed: {
    label: "Hoàn tất",
    className: "bg-success/10 text-success border-success/30",
  },
  processing: {
    label: "Đang xử lý",
    className: "bg-info/10 text-info border-info/30",
  },
  failed: {
    label: "Thất bại",
    className: "bg-destructive/10 text-destructive border-destructive/30",
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

export type CollectionDetailTab =
  | "documents"
  | "facts"
  | "tasks"
  | "playground";
