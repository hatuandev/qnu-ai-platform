import type * as React from "react";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export function Field({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div className={cn("grid content-start gap-2", className)} {...props} />
  );
}

export function FieldLabel({
  className,
  required,
  children,
  ...props
}: React.ComponentProps<typeof Label> & { required?: boolean }) {
  return (
    <Label className={cn("font-medium", className)} {...props}>
      {children}
      {required ? <span className="ml-1 text-destructive">*</span> : null}
    </Label>
  );
}

export function FieldDescription({
  className,
  ...props
}: React.ComponentProps<"p">) {
  return (
    <p
      className={cn(
        "text-[length:var(--font-size-field-help)] text-muted-foreground",
        className,
      )}
      {...props}
    />
  );
}

export function FieldError({
  id,
  className,
  children,
  ...props
}: React.ComponentProps<"p">) {
  return (
    <p
      id={id}
      role="alert"
      className={cn(
        "text-[length:var(--font-size-field-help)] text-destructive",
        className,
      )}
      {...props}
    >
      {children}
    </p>
  );
}
