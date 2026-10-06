import type * as React from "react";
import { cn } from "@/lib/utils";

export function SettingsRow({
  title,
  description,
  control,
  className,
}: {
  title: string;
  description: string;
  control: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 border-b py-4 first:pt-0 last:border-b-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between sm:gap-6",
        className,
      )}
    >
      <div className="min-w-0">
        <h3 className="text-sm font-medium">{title}</h3>
        <p className="type-supporting mt-1 text-muted-foreground">
          {description}
        </p>
      </div>
      <div className="shrink-0">{control}</div>
    </div>
  );
}
