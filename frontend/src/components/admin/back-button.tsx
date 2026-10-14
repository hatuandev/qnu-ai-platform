import { ArrowLeft } from "lucide-react";
import type { ComponentProps } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** Navigate to an explicit parent; never depend on browser history length. */
export function BackButton({
  label,
  className,
  ...props
}: Omit<ComponentProps<typeof Button>, "children" | "asChild"> & {
  label: string;
}) {
  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      title={`Về ${label}`}
      aria-label={`Về ${label}`}
      {...props}
      className={cn(
        "shrink-0 gap-1.5 text-xs text-muted-foreground hover:text-foreground",
        className,
      )}
    >
      <ArrowLeft className="size-3.5" aria-hidden="true" />
      <span>{label}</span>
    </Button>
  );
}
