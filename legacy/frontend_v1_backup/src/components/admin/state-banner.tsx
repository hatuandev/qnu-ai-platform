import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { AlertTriangle, CheckCircle2, Info, RefreshCw, WifiOff, X } from "lucide-react";
import * as React from "react";

export type StateBannerVariant = "degraded" | "demo" | "offline" | "info" | "success";

export interface StateBannerProps extends React.HTMLAttributes<HTMLDivElement> {
  variant: StateBannerVariant;
  title?: string;
  description: React.ReactNode;
  timestamp?: string | Date;
  onAction?: () => void;
  actionLabel?: string;
  isActionLoading?: boolean;
  onDismiss?: () => void;
}

const VARIANT_CONFIG: Record<
  StateBannerVariant,
  {
    icon: React.ElementType;
    containerClass: string;
    iconClass: string;
    defaultTitle: string;
  }
> = {
  degraded: {
    icon: AlertTriangle,
    containerClass: "border-amber-500/30 bg-amber-500/10 text-amber-950 dark:text-amber-200",
    iconClass: "text-amber-600 dark:text-amber-400",
    defaultTitle: "Dữ liệu đang ở chế độ suy giảm (Degraded)",
  },
  demo: {
    icon: Info,
    containerClass: "border-primary/30 bg-primary/10 text-foreground",
    iconClass: "text-primary",
    defaultTitle: "Dữ liệu mẫu minh họa (Demo Mode)",
  },
  offline: {
    icon: WifiOff,
    containerClass:
      "border-destructive/30 bg-destructive/10 text-destructive-foreground dark:text-destructive",
    iconClass: "text-destructive",
    defaultTitle: "Mất kết nối máy chủ",
  },
  info: {
    icon: Info,
    containerClass: "border-border bg-muted/50 text-foreground",
    iconClass: "text-muted-foreground",
    defaultTitle: "Thông tin hệ thống",
  },
  success: {
    icon: CheckCircle2,
    containerClass:
      "border-emerald-500/30 bg-emerald-500/10 text-emerald-950 dark:text-emerald-200",
    iconClass: "text-emerald-600 dark:text-emerald-400",
    defaultTitle: "Thao tác thành công",
  },
};

export function StateBanner({
  variant,
  title,
  description,
  timestamp,
  onAction,
  actionLabel,
  isActionLoading = false,
  onDismiss,
  className,
  ...props
}: StateBannerProps) {
  const config = VARIANT_CONFIG[variant];
  const Icon = config.icon;
  const effectiveTitle = title ?? config.defaultTitle;

  const formattedTime = React.useMemo(() => {
    if (!timestamp) return null;
    if (typeof timestamp === "string") return timestamp;
    return timestamp.toLocaleTimeString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }, [timestamp]);

  return (
    <div
      aria-live="polite"
      className={cn(
        "flex flex-col gap-2 rounded-lg border p-3.5 sm:flex-row sm:items-center sm:justify-between text-xs transition-all",
        config.containerClass,
        className
      )}
      {...props}
    >
      <div className="flex items-start gap-3">
        <div className={cn("mt-0.5 shrink-0", config.iconClass)}>
          <Icon className="size-4" />
        </div>
        <div className="space-y-0.5">
          <div className="flex items-center gap-2 font-medium">
            <span>{effectiveTitle}</span>
            {formattedTime && (
              <span className="rounded bg-background/50 px-1.5 py-0.5 text-[10px] text-muted-foreground font-normal">
                Cập nhật: {formattedTime}
              </span>
            )}
          </div>
          <div className="text-muted-foreground leading-relaxed">{description}</div>
        </div>
      </div>

      <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
        {onAction && actionLabel && (
          <Button
            size="sm"
            variant="outline"
            onClick={onAction}
            disabled={isActionLoading}
            className="h-7 text-xs bg-background/80 hover:bg-background"
          >
            {isActionLoading && <RefreshCw className="mr-1.5 size-3 animate-spin" />}
            {actionLabel}
          </Button>
        )}
        {onDismiss && (
          <Button
            size="icon-sm"
            variant="ghost"
            onClick={onDismiss}
            aria-label="Đóng thông báo"
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="size-3.5" />
          </Button>
        )}
      </div>
    </div>
  );
}
