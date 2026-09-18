import { useTheme } from "@/components/theme-provider";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Kbd } from "@/components/ui/kbd";
import { useAuth } from "@/contexts/auth-context";
import { NAVIGATION_CONFIG } from "@/navigation/config";
import {
  ChevronRight,
  ExternalLink,
  LogOut,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  Sun,
} from "lucide-react";
import * as React from "react";

interface TopbarProps {
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
  onOpenCommand: () => void;
  currentPath: string;
  onNavigate?: (path: string) => void;
}

export function Topbar({
  sidebarOpen,
  onToggleSidebar,
  onOpenCommand,
  currentPath,
  onNavigate,
}: TopbarProps) {
  const { resolvedTheme, setTheme } = useTheme();
  const { logout } = useAuth();

  const handleLogout = React.useCallback(async () => {
    await logout();
    if (onNavigate) {
      onNavigate("/login");
    } else {
      window.location.href = "/login";
    }
  }, [logout, onNavigate]);

  // Compute breadcrumbs from current path
  const breadcrumbInfo = React.useMemo(() => {
    for (const section of NAVIGATION_CONFIG) {
      for (const item of section.items) {
        const isExactPath = item.path === currentPath;
        const isNestedPath = item.path !== "/" && currentPath.startsWith(`${item.path}/`);
        if (isExactPath || isNestedPath) {
          return { section: section.title, item: item.title };
        }
      }
    }
    return { section: "Hệ Thống", item: "Tổng Quan" };
  }, [currentPath]);

  return (
    <header className="sticky top-0 z-40 flex h-14 w-full items-center justify-between border-b border-border bg-background/80 px-4 backdrop-blur-md transition-all">
      {/* Left: Sidebar Toggle & Breadcrumbs */}
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onToggleSidebar}
          className="text-muted-foreground hover:text-foreground"
          title={sidebarOpen ? "Thu gọn thanh bên" : "Mở rộng thanh bên"}
          aria-label="Toggle Sidebar"
        >
          {sidebarOpen ? (
            <PanelLeftClose className="size-4" />
          ) : (
            <PanelLeftOpen className="size-4" />
          )}
        </Button>

        {/* Breadcrumbs */}
        <nav aria-label="Breadcrumbs" className="hidden items-center gap-1.5 text-xs sm:flex">
          <span className="font-semibold text-foreground/80">QNU Studio</span>
          <ChevronRight className="size-3.5 text-muted-foreground" />
          <span className="text-muted-foreground">{breadcrumbInfo.section}</span>
          <ChevronRight className="size-3.5 text-muted-foreground" />
          <span className="font-medium text-primary">{breadcrumbInfo.item}</span>
        </nav>
      </div>

      {/* Right: Search, Theme Toggle, User Profile */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Quick Search Button (Ctrl + K) */}
        <button
          type="button"
          onClick={onOpenCommand}
          className="flex h-8 w-44 sm:w-60 items-center justify-between rounded-md border border-input bg-background/50 px-2.5 text-xs text-muted-foreground shadow-2xs transition-colors hover:bg-muted/50 hover:text-foreground"
          aria-label="Mở tìm kiếm nhanh"
        >
          <div className="flex items-center gap-2 truncate">
            <Search className="size-3.5 shrink-0" />
            <span className="truncate">Tìm kiếm nhanh...</span>
          </div>
          <Kbd className="hidden sm:inline-flex">Ctrl K</Kbd>
        </button>

        {/* Theme Toggle Button */}
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
          title={
            resolvedTheme === "dark" ? "Chuyển sang giao diện Sáng" : "Chuyển sang giao diện Tối"
          }
          aria-label="Toggle Theme"
        >
          {resolvedTheme === "dark" ? (
            <Sun className="size-4 text-warning" />
          ) : (
            <Moon className="size-4" />
          )}
        </Button>

        {/* User Profile Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="gap-2 px-1.5 hover:bg-muted">
              <Avatar className="size-7">
                <AvatarFallback className="text-[11px] font-bold text-primary bg-primary/10">
                  QNU
                </AvatarFallback>
              </Avatar>
              <div className="hidden text-left sm:block">
                <p className="text-xs font-semibold leading-none text-foreground">Cán bộ QNU</p>
                <p className="text-[10px] text-muted-foreground">Admin Portal</p>
              </div>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <p className="text-xs font-semibold text-foreground">Cán bộ Quản trị Hệ thống</p>
              <p className="text-[11px] text-muted-foreground font-normal">admin@qnu.edu.vn</p>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <a
                href="http://localhost:8001/docs"
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-between cursor-pointer"
              >
                <span>Swagger REST API</span>
                <ExternalLink className="size-3 text-muted-foreground" />
              </a>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <a
                href="http://localhost:6333/dashboard"
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-between cursor-pointer"
              >
                <span>Qdrant Vector DB</span>
                <ExternalLink className="size-3 text-muted-foreground" />
              </a>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={handleLogout}
              className="text-destructive cursor-pointer flex items-center justify-between"
            >
              <span>Đăng xuất</span>
              <LogOut className="size-3.5 text-destructive" />
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
