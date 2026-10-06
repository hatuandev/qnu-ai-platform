import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";
import type * as React from "react";

export interface SpinnerProps extends React.OutputHTMLAttributes<HTMLOutputElement> {
  size?: "sm" | "default" | "lg";
}

export function Spinner({ size = "default", className, ...props }: SpinnerProps) {
  const sizeClasses = {
    sm: "size-3.5",
    default: "size-4",
    lg: "size-6",
  }[size];

  return (
    <output
      aria-label="Đang xử lý..."
      className={cn("inline-flex items-center justify-center text-primary", className)}
      {...props}
    >
      <Loader2 className={cn("animate-spin", sizeClasses)} />
      <span className="sr-only">Đang xử lý...</span>
    </output>
  );
}
