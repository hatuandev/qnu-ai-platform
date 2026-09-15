import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { NAVIGATION_CONFIG } from "@/navigation/config";
import { Sparkles } from "lucide-react";

interface AppSidebarProps {
  open: boolean;
  currentPath: string;
  onNavigate: (path: string) => void;
  backendOnline?: boolean;
}

export function AppSidebar({
  open,
  currentPath,
  onNavigate,
  backendOnline = true,
}: AppSidebarProps) {
  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-50 flex flex-col border-r border-border bg-card transition-all duration-300 ease-in-out select-none",
        open ? "w-64" : "w-16"
      )}
    >
      {/* 1. Sidebar Header (Brand & Logo) */}
      <div className="flex h-14 items-center gap-3 border-b border-border px-4">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-xs">
          <Sparkles className="size-5" />
        </div>
        {open && (
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
      <div className="flex-1 overflow-y-auto px-2 py-4 space-y-6">
        {NAVIGATION_CONFIG.map((section) => (
          <div key={section.id} className="space-y-1">
            {open && (
              <h4 className="px-3 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70 animate-in fade-in">
                {section.title}
              </h4>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = currentPath === item.path;

                const buttonContent = (
                  <button
                    type="button"
                    key={item.id}
                    onClick={() => onNavigate(item.path)}
                    className={cn(
                      "group relative flex w-full items-center gap-3 rounded-md px-3 py-2 text-xs transition-all duration-150",
                      isActive
                        ? "bg-primary/10 text-primary font-semibold shadow-2xs"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground",
                      !open && "justify-center px-0 py-2.5"
                    )}
                  >
                    <Icon
                      className={cn(
                        "size-4 shrink-0 transition-colors",
                        isActive
                          ? "text-primary"
                          : "text-muted-foreground group-hover:text-foreground"
                      )}
                    />
                    {open && (
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

                if (!open) {
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
              })}
            </div>
          </div>
        ))}
      </div>

      {/* 3. Sidebar Footer (Backend Live Status) */}
      <div className="border-t border-border p-3 bg-muted/20">
        <div className={cn("flex items-center gap-2", !open && "justify-center")}>
          <span
            className={cn(
              "size-2 rounded-full shrink-0",
              backendOnline ? "bg-success animate-pulse" : "bg-destructive"
            )}
          />
          {open && (
            <div className="min-w-0 flex-1 text-[11px] animate-in fade-in">
              <p className="font-medium truncate text-foreground">
                {backendOnline ? "Backend Connected" : "Backend Offline"}
              </p>
              <p className="text-[10px] text-muted-foreground font-mono">Port 8001 / REST API</p>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
