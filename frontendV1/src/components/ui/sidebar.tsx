import { Slot } from "@radix-ui/react-slot";
import { PanelLeft } from "lucide-react";
import {
  createContext,
  forwardRef,
  useContext,
  useMemo,
  useState,
} from "react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useIsMobile } from "@/hooks/use-mobile";
import { cn } from "@/lib/utils";

type SidebarState = "expanded" | "collapsed";
type SidebarContextValue = {
  state: SidebarState;
  isMobile: boolean;
  openMobile: boolean;
  setOpenMobile: (open: boolean) => void;
  toggleSidebar: () => void;
};

const SidebarContext = createContext<SidebarContextValue | null>(null);

export function SidebarProvider({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const isMobile = useIsMobile();
  const [open, setOpen] = useState(true);
  const [openMobile, setOpenMobile] = useState(false);
  const value = useMemo<SidebarContextValue>(
    () => ({
      state: open ? "expanded" : "collapsed",
      isMobile,
      openMobile,
      setOpenMobile,
      toggleSidebar: () => {
        if (isMobile) setOpenMobile((current) => !current);
        else setOpen((current) => !current);
      },
    }),
    [isMobile, open, openMobile],
  );
  return (
    <SidebarContext.Provider value={value}>
      <div
        data-sidebar-state={value.state}
        className={cn("group/sidebar-wrapper flex min-h-svh w-full", className)}
      >
        {children}
      </div>
    </SidebarContext.Provider>
  );
}

export function useSidebar() {
  const context = useContext(SidebarContext);
  if (!context)
    throw new Error("useSidebar must be used within SidebarProvider");
  return context;
}

export function Sidebar({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const { state, isMobile, openMobile, setOpenMobile } = useSidebar();
  if (isMobile)
    return (
      <Sheet open={openMobile} onOpenChange={setOpenMobile}>
        <SheetContent
          side="left"
          showClose={false}
          className="w-[var(--sidebar-width)] p-0"
        >
          <SheetTitle className="sr-only">Điều hướng</SheetTitle>
          {children}
        </SheetContent>
      </Sheet>
    );
  return (
    <aside
      data-state={state}
      className={cn(
        "fixed inset-y-0 left-0 z-40 hidden h-svh w-[var(--sidebar-width)] flex-col border-r bg-background transition-[width] duration-200 lg:flex",
        state === "collapsed" && "w-16",
        className,
      )}
    >
      {children}
    </aside>
  );
}

export function SidebarInset({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const { state } = useSidebar();
  return (
    <div
      data-state={state}
      className={cn(
        "min-h-svh min-w-0 flex-1 transition-[padding] duration-200 lg:pl-[var(--sidebar-width)]",
        state === "collapsed" && "lg:pl-16",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function SidebarTrigger({
  className,
  ...props
}: React.ComponentProps<typeof Button>) {
  const { state, isMobile, openMobile, toggleSidebar } = useSidebar();
  const expanded = isMobile ? openMobile : state === "expanded";
  return (
    <Button
      variant="ghost"
      size="icon"
      className={cn("shrink-0", className)}
      onClick={toggleSidebar}
      aria-label={
        isMobile
          ? expanded
            ? "Đóng điều hướng"
            : "Mở điều hướng"
          : expanded
            ? "Thu gọn thanh bên"
            : "Mở rộng thanh bên"
      }
      aria-expanded={expanded}
      {...props}
    >
      <PanelLeft />
    </Button>
  );
}

export function SidebarRail({ className }: { className?: string }) {
  const { state, toggleSidebar } = useSidebar();
  return (
    <button
      type="button"
      aria-label={
        state === "expanded" ? "Thu gọn thanh bên" : "Mở rộng thanh bên"
      }
      onClick={toggleSidebar}
      className={cn(
        "absolute inset-y-0 right-0 z-20 hidden w-3 translate-x-1/2 cursor-ew-resize lg:block",
        className,
      )}
    />
  );
}

export function SidebarHeader({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn("flex min-h-16 w-full items-center gap-3 px-4", className)}
    >
      {children}
    </div>
  );
}
export function SidebarContent({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const { state, isMobile } = useSidebar();
  const compact = state === "collapsed" && !isMobile;

  return (
    <div
      className={cn(
        "min-h-0 flex-1 overflow-y-auto overscroll-contain py-4 [scrollbar-gutter:stable] [-webkit-overflow-scrolling:touch]",
        compact ? "pl-4 pr-0" : "px-3",
        className,
      )}
    >
      {children}
    </div>
  );
}
export function SidebarFooter({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={cn("border-t p-3", className)}>{children}</div>;
}
export function SidebarGroup({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={cn("mb-5", className)}>{children}</div>;
}
export function SidebarGroupLabel({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const { state, isMobile } = useSidebar();
  return (
    <div
      className={cn(
        "mb-1.5 px-2.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/80",
        state === "collapsed" && !isMobile && "sr-only",
        className,
      )}
    >
      {children}
    </div>
  );
}
export function SidebarMenu({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={cn("space-y-0.5", className)}>{children}</div>;
}
export function SidebarMenuItem({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={className}>{children}</div>;
}

type SidebarMenuButtonProps = React.ComponentProps<"button"> & {
  isActive?: boolean;
  tooltip?: string;
  asChild?: boolean;
};

export const SidebarMenuButton = forwardRef<
  HTMLButtonElement,
  SidebarMenuButtonProps
>(function SidebarMenuButton(
  { children, className, isActive, tooltip, asChild = false, ...props },
  ref,
) {
  const { state, isMobile } = useSidebar();
  const compact = state === "collapsed" && !isMobile;
  const menuClass = cn(
    "relative flex h-[var(--sidebar-item-height)] w-full items-center gap-2.5 rounded-md px-2.5 text-left text-sm font-medium text-muted-foreground no-underline transition-colors hover:bg-accent hover:text-accent-foreground",
    isActive && "bg-accent font-semibold text-accent-foreground",
    compact && "justify-center px-2",
    className,
  );
  const content = asChild ? (
    <Slot ref={ref} className={menuClass} {...props}>
      {children}
    </Slot>
  ) : (
    <button ref={ref} type="button" className={menuClass} {...props}>
      {children}
    </button>
  );
  if (!compact || !tooltip) return content;
  return (
    <Tooltip>
      <TooltipTrigger asChild>{content}</TooltipTrigger>
      <TooltipContent side="right">{tooltip}</TooltipContent>
    </Tooltip>
  );
});

export function SidebarMenuSub({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={cn("space-y-0.5 pt-0.5", className)}>{children}</div>;
}
export function SidebarMenuSubItem({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={className}>{children}</div>;
}
type SidebarMenuSubButtonProps = React.ComponentProps<"button"> & {
  isActive?: boolean;
  asChild?: boolean;
};

export const SidebarMenuSubButton = forwardRef<
  HTMLButtonElement,
  SidebarMenuSubButtonProps
>(function SidebarMenuSubButton(
  { children, className, isActive, asChild = false, ...props },
  ref,
) {
  const menuClass = cn(
    "relative ml-5 flex h-[var(--sidebar-item-height)] items-center gap-2 rounded-md pl-3 text-[13.5px] font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
    isActive && "bg-accent font-semibold text-accent-foreground",
    className,
  );
  return asChild ? (
    <Slot ref={ref} className={menuClass} {...props}>
      {children}
    </Slot>
  ) : (
    <button ref={ref} type="button" className={menuClass} {...props}>
      {children}
    </button>
  );
});
