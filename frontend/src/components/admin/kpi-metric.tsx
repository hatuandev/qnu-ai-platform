import { cn } from "@/lib/utils";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import type * as React from "react";

export interface KpiMetricProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  value: string | number;
  description?: string;
  change?: string;
  changeType?: "increase" | "decrease" | "neutral";
  icon?: React.ElementType;
}

export function KpiMetric({
  title,
  value,
  description,
  change,
  changeType = "neutral",
  icon: Icon,
  className,
  ...props
}: KpiMetricProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card p-5 shadow-2xs transition-shadow hover:shadow-xs",
        className
      )}
      {...props}
    >
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-muted-foreground">{title}</p>
        {Icon && (
          <div className="flex size-8 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Icon className="size-4" />
          </div>
        )}
      </div>

      <div className="mt-2">
        <h3 className="text-2xl font-bold tracking-tight text-foreground font-mono">{value}</h3>
      </div>

      {(change || description) && (
        <div className="mt-3 flex items-center gap-2 text-xs">
          {change && (
            <span
              className={cn(
                "inline-flex items-center gap-0.5 rounded-sm px-1.5 py-0.5 font-medium",
                changeType === "increase" && "bg-success/15 text-success",
                changeType === "decrease" && "bg-destructive/15 text-destructive",
                changeType === "neutral" && "bg-muted text-muted-foreground"
              )}
            >
              {changeType === "increase" && <ArrowUpRight className="size-3" />}
              {changeType === "decrease" && <ArrowDownRight className="size-3" />}
              {changeType === "neutral" && <Minus className="size-3" />}
              {change}
            </span>
          )}
          {description && <span className="text-muted-foreground text-[11px]">{description}</span>}
        </div>
      )}
    </div>
  );
}
