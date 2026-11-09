import type * as React from "react";
import { cn } from "@/lib/utils";

type Trend = "positive" | "negative" | "neutral";

export function KpiMetric({
  label,
  value,
  delta,
  trend = "neutral",
  helper,
  icon: Icon,
}: {
  label: string;
  value: string;
  delta?: string;
  trend?: Trend;
  helper?: string;
  icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="min-w-0 p-4 sm:p-5">
      <div className="flex items-center justify-between gap-3">
        <span className="type-caption text-muted-foreground">{label}</span>
        {Icon ? (
          <Icon className="size-4 text-muted-foreground" aria-hidden="true" />
        ) : null}
      </div>
      <div className="mt-2 flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className="text-[1.75rem] font-semibold tracking-tight">
          {value}
        </span>
        {delta ? (
          <span
            className={cn(
              "type-caption font-medium",
              trend === "positive" && "text-success",
              trend === "negative" && "text-destructive",
              trend === "neutral" && "text-muted-foreground",
            )}
          >
            {delta}
          </span>
        ) : null}
      </div>
      {helper ? (
        <p className="type-caption mt-1 text-muted-foreground">{helper}</p>
      ) : null}
    </div>
  );
}

export type { Trend };
