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
  Menu,
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
  onOpenMobileDrawer?: () => void;
}

export function Topbar({
  sidebarOpen,
  onToggleSidebar,
  onOpenCommand,
  currentPath,
  onNavigate,
  onOpenMobileDrawer,
}: TopbarProps) {
  const { resolvedTheme, setTheme } = useTheme();
  const { actor, logout } = useAuth();

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

  // User details derived from session
  const displayName = actor?.username || "Cán bộ QNU";
  const displayEmail = actor ? `${actor.username}@qnu.edu.vn` : "canbo@qnu.edu.vn";
  const displayRole = actor?.role === "admin" ? "Quản trị viên" : "Cán bộ chuyên môn";
  const avatarInitials = React.useMemo(() => {
    if (actor?.username) {
      return actor.username.slice(0, 2).toUpperCase();
    }
    return "QNU";
  }, [actor?.username]);

  const isDevMode = import.meta.env.DEV;

  return (
    <header className="sticky top-0 z-40 flex h-[var(--topbar-height)] w-full items-center justify-between border-b border-border bg-background/95 px-3 sm:px-4 lg:px-6 backdrop-blur transition-all">
      {/* Left: Mobile Drawer Trigger, Desktop Sidebar Toggle & Breadcrumbs */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Mobile Hamburger Trigger (< lg) */}
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onOpenMobileDrawer}
          className="size-8.5 rounded-lg text-muted-foreground hover:text-foreground lg:hidden"
          title="Mở menu điều hướng"
          aria-label="Mở menu điều hướng"
        >
          <Menu className="size-5" />
        </Button>

        {/* Desktop Sidebar Toggle (>= lg) */}
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onToggleSidebar}
          className="hidden lg:inline-flex size-8.5 rounded-lg text-muted-foreground hover:text-foreground"
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
        <nav aria-label="Breadcrumbs" className="hidden items-center gap-2 text-sm sm:flex">
          <span className="font-semibold text-foreground/80">QNU Platform</span>
          <ChevronRight className="size-3.5 text-muted-foreground/70" />
          <span className="text-muted-foreground">{breadcrumbInfo.section}</span>
          <ChevronRight className="size-3.5 text-muted-foreground/70" />
          <span className="font-medium text-primary">{breadcrumbInfo.item}</span>
        </nav>
      </div>

      {/* Right: Search, Theme Toggle, User Profile */}
      <div className="flex items-center gap-1.5 sm:gap-2.5">
        {/* Quick Search Button (Ctrl + K) */}
        <Button
          variant="outline"
          size="sm"
          onClick={onOpenCommand}
          className="h-9 items-center gap-2.5 rounded-lg border-border/70 bg-muted/20 px-3 text-sm font-normal text-muted-foreground hover:bg-muted/40 hover:text-foreground"
          aria-label="Mở tìm kiếm nhanh (Ctrl K)"
        >
          <Search className="size-4 shrink-0 text-muted-foreground/80" />
          <span className="hidden sm:inline font-normal text-foreground/80">Tìm kiếm...</span>
          <Kbd className="hidden sm:inline-flex">Ctrl K</Kbd>
        </Button>

        {/* Theme Toggle Button */}
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
          className="size-8.5 rounded-lg text-muted-foreground hover:text-foreground"
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
            <Button
              variant="ghost"
              size="sm"
              className="gap-2 px-1.5 h-9 hover:bg-muted rounded-lg"
            >
              <Avatar className="size-8">
                <AvatarFallback className="text-xs font-semibold text-primary bg-primary/10">
                  {avatarInitials}
                </AvatarFallback>
              </Avatar>
              <div className="hidden text-left sm:block">
                <p className="text-sm font-semibold leading-tight text-foreground truncate max-w-[140px]">
                  {displayName}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">{displayRole}</p>
              </div>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <p className="text-sm font-semibold text-foreground">{displayName}</p>
              <p className="text-xs text-muted-foreground font-normal truncate">{displayEmail}</p>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />

            {/* Dev Tools Section (Chỉ hiển thị khi chạy môi trường phát triển) */}
            {isDevMode && (
              <>
                <DropdownMenuLabel className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider py-1">
                  Công Cụ Lập Trình (Dev)
                </DropdownMenuLabel>
                <DropdownMenuItem asChild>
                  <a
                    href="http://localhost:8001/docs"
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center justify-between cursor-pointer text-xs"
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
                    className="flex items-center justify-between cursor-pointer text-xs"
                  >
                    <span>Qdrant Vector DB</span>
                    <ExternalLink className="size-3 text-muted-foreground" />
                  </a>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
              </>
            )}

            <DropdownMenuItem
              onClick={handleLogout}
              className="text-destructive cursor-pointer flex items-center justify-between text-xs"
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
