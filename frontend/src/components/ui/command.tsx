import { Command as CommandPrimitive } from "cmdk";
import { Search } from "lucide-react";
import type * as React from "react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

function Command({
  className,
  ...props
}: React.ComponentProps<typeof CommandPrimitive>) {
  return (
    <CommandPrimitive
      data-slot="command"
      className={cn(
        "flex h-full w-full flex-col overflow-hidden rounded-2xl bg-popover text-popover-foreground",
        className,
      )}
      {...props}
    />
  );
}

function CommandDialog({
  title = "Trình đơn lệnh",
  children,
  contentClassName,
  ...props
}: React.ComponentProps<typeof Dialog> & {
  title?: string;
  contentClassName?: string;
}) {
  return (
    <Dialog {...props}>
      <DialogContent
        className={cn(
          "max-w-lg sm:max-w-xl w-[calc(100vw-1.5rem)] max-h-[85vh] sm:max-h-[80vh] flex flex-col rounded-2xl border border-border/80 bg-popover/98 backdrop-blur-2xl shadow-2xl overflow-hidden p-0",
          contentClassName,
        )}
        showCloseButton={false}
      >
        <DialogTitle className="sr-only">{title}</DialogTitle>
        <Command className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:text-muted-foreground [&_[cmdk-group]:not([hidden])_~[cmdk-group]]:pt-1 [&_[cmdk-input-wrapper]_svg]:size-5">
          {children}
        </Command>
      </DialogContent>
    </Dialog>
  );
}

function CommandInput({
  className,
  ...props
}: React.ComponentProps<typeof CommandPrimitive.Input>) {
  return (
    <div
      data-slot="command-input-wrapper"
      className="flex h-12 sm:h-13 shrink-0 items-center gap-3 border-b border-border/70 px-3.5 sm:px-4 bg-transparent"
    >
      <Search className="size-4.5 shrink-0 text-muted-foreground/70" />
      <CommandPrimitive.Input
        data-slot="command-input"
        className={cn(
          "type-control flex h-10 w-full bg-transparent text-base sm:text-sm outline-none placeholder:text-muted-foreground/60 disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
        {...props}
      />
    </div>
  );
}

function CommandList({
  className,
  ...props
}: React.ComponentProps<typeof CommandPrimitive.List>) {
  return (
    <CommandPrimitive.List
      data-slot="command-list"
      className={cn(
        "max-h-[60vh] sm:max-h-[460px] overflow-y-auto overflow-x-hidden p-1.5 sm:p-2 scroll-smooth [scrollbar-width:thin] [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-muted-foreground/20 hover:[&::-webkit-scrollbar-thumb]:bg-muted-foreground/35",
        className,
      )}
      {...props}
    />
  );
}

function CommandEmpty(
  props: React.ComponentProps<typeof CommandPrimitive.Empty>,
) {
  return (
    <CommandPrimitive.Empty
      data-slot="command-empty"
      className="py-12 text-center text-sm text-muted-foreground"
      {...props}
    />
  );
}

function CommandGroup({
  className,
  ...props
}: React.ComponentProps<typeof CommandPrimitive.Group>) {
  return (
    <CommandPrimitive.Group
      data-slot="command-group"
      className={cn(
        "overflow-hidden p-1 text-foreground [&_[cmdk-group-heading]]:type-metadata [&_[cmdk-group-heading]]:px-2.5 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-muted-foreground/70",
        className,
      )}
      {...props}
    />
  );
}

function CommandItem({
  className,
  ...props
}: React.ComponentProps<typeof CommandPrimitive.Item>) {
  return (
    <CommandPrimitive.Item
      data-slot="command-item"
      className={cn(
        "type-control group relative flex cursor-pointer select-none items-center gap-3 rounded-xl px-2.5 sm:px-3 py-2.5 sm:py-2 text-sm outline-none transition-all duration-150 data-[disabled=true]:pointer-events-none data-[selected=true]:bg-accent/80 dark:data-[selected=true]:bg-accent/50 data-[disabled=true]:opacity-50",
        className,
      )}
      {...props}
    />
  );
}

function CommandSeparator({
  className,
  ...props
}: React.ComponentProps<typeof CommandPrimitive.Separator>) {
  return (
    <CommandPrimitive.Separator
      data-slot="command-separator"
      className={cn("-mx-1 my-1.5 h-px bg-border/60", className)}
      {...props}
    />
  );
}

function CommandShortcut({
  className,
  ...props
}: React.ComponentProps<"span">) {
  return (
    <span
      className={cn(
        "ml-auto hidden sm:inline-flex items-center gap-1 rounded-md border border-border/70 bg-muted/60 px-1.5 py-0.5 font-mono text-[10px] font-medium tracking-tight text-muted-foreground transition-opacity",
        className,
      )}
      {...props}
    />
  );
}

export {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
};
