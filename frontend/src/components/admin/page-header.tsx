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
  title: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn("flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between", className)}
    >
      <div className="min-w-0">
        <div className="type-metadata mb-2 font-semibold uppercase tracking-[0.12em] text-muted-foreground">
          {eyebrow ?? "Quản trị AI"}
        </div>
        <h1 className="type-page-title m-0">{title}</h1>
        {description ? (
          <p className="mt-1.5 max-w-2xl text-[length:var(--font-size-body)] leading-6 text-muted-foreground">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}
