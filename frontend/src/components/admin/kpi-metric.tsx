import { cn } from "@/lib/utils";
import type * as React from "react";

export type Trend = "positive" | "negative" | "neutral";

export interface KpiMetricProps extends React.HTMLAttributes<HTMLDivElement> {
  label?: string;
  title?: string;
  value: string | number;
  delta?: string;
  change?: string;
  trend?: Trend;
  changeType?: "increase" | "decrease" | "neutral";
  helper?: string;
  description?: string;
  icon?: React.ComponentType<{ className?: string }>;
  standalone?: boolean;
}

export function KpiMetric({
  label,
  title,
  value,
  delta,
  change,
  trend,
  changeType,
  helper,
  description,
  icon: Icon,
  standalone = false,
  className,
  ...props
}: KpiMetricProps) {
  const displayLabel = label ?? title ?? "";
  const displayHelper = helper ?? description;
  const displayDelta = delta ?? change;

  // Resolve trend
  let resolvedTrend: Trend = "neutral";
  if (trend) {
    resolvedTrend = trend;
  } else if (changeType === "increase") {
    resolvedTrend = "positive";
  } else if (changeType === "decrease") {
    resolvedTrend = "negative";
  }

  return (
    <div
      className={cn(
        "min-w-0 p-4 sm:p-5",
        standalone && "rounded-lg border border-border bg-card shadow-2xs",
        className
      )}
      {...props}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium text-muted-foreground">{displayLabel}</span>
        {Icon ? (
          <div className="flex size-7 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Icon className="size-4" aria-hidden="true" />
          </div>
        ) : null}
      </div>

      <div className="mt-2 flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground font-mono">
          {value}
        </span>
        {displayDelta ? (
          <span
            className={cn(
              "text-xs sm:text-sm font-medium",
              resolvedTrend === "positive" && "text-success",
              resolvedTrend === "negative" && "text-destructive",
              resolvedTrend === "neutral" && "text-muted-foreground"
            )}
          >
            {displayDelta}
          </span>
        ) : null}
      </div>

      {displayHelper ? <p className="mt-1 text-xs text-muted-foreground">{displayHelper}</p> : null}
    </div>
  );
}
