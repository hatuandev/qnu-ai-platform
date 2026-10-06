import { cn } from "@/lib/utils";
import * as React from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  sizeVariant?: "default" | "sm";
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, sizeVariant = "default", ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "type-control flex w-full rounded-md border border-input bg-background px-3 py-1 transition-[color,box-shadow] file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/20 disabled:cursor-not-allowed disabled:opacity-50",
          sizeVariant === "sm"
            ? "h-[var(--control-height-sm)] text-sm px-2.5"
            : "h-[var(--control-height)] text-sm",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
