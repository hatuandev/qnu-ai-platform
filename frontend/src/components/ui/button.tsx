import { cn } from "@/lib/utils";
import { Slot } from "@radix-ui/react-slot";
import * as React from "react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
  size?: "default" | "sm" | "lg" | "icon" | "icon-sm";
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";

    const variantClasses = {
      default:
        "bg-primary text-primary-foreground hover:bg-primary/90 shadow-2xs active:scale-[0.98]",
      destructive:
        "bg-destructive text-destructive-foreground hover:bg-destructive/90 shadow-2xs active:scale-[0.98]",
      outline:
        "border border-border bg-background hover:bg-muted text-foreground active:scale-[0.98]",
      secondary: "bg-muted text-foreground hover:bg-muted/80 active:scale-[0.98]",
      ghost: "hover:bg-muted hover:text-foreground",
      link: "text-primary underline-offset-4 hover:underline p-0 h-auto",
    }[variant];

    const sizeClasses = {
      default: "h-[var(--control-height)] px-3.5",
      sm: "h-[var(--control-height-sm)] rounded-md px-3 text-xs",
      lg: "h-10 rounded-md px-5",
      icon: "size-9 p-0",
      "icon-sm": "size-8 p-0 text-xs",
    }[size];

    return (
      <Comp
        className={cn(
          "type-control inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:pointer-events-none disabled:opacity-50 select-none [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
          variantClasses,
          sizeClasses,
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button };
