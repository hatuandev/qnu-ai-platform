import { Moon, Search, Sun } from "lucide-react";
import { useAuth } from "@/app/auth";
import { useTheme } from "@/app/theme-provider";
import { AccountMenuContent } from "@/components/admin/account-menu";
import { NotificationsPopover } from "@/components/admin/notifications-popover";
import { QuickCreateMenu } from "@/components/admin/quick-create-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { usePlatformShortcut } from "@/hooks/use-platform-shortcut";
import { Breadcrumbs } from "@/layouts/breadcrumbs";

export function Topbar({ onOpenCommand }: { onOpenCommand: () => void }) {
  const { resolvedTheme, setTheme } = useTheme();
  const { user } = useAuth();
  const shortcut = usePlatformShortcut();
  const displayName = user?.name || "KTX";
  const initials = displayName
    .split(/\s+/)
    .filter((part: string) => Boolean(part))
    .map((part: string) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  const themeLabel =
    resolvedTheme === "dark"
      ? "Chuyển sang giao diện sáng"
      : "Chuyển sang giao diện tối";

  return (
    <header className="sticky top-0 z-30 flex h-[var(--topbar-height)] items-center gap-1.5 border-b bg-background/95 px-3 backdrop-blur sm:gap-3 sm:px-4 lg:px-5">
      <SidebarTrigger aria-label="Mở hoặc thu gọn thanh bên" />
      <Breadcrumbs />
      <div className="ml-auto flex items-center gap-1">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="outline"
              size="icon"
              className="size-8.5 rounded-lg border-border/70 text-muted-foreground hover:text-foreground lg:hidden"
              onClick={onOpenCommand}
              aria-label={`Tìm kiếm (${shortcut})`}
            >
              <Search className="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Tìm kiếm · {shortcut}</TooltipContent>
        </Tooltip>
        <Button
          variant="outline"
          size="sm"
          className="hidden h-8.5 items-center gap-2.5 rounded-lg border-border/70 bg-muted/20 px-3 text-xs font-normal text-muted-foreground hover:bg-muted/40 hover:text-foreground lg:flex"
          onClick={onOpenCommand}
        >
          <Search className="size-3.5 shrink-0 text-muted-foreground/80" />
          <span className="font-normal text-foreground/80">Tìm kiếm</span>
          <kbd className="pointer-events-none inline-flex h-5 select-none items-center justify-center rounded border border-border/80 bg-background px-1.5 font-mono text-[10px] font-medium leading-none text-muted-foreground shadow-2xs">
            {shortcut}
          </kbd>
        </Button>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={() =>
                setTheme(resolvedTheme === "dark" ? "light" : "dark")
              }
              aria-label={themeLabel}
            >
              {resolvedTheme === "dark" ? <Sun /> : <Moon />}
            </Button>
          </TooltipTrigger>
          <TooltipContent>{themeLabel}</TooltipContent>
        </Tooltip>
        <NotificationsPopover />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Mở menu tài khoản">
              <Avatar className="size-8">
                <AvatarFallback>{initials || "OR"}</AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <AccountMenuContent side="bottom" align="end" />
        </DropdownMenu>
        <QuickCreateMenu />
      </div>
    </header>
  );
}
