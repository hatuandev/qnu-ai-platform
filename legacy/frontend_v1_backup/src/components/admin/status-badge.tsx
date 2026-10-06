import { cn } from "@/lib/utils";
import type * as React from "react";

export type StatusType =
  | "ready"
  | "healthy"
  | "online"
  | "active"
  | "success"
  | "completed"
  | "processing"
  | "indexing"
  | "ingesting"
  | "running"
  | "review_pending"
  | "pending"
  | "approved"
  | "warning"
  | "half_open"
  | "suspended"
  | "inactive"
  | "offline"
  | "archived"
  | "closed"
  | "open"
  | "error"
  | "failed";

export interface StatusBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  status: StatusType | string;
  label?: string;
  pulse?: boolean;
}

const STATUS_CONFIGS: Record<
  string,
  { defaultLabel: string; bgClass: string; textClass: string; dotClass: string }
> = {
  ready: {
    defaultLabel: "Sẵn sàng",
    bgClass: "bg-success/12",
    textClass: "text-success",
    dotClass: "bg-success",
  },
  healthy: {
    defaultLabel: "Khỏe mạnh",
    bgClass: "bg-success/12",
    textClass: "text-success",
    dotClass: "bg-success",
  },
  online: {
    defaultLabel: "Trực tuyến",
    bgClass: "bg-success/12",
    textClass: "text-success",
    dotClass: "bg-success",
  },
  active: {
    defaultLabel: "Đang hoạt động",
    bgClass: "bg-success/12",
    textClass: "text-success",
    dotClass: "bg-success",
  },
  success: {
    defaultLabel: "Thành công",
    bgClass: "bg-success/12",
    textClass: "text-success",
    dotClass: "bg-success",
  },
  completed: {
    defaultLabel: "Hoàn tất",
    bgClass: "bg-success/12",
    textClass: "text-success",
    dotClass: "bg-success",
  },
  approved: {
    defaultLabel: "Đã phê duyệt",
    bgClass: "bg-success/12",
    textClass: "text-success",
    dotClass: "bg-success",
  },
  processing: {
    defaultLabel: "Đang xử lý",
    bgClass: "bg-primary/12",
    textClass: "text-primary",
    dotClass: "bg-primary",
  },
  indexing: {
    defaultLabel: "Đang đánh chỉ mục",
    bgClass: "bg-primary/12",
    textClass: "text-primary",
    dotClass: "bg-primary",
  },
  ingesting: {
    defaultLabel: "Đang bóc tách",
    bgClass: "bg-primary/12",
    textClass: "text-primary",
    dotClass: "bg-primary",
  },
  running: {
    defaultLabel: "Đang thực thi",
    bgClass: "bg-primary/12",
    textClass: "text-primary",
    dotClass: "bg-primary",
  },
  review_pending: {
    defaultLabel: "Chờ kiểm duyệt",
    bgClass: "bg-info/12",
    textClass: "text-info",
    dotClass: "bg-info",
  },
  pending: {
    defaultLabel: "Đang chờ",
    bgClass: "bg-info/12",
    textClass: "text-info",
    dotClass: "bg-info",
  },
  closed: {
    defaultLabel: "Closed (Bình thường)",
    bgClass: "bg-success/12",
    textClass: "text-success",
    dotClass: "bg-success",
  },
  half_open: {
    defaultLabel: "Half-Open (Thăm dò)",
    bgClass: "bg-warning/12",
    textClass: "text-foreground",
    dotClass: "bg-warning",
  },
  open: {
    defaultLabel: "Open (Ngắt mạch)",
    bgClass: "bg-destructive/12",
    textClass: "text-destructive",
    dotClass: "bg-destructive",
  },
  warning: {
    defaultLabel: "Cảnh báo",
    bgClass: "bg-warning/12",
    textClass: "text-foreground",
    dotClass: "bg-warning",
  },
  suspended: {
    defaultLabel: "Tạm ngưng",
    bgClass: "bg-destructive/12",
    textClass: "text-destructive",
    dotClass: "bg-destructive",
  },
  inactive: {
    defaultLabel: "Ngừng hoạt động",
    bgClass: "bg-secondary",
    textClass: "text-secondary-foreground",
    dotClass: "bg-muted-foreground",
  },
  offline: {
    defaultLabel: "Ngoại tuyến",
    bgClass: "bg-secondary",
    textClass: "text-secondary-foreground",
    dotClass: "bg-muted-foreground",
  },
  archived: {
    defaultLabel: "Đã lưu trữ",
    bgClass: "bg-secondary",
    textClass: "text-secondary-foreground",
    dotClass: "bg-muted-foreground",
  },
  error: {
    defaultLabel: "Lỗi",
    bgClass: "bg-destructive/12",
    textClass: "text-destructive",
    dotClass: "bg-destructive",
  },
  failed: {
    defaultLabel: "Thất bại",
    bgClass: "bg-destructive/12",
    textClass: "text-destructive",
    dotClass: "bg-destructive",
  },
};

export function StatusBadge({
  status,
  label,
  pulse = false,
  className,
  ...props
}: StatusBadgeProps) {
  const config = STATUS_CONFIGS[status] || STATUS_CONFIGS.offline;
  const displayLabel = label || config.defaultLabel;

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
        config.bgClass,
        config.textClass,
        className
      )}
      {...props}
    >
      <span className="relative flex size-2">
        {pulse && (
          <span
            className={cn(
              "absolute inline-flex size-full animate-ping rounded-full opacity-75",
              config.dotClass
            )}
          />
        )}
        <span className={cn("relative inline-flex size-2 rounded-full", config.dotClass)} />
      </span>
      <span>{displayLabel}</span>
    </div>
  );
}
