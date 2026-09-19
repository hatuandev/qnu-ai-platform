import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { FolderOpen, SearchX } from "lucide-react";
import type * as React from "react";

export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "empty" | "filter-empty";
  icon?: React.ElementType;
  title?: string;
  description?: string;
  action?: React.ReactNode;
  onReset?: () => void;
  resetLabel?: string;
}

export function EmptyState({
  variant = "empty",
  icon,
  title,
  description,
  action,
  onReset,
  resetLabel = "Xóa bộ lọc",
  className,
  ...props
}: EmptyStateProps) {
  const isFilterEmpty = variant === "filter-empty";
  const DefaultIcon = isFilterEmpty ? SearchX : FolderOpen;
  const Icon = icon ?? DefaultIcon;
  const effectiveTitle = title ?? (isFilterEmpty ? "Không tìm thấy kết quả" : "Không có dữ liệu");
  const effectiveDescription =
    description ??
    (isFilterEmpty
      ? "Không có mục nào khớp với điều kiện lọc hoặc từ khóa tìm kiếm của bạn."
      : undefined);

  return (
    <div
      className={cn(
        "flex min-h-[220px] flex-col items-center justify-center rounded-lg border border-dashed border-border bg-muted/20 p-8 text-center",
        className
      )}
      {...props}
    >
      <div className="flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground mb-3">
        <Icon className="size-6" />
      </div>
      <h3 className="text-sm font-semibold text-foreground">{effectiveTitle}</h3>
      {effectiveDescription && (
        <p className="mt-1 max-w-sm text-xs text-muted-foreground leading-relaxed">
          {effectiveDescription}
        </p>
      )}
      {action ? (
        <div className="mt-4">{action}</div>
      ) : onReset ? (
        <div className="mt-4">
          <Button variant="outline" size="sm" onClick={onReset} className="text-xs">
            {resetLabel}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
