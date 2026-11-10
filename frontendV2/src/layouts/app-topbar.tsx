import { Bell, Menu, Moon, Search, Sun, User } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { useUiStore } from "@/lib/ui-store";
import { AppBreadcrumb } from "./app-breadcrumb";
import { AppSidebar } from "./app-sidebar";

export function AppTopbar() {
  const [navigationOpen, setNavigationOpen] = useState(false);
  const { theme, setTheme, devActor } = useUiStore();

  return (
    <header className="flex h-14 items-center justify-between border-b border-border/60 bg-card px-4 gap-4">
      {/* Left: Dynamic Route Breadcrumb */}
      <div className="flex items-center gap-2 min-w-0">
        <Sheet open={navigationOpen} onOpenChange={setNavigationOpen}>
          <SheetTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden shrink-0"
              aria-label="Mở menu điều hướng"
            >
              <Menu className="size-4" />
            </Button>
          </SheetTrigger>
          <SheetContent className="p-0 md:hidden" side="left">
            <SheetHeader className="sr-only">
              <SheetTitle>Điều hướng</SheetTitle>
              <SheetDescription>
                Chọn chức năng trong hệ thống.
              </SheetDescription>
            </SheetHeader>
            <AppSidebar mobile onNavigate={() => setNavigationOpen(false)} />
          </SheetContent>
        </Sheet>
        <AppBreadcrumb />
      </div>

      {/* Center: Global Search Bar */}
      <div className="flex-1 max-w-md mx-auto hidden md:flex items-center">
        <div className="relative w-full">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Tìm kiếm tài liệu, mô hình, trợ lý... (Ctrl + K)"
            className="w-full h-8 rounded-md border border-border/60 bg-muted/30 pl-8 pr-3 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring focus:bg-background transition-colors"
          />
        </div>
      </div>

      {/* Right: Actions, Theme, User */}
      <div className="flex items-center gap-1.5 shrink-0">
        <Button
          variant="ghost"
          size="sm"
          className="size-8 p-0 text-muted-foreground hover:text-foreground"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          aria-label="Đổi giao diện Sáng / Tối"
        >
          {theme === "dark" ? (
            <Sun className="size-4" />
          ) : (
            <Moon className="size-4" />
          )}
        </Button>

        <Button
          variant="ghost"
          size="sm"
          className="size-8 p-0 text-muted-foreground hover:text-foreground"
          aria-label="Thông báo"
        >
          <Bell className="size-4" />
        </Button>

        {/* User Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="size-8 p-0 rounded-full hover:bg-muted"
            >
              <div className="size-7 rounded-full bg-primary/10 text-primary flex items-center justify-center font-medium text-xs">
                <User className="size-3.5" />
              </div>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-52">
            <div className="flex flex-col space-y-1 p-2">
              <p className="text-xs font-medium text-foreground leading-none">
                {devActor?.display_name || "Quản trị viên dev"}
              </p>
              <p className="text-[11px] text-muted-foreground leading-none font-mono">
                {devActor?.username || devActor?.email || "dev@qnu.edu.vn"}
              </p>
            </div>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-xs">
              Hồ sơ cá nhân
            </DropdownMenuItem>
            <DropdownMenuItem className="text-xs">
              Khóa API & Quyền
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-xs text-destructive">
              Đăng xuất
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
