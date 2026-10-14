import type * as React from "react";
import { useId } from "react";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export interface FieldControlProps {
  id: string;
  "aria-describedby"?: string;
  "aria-invalid"?: boolean;
  "aria-required"?: boolean;
}

export interface FieldProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>, "children"> {
  label?: string;
  required?: boolean;
  error?: string;
  hint?: string;
  htmlFor?: string;
  children: React.ReactNode | ((control: FieldControlProps) => React.ReactNode);
}

export function Field({
  label,
  required = false,
  error,
  hint,
  htmlFor,
  className,
  children,
  ...props
}: FieldProps) {
  const generatedId = useId();
  const controlId = htmlFor || generatedId;
  const helpId = `${controlId}-help`;
  const errorId = `${controlId}-error`;
  return (
    <div className={cn("space-y-1.5", className)} {...props}>
      {label && (
        <div className="flex items-center justify-between">
          <Label
            htmlFor={controlId}
            className="flex items-center gap-1 text-xs font-medium"
          >
            <span>{label}</span>
            {required && <span className="text-destructive">*</span>}
          </Label>
        </div>
      )}
      {typeof children === "function"
        ? children({
            id: controlId,
            "aria-describedby": error ? errorId : hint ? helpId : undefined,
            "aria-invalid": error ? true : undefined,
            "aria-required": required || undefined,
          })
        : children}
      {error && (
        <p
          id={errorId}
          role="alert"
          className="text-[11px] font-medium text-destructive leading-normal"
        >
          {error}
        </p>
      )}
      {!error && hint && (
        <p
          id={helpId}
          className="text-[11px] text-muted-foreground leading-normal"
        >
          {hint}
        </p>
      )}
    </div>
  );
}

export function FieldLabel({
  className,
  ...props
}: React.ComponentProps<typeof Label>) {
  return <Label className={cn("font-medium", className)} {...props} />;
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
