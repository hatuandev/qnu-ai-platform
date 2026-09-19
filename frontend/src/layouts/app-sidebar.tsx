import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { NAVIGATION_CONFIG, type NavItem } from "@/navigation/config";
import { ChevronDown, ChevronRight, Sparkles } from "lucide-react";
import * as React from "react";

interface AppSidebarProps {
  open: boolean;
  currentPath: string;
  onNavigate: (path: string) => void;
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
  backendOnline = true,
  isMobile = false,
  onCloseMobile,
}: AppSidebarProps) {
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

  const handleItemClick = (path: string) => {
    onNavigate(path);
    if (isMobile) {
      onCloseMobile?.();
    }
  };

  return (
    <aside
      className={cn(
        "flex flex-col bg-card transition-all duration-300 ease-in-out select-none",
        isMobile
          ? "h-full w-full border-none"
          : cn(
              "hidden lg:flex fixed inset-y-0 left-0 z-50 border-r border-border",
              open ? "w-64" : "w-16"
            )
      )}
    >
      {/* 1. Sidebar Header (Brand & Logo) */}
      <div className="flex h-14 shrink-0 items-center gap-3 border-b border-border px-4">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-xs">
          <Sparkles className="size-5" />
        </div>
        {effectiveOpen && (
          <div className="min-w-0 flex-1 animate-in fade-in duration-200">
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-sm tracking-tight truncate">QNU.AI</span>
              <span className="rounded bg-primary/10 px-1.5 py-0.2 text-[10px] font-semibold text-primary">
                Platform
              </span>
            </div>
            <p className="text-[10px] text-muted-foreground truncate">Đại học Quy Nhơn</p>
          </div>
        )}
      </div>

      {/* 2. Scrollable Navigation Menu */}
      <div className="flex-1 overflow-y-auto px-2 py-4 space-y-5">
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
                    className="flex w-full items-center justify-between px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70 hover:text-foreground transition-colors"
                  >
                    <span className="flex items-center gap-1">
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
                <h4 className="px-3 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70 animate-in fade-in">
                  {section.title}
                </h4>
              )}
              <div className="space-y-0.5">{visibleItems.map((item) => renderNavItem(item))}</div>
            </div>
          );
        })}
      </div>

      {/* 3. Sidebar Footer (Clean System Status - No Dev Junk) */}
      <div className="shrink-0 border-t border-border p-3 bg-muted/20">
        <div className={cn("flex items-center gap-2", !effectiveOpen && "justify-center")}>
          <span
            className={cn(
              "size-2 rounded-full shrink-0",
              backendOnline ? "bg-success animate-pulse" : "bg-destructive"
            )}
          />
          {effectiveOpen && (
            <div className="min-w-0 flex-1 text-[11px] animate-in fade-in">
              <p className="font-medium truncate text-foreground">
                {backendOnline ? "Hệ thống sẵn sàng" : "Mất kết nối máy chủ"}
              </p>
              <p className="text-[10px] text-muted-foreground">
                {backendOnline ? "Đồng bộ thời gian thực" : "Vui lòng kiểm tra mạng"}
              </p>
            </div>
          )}
        </div>
      </div>
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
          "group relative flex w-full items-center gap-3 rounded-md px-3 py-2 text-xs transition-all duration-150",
          isActive
            ? "bg-primary/10 text-primary font-semibold shadow-2xs"
            : "text-muted-foreground hover:bg-muted hover:text-foreground",
          !effectiveOpen && "justify-center px-0 py-2.5"
        )}
      >
        <Icon
          className={cn(
            "size-4 shrink-0 transition-colors",
            isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground"
          )}
        />
        {effectiveOpen && (
          <div className="flex flex-1 items-center justify-between truncate animate-in fade-in">
            <span className="truncate">{item.title}</span>
            {item.badge && (
              <Badge
                variant={item.badgeVariant || "default"}
                className="ml-auto px-1.5 py-0 text-[10px] font-medium"
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
