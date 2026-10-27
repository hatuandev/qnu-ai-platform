import * as PopoverPrimitive from "@radix-ui/react-popover";
import type * as React from "react";
import { cn } from "@/lib/utils";

const Popover = PopoverPrimitive.Root;
const PopoverTrigger = PopoverPrimitive.Trigger;
const PopoverAnchor = PopoverPrimitive.Anchor;

function PopoverContent({
  className,
  align = "center",
  sideOffset = 4,
  ...props
}: React.ComponentProps<typeof PopoverPrimitive.Content>) {
  return (
    <PopoverPrimitive.Portal>
      <PopoverPrimitive.Content
        data-slot="popover-content"
        align={align}
        sideOffset={sideOffset}
        className={cn(
          "z-50 w-[240px] rounded-lg border bg-popover p-1.5 text-popover-foreground shadow-sm outline-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0 data-[state=open]:zoom-in-[.98] data-[state=closed]:zoom-out-[.98] data-[state=open]:duration-[var(--motion-base)] data-[state=closed]:duration-[var(--motion-fast)] data-[state=open]:ease-out data-[state=closed]:ease-in data-[side=bottom]:data-[state=open]:slide-in-from-top-1 data-[side=bottom]:data-[state=closed]:slide-out-to-top-1 data-[side=top]:data-[state=open]:slide-in-from-bottom-1 data-[side=top]:data-[state=closed]:slide-out-to-bottom-1 data-[side=left]:data-[state=open]:slide-in-from-right-1 data-[side=left]:data-[state=closed]:slide-out-to-right-1 data-[side=right]:data-[state=open]:slide-in-from-left-1 data-[side=right]:data-[state=closed]:slide-out-to-left-1",
          className,
        )}
        {...props}
      />
    </PopoverPrimitive.Portal>
  );
}

function PopoverClose({
  className,
  ...props
}: React.ComponentProps<typeof PopoverPrimitive.Close>) {
  return (
    <PopoverPrimitive.Close
      className={cn(
        "rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40",
        className,
      )}
      {...props}
    />
  );
}

export { Popover, PopoverAnchor, PopoverClose, PopoverContent, PopoverTrigger };
