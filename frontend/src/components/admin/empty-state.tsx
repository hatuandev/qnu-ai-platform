import type * as React from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  secondaryAction,
  className,
}: {
  icon?: React.ComponentType<{ className?: string }>;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
  secondaryAction?: { label: string; onClick: () => void };
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex min-h-40 flex-col items-center justify-center px-5 py-8 text-center",
        className,
      )}
    >
      {Icon ? (
        <div className="mb-3 flex size-9 items-center justify-center rounded-md border bg-muted text-muted-foreground">
          <Icon className="size-4" />
        </div>
      ) : null}
      <h3 className="text-sm font-semibold">{title}</h3>
      {description ? (
        <p className="type-supporting mt-1 max-w-sm text-muted-foreground">
          {description}
        </p>
      ) : null}
      {action || secondaryAction ? (
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          {action ? (
            <Button size="sm" onClick={action.onClick}>
              {action.label}
            </Button>
          ) : null}
          {secondaryAction ? (
            <Button
              size="sm"
              variant="outline"
              onClick={secondaryAction.onClick}
            >
              {secondaryAction.label}
            </Button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
