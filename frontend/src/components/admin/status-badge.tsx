import { cn } from "@/lib/utils";
import type * as React from "react";

export type StatusType =
  | "ready"
  | "healthy"
  | "online"
  | "processing"
  | "ingesting"
  | "closed"
  | "open"
  | "half_open"
  | "warning"
  | "error"
  | "offline"
  | "failed";

export interface StatusBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  status: StatusType;
  label?: string;
  pulse?: boolean;
}

const STATUS_CONFIGS: Record<
  StatusType,
  { defaultLabel: string; bgClass: string; textClass: string; dotClass: string }
> = {
  ready: {
    defaultLabel: "Sẵn sàng",
    bgClass: "bg-success/15",
    textClass: "text-success",
    dotClass: "bg-success",
  },
  healthy: {
    defaultLabel: "Khỏe mạnh",
    bgClass: "bg-success/15",
    textClass: "text-success",
    dotClass: "bg-success",
  },
  online: {
    defaultLabel: "Trực tuyến",
    bgClass: "bg-success/15",
    textClass: "text-success",
    dotClass: "bg-success",
  },
  processing: {
    defaultLabel: "Đang xử lý",
    bgClass: "bg-primary/15",
    textClass: "text-primary",
    dotClass: "bg-primary",
  },
  ingesting: {
    defaultLabel: "Đang bóc tách",
    bgClass: "bg-primary/15",
    textClass: "text-primary",
    dotClass: "bg-primary",
  },
  closed: {
    defaultLabel: "Closed (Bình thường)",
    bgClass: "bg-success/15",
    textClass: "text-success",
    dotClass: "bg-success",
  },
  half_open: {
    defaultLabel: "Half-Open (Thăm dò)",
    bgClass: "bg-warning/15",
    textClass: "text-warning",
    dotClass: "bg-warning",
  },
  open: {
    defaultLabel: "Open (Ngắt mạch)",
    bgClass: "bg-destructive/15",
    textClass: "text-destructive",
    dotClass: "bg-destructive",
  },
  warning: {
    defaultLabel: "Cảnh báo",
    bgClass: "bg-warning/15",
    textClass: "text-warning",
    dotClass: "bg-warning",
  },
  error: {
    defaultLabel: "Lỗi kết nối",
    bgClass: "bg-destructive/15",
    textClass: "text-destructive",
    dotClass: "bg-destructive",
  },
  offline: {
    defaultLabel: "Ngoại tuyến",
    bgClass: "bg-muted",
    textClass: "text-muted-foreground",
    dotClass: "bg-muted-foreground",
  },
  failed: {
    defaultLabel: "Thất bại",
    bgClass: "bg-destructive/15",
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
