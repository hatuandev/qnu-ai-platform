import { cn } from "@/lib/utils";
import type * as React from "react";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variantClasses = {
    default: "border-transparent bg-primary/12 text-primary hover:bg-primary/20",
    secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
    destructive: "border-transparent bg-destructive/12 text-destructive hover:bg-destructive/20",
    outline: "text-foreground border-border/80 bg-background/50",
    success: "border-transparent bg-success/12 text-success font-medium",
    warning: "border-transparent bg-warning/12 text-foreground font-medium",
    info: "border-transparent bg-info/12 text-info font-medium",
  }[variant];

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 select-none",
        variantClasses,
        className
      )}
      {...props}
    />
  );
}

export { Badge };
