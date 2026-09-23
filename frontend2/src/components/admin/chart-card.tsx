import { RefreshCw } from "lucide-react";
import type * as React from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function ChartCard({
  title,
  description,
  action,
  children,
  className,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`overflow-hidden rounded-lg border bg-card ${className ?? ""}`}
    >
      <div className="flex items-start justify-between gap-3 border-b px-4 py-4 sm:px-5">
        <div className="min-w-0">
          <h2 className="text-base font-semibold">{title}</h2>
          {description ? (
            <p className="type-supporting mt-1 text-muted-foreground">
              {description}
            </p>
          ) : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
      {children}
    </section>
  );
}

export function ChartLoading() {
  return (
    <div className="space-y-3 p-4 sm:p-5">
      <Skeleton className="h-[220px] w-full sm:h-[280px]" />
    </div>
  );
}

export function ChartEmpty({
  title = "Chưa có dữ liệu",
  description = "Dữ liệu sẽ xuất hiện khi hoạt động được ghi nhận.",
  compact = false,
}: {
  title?: string;
  description?: string;
  compact?: boolean;
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center px-4 text-center ${
        compact ? "h-[160px] sm:h-[180px]" : "h-[220px] sm:h-[280px]"
      }`}
    >
      <p className="text-sm font-medium">{title}</p>
      <p className="mt-1 text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

export function ChartError({ onRetry }: { onRetry?: () => void }) {
  return (
    <div className="flex h-[220px] flex-col items-center justify-center gap-2 px-4 text-center sm:h-[280px]">
      <p className="text-sm font-medium">Không thể tải dữ liệu biểu đồ</p>
      <p className="text-sm text-muted-foreground">Hãy thử lại sau.</p>
      {onRetry ? (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RefreshCw /> Thử lại
        </Button>
      ) : null}
    </div>
  );
}
