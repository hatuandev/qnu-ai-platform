import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import type * as React from "react";

export interface FieldProps extends React.HTMLAttributes<HTMLDivElement> {
  label?: string;
  required?: boolean;
  error?: string;
  hint?: string;
  htmlFor?: string;
  children: React.ReactNode;
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
  return (
    <div className={cn("space-y-1.5", className)} {...props}>
      {label && (
        <div className="flex items-center justify-between">
          <Label htmlFor={htmlFor} className="flex items-center gap-1 text-xs font-medium">
            <span>{label}</span>
            {required && <span className="text-destructive">*</span>}
          </Label>
        </div>
      )}
      {children}
      {error && <p className="text-[11px] font-medium text-destructive leading-normal">{error}</p>}
      {!error && hint && <p className="text-[11px] text-muted-foreground leading-normal">{hint}</p>}
    </div>
  );
}
