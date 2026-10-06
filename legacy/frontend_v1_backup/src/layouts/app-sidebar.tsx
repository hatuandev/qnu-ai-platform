import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useAuth } from "@/contexts/auth-context";
import { cn } from "@/lib/utils";
import { NAVIGATION_CONFIG, type NavItem } from "@/navigation/config";
import { ChevronDown, ChevronRight, Sparkles } from "lucide-react";
import * as React from "react";

interface AppSidebarProps {
  open: boolean;
  currentPath: string;
  onNavigate: (path: string) => void;
  onToggleSidebar?: () => void;
  backendOnline?: boolean;
  isMobile?: boolean;
  onCloseMobile?: () => void;
}

function isPathActive(itemPath: string, currentPath: string): boolean {
  if (itemPath === "/") {
    return currentPath === "/";
  }
  if (itemPath === "/assistants") {
    return currentPath.startsWith("/assistants");
  }
  if (itemPath === "/knowledge") {
    return (
      currentPath === "/knowledge" ||
      (currentPath.startsWith("/knowledge/") &&
        !currentPath.startsWith("/knowledge/settings") &&
        !currentPath.startsWith("/knowledge/ocr-lab"))
    );
  }
  if (itemPath === "/models") {
    return currentPath.startsWith("/models");
  }
  if (itemPath === "/conversations") {
    return currentPath.startsWith("/conversations");
  }
  if (itemPath === "/quality") {
    return (
      currentPath === "/quality" ||
      currentPath.startsWith("/quality/") ||
      currentPath.startsWith("/evaluation")
    );
  }
  if (itemPath === "/operations/runs") {
    return currentPath.startsWith("/operations/runs") || currentPath.startsWith("/runs");
  }
  if (itemPath === "/settings/integrations") {
    return (
      currentPath.startsWith("/settings/integrations") ||
      currentPath.startsWith("/channels") ||
      currentPath.startsWith("/developer")
    );
  }
  if (itemPath === "/advanced/workflows") {
    return (
      currentPath.startsWith("/advanced/workflows") ||
      currentPath.startsWith("/workflows") ||
      currentPath.startsWith("/canvas")
    );
  }
  if (itemPath === "/advanced/capabilities/nodes") {
    return (
      currentPath.startsWith("/advanced/capabilities/nodes") || currentPath.startsWith("/nodes")
    );
  }
  if (itemPath === "/advanced/capabilities/tools") {
    return (
      currentPath.startsWith("/advanced/capabilities/tools") || currentPath.startsWith("/tools")
    );
  }
  if (itemPath === "/knowledge/settings/document-types") {
    return (
      currentPath.startsWith("/knowledge/settings/document-types") ||
      currentPath.startsWith("/document-types")
    );
  }
  if (itemPath === "/knowledge/ocr-lab") {
    return currentPath.startsWith("/knowledge/ocr-lab") || currentPath.startsWith("/ocr");
  }
  return currentPath === itemPath || currentPath.startsWith(`${itemPath}/`);
}

export function AppSidebar({
  open,
  currentPath,
  onNavigate,
  onToggleSidebar,
  backendOnline = true,
  isMobile = false,
  onCloseMobile,
}: AppSidebarProps) {
  const { actor } = useAuth();
  const [advancedOpen, setAdvancedOpen] = React.useState<boolean>(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("qnu-advanced-open");
      return saved !== null ? saved === "true" : false;
    }
    return false;
  });

  const toggleAdvanced = () => {
    setAdvancedOpen((prev) => {
      const next = !prev;
      localStorage.setItem("qnu-advanced-open", String(next));
      return next;
    });
  };

  const isDevMode = import.meta.env.DEV;
  const effectiveOpen = isMobile || open;

  const displayName = actor?.username || "Cán bộ QNU";
  const displayEmail = actor?.username ? `${actor.username}@qnu.edu.vn` : "canbo@qnu.edu.vn";
  const avatarInitial = displayName.charAt(0).toUpperCase();

  const handleItemClick = (path: string) => {
    onNavigate(path);
    if (isMobile) {
      onCloseMobile?.();
    }
  };

  return (
    <aside
      data-state={effectiveOpen ? "expanded" : "collapsed"}
      className={cn(
        "fixed inset-y-0 left-0 z-40 hidden h-svh flex-col border-r border-border bg-background transition-[width] duration-200 lg:flex select-none",
        open ? "w-[var(--sidebar-width)]" : "w-16",
        isMobile && "flex z-50 w-full h-full border-none"
      )}
    >
      {/* 1. Sidebar Header (Brand & Logo) - Chuẩn QLKTX min-h-16 (64px) */}
      <div className="flex min-h-16 h-16 w-full shrink-0 items-center gap-3 px-3 border-b border-border/70">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-xs">
          <Sparkles className="size-5" />
        </div>
        {effectiveOpen && (
          <div className="min-w-0 flex-1 animate-in fade-in duration-200">
            <p className="text-[15px] font-bold text-foreground tracking-tight leading-tight truncate">
              QNU AI Platform
            </p>
            <p className="text-xs text-muted-foreground leading-tight truncate mt-0.5">
              Trường Đại học Quy Nhơn
            </p>
          </div>
        )}
      </div>

      {/* 2. Scrollable Navigation Menu - Chuẩn QLKTX */}
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain py-4 [scrollbar-gutter:stable] [-webkit-overflow-scrolling:touch] px-3 space-y-4">
        {NAVIGATION_CONFIG.map((section) => {
          if (section.isAdvancedSection) {
            const visibleItems = section.items.filter((item) => !item.isDevOnly || isDevMode);
            const hasActiveChild = visibleItems.some((item) =>
              isPathActive(item.path, currentPath)
            );

            return (
              <div key={section.id} className="space-y-1 pt-1 border-t border-border/60">
                {effectiveOpen ? (
                  <button
                    type="button"
                    onClick={toggleAdvanced}
                    className="flex w-full items-center justify-between px-3 py-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground/80 hover:text-foreground transition-colors mb-1 select-none"
                  >
                    <span className="flex items-center gap-1.5">
                      {section.title}
                      {hasActiveChild && (
                        <span className="size-1.5 rounded-full bg-primary inline-block" />
                      )}
                    </span>
                    {advancedOpen ? (
                      <ChevronDown className="size-3.5" />
                    ) : (
                      <ChevronRight className="size-3.5" />
                    )}
                  </button>
                ) : (
                  <div className="h-px bg-border/60 my-2" />
                )}

                {(advancedOpen || !effectiveOpen) && (
                  <div className="space-y-0.5">
                    {visibleItems.map((item) => renderNavItem(item))}
                  </div>
                )}
              </div>
            );
          }

          const visibleItems = section.items.filter((item) => !item.isDevOnly || isDevMode);

          return (
            <div key={section.id} className="space-y-1">
              {effectiveOpen && (
                <h4 className="px-3 py-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground/80 mb-1 select-none animate-in fade-in">
                  {section.title}
                </h4>
              )}
              <div className="space-y-0.5">{visibleItems.map((item) => renderNavItem(item))}</div>
            </div>
          );
        })}
      </div>

      {/* 3. Bottom User Profile & System Status Footer - Chuẩn QLKTX */}
      <div className="shrink-0 border-t border-border p-3 px-3">
        {effectiveOpen ? (
          <div className="flex items-center gap-3 animate-in fade-in duration-200">
            <div className="flex size-8.5 shrink-0 items-center justify-center rounded-full bg-primary/10 border border-primary/20 text-primary font-bold text-xs">
              {avatarInitial}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-foreground truncate leading-tight">
                {displayName}
              </p>
              <p className="text-xs text-muted-foreground truncate leading-tight mt-0.5">
                {displayEmail}
              </p>
            </div>
            <span
              className={cn(
                "size-2 rounded-full shrink-0 ml-auto",
                backendOnline ? "bg-success" : "bg-destructive"
              )}
              title={backendOnline ? "Hệ thống trực tuyến" : "Mất kết nối máy chủ"}
            />
          </div>
        ) : (
          <div className="flex justify-center">
            <Tooltip delayDuration={0}>
              <TooltipTrigger asChild>
                <div className="flex size-8.5 shrink-0 items-center justify-center rounded-full bg-primary/10 border border-primary/20 text-primary font-bold text-xs cursor-pointer">
                  {avatarInitial}
                </div>
              </TooltipTrigger>
              <TooltipContent side="right" className="text-xs">
                <p className="font-semibold text-sm">{displayName}</p>
                <p className="text-xs text-muted-foreground">{displayEmail}</p>
              </TooltipContent>
            </Tooltip>
          </div>
        )}
      </div>

      {/* 4. Desktop Sidebar Resize / Toggle Handle Button - Chuẩn QLKTX */}
      {onToggleSidebar && !isMobile && (
        <button
          type="button"
          onClick={onToggleSidebar}
          aria-label={open ? "Thu gọn thanh bên" : "Mở rộng thanh bên"}
          title={open ? "Thu gọn thanh bên" : "Mở rộng thanh bên"}
          className="absolute inset-y-0 right-0 z-20 hidden w-1.5 translate-x-1/2 cursor-ew-resize hover:bg-primary/30 transition-colors lg:block"
        />
      )}
    </aside>
  );

  function renderNavItem(item: NavItem) {
    const Icon = item.icon;
    const isActive = isPathActive(item.path, currentPath);

    const buttonContent = (
      <button
        type="button"
        key={item.id}
        onClick={() => handleItemClick(item.path)}
        className={cn(
          "group relative flex w-full h-[var(--sidebar-item-height)] items-center gap-3 rounded-md px-3 text-sm transition-colors duration-150",
          isActive
            ? "bg-primary/10 text-primary font-semibold"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground font-medium",
          !effectiveOpen && "justify-center px-0"
        )}
      >
        <Icon
          className={cn(
            "size-4.5 shrink-0 transition-colors",
            isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground"
          )}
        />
        {effectiveOpen && (
          <div className="flex flex-1 items-center justify-between truncate animate-in fade-in">
            <span className="truncate">{item.title}</span>
            {item.badge && (
              <Badge
                variant={item.badgeVariant || "default"}
                className={cn(
                  "ml-auto px-1.5 py-0 text-xs font-medium rounded-sm",
                  isActive && "bg-primary text-primary-foreground"
                )}
              >
                {item.badge}
              </Badge>
            )}
          </div>
        )}
      </button>
    );

    if (!effectiveOpen) {
      return (
        <Tooltip key={item.id} delayDuration={0}>
          <TooltipTrigger asChild>{buttonContent}</TooltipTrigger>
          <TooltipContent side="right" className="flex items-center gap-2 text-xs">
            <span>{item.title}</span>
            {item.badge && (
              <Badge variant="secondary" className="px-1 py-0 text-[9px]">
                {item.badge}
              </Badge>
            )}
          </TooltipContent>
        </Tooltip>
      );
    }

    return buttonContent;
  }
}
