import { cn } from "@/lib/utils";
import type * as React from "react";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
}: {
  eyebrow?: string;
  title: React.ReactNode;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn("flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between", className)}
    >
      <div className="min-w-0">
        <div className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {eyebrow ?? "Quản trị AI"}
        </div>
        <h1 className="type-page-title m-0 text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
          {title}
        </h1>
        {description ? (
          <p className="mt-1.5 max-w-3xl text-sm sm:text-base leading-relaxed text-muted-foreground">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}
