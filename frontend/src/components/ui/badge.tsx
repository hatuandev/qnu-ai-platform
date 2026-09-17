import { cn } from "@/lib/utils";
import type * as React from "react";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variantClasses = {
    default: "border-transparent bg-primary/10 text-primary hover:bg-primary/20",
    secondary: "border-transparent bg-muted text-muted-foreground hover:bg-muted/80",
    destructive: "border-transparent bg-destructive/15 text-destructive hover:bg-destructive/25",
    outline: "text-foreground border-border/80 bg-background/50",
    success: "border-transparent bg-success/15 text-success font-medium",
    warning: "border-transparent bg-warning/15 text-warning font-medium",
    info: "border-transparent bg-info/15 text-info font-medium",
  }[variant];

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 select-none",
        variantClasses,
        className
      )}
      {...props}
    />
  );
}

export { Badge };
