import { Link, useLocation } from "@tanstack/react-router";
import {
  BookOpen,
  Bot,
  ChevronLeft,
  ChevronRight,
  Cpu,
  Inbox,
  LayoutDashboard,
  MessagesSquare,
  Settings,
  Workflow,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useUiStore } from "@/lib/ui-store";
import { cn } from "@/lib/utils";
import { WorkspaceSwitcher } from "./workspace-switcher";

export type NavItem = {
  title: string;
  href: string;
  icon: typeof LayoutDashboard;
  badge?: string | number;
  badgeVariant?: "default" | "secondary" | "destructive" | "outline";
};

export type NavSection = {
  heading?: string;
  items: NavItem[];
};

const navigationSections: NavSection[] = [
  {
    items: [
      {
        title: "Tổng quan",
        href: "/",
        icon: LayoutDashboard,
      },
    ],
  },
  {
    heading: "Tri thức & Nội dung",
    items: [
      {
        title: "Kho tri thức",
        href: "/knowledge",
        icon: BookOpen,
      },
      {
        title: "Hộp thư duyệt",
        href: "/inbox",
        icon: Inbox,
        badge: 2,
        badgeVariant: "default",
      },
    ],
  },
  {
    heading: "Trợ lý & Tương tác",
    items: [
      {
        title: "Trợ lý AI",
        href: "/assistants",
        icon: Bot,
      },
      {
        title: "Hội thoại",
        href: "/chat",
        icon: MessagesSquare,
      },
    ],
  },
  {
    heading: "Hệ thống",
    items: [
      {
        title: "Tác vụ",
        href: "/operations",
        icon: Workflow,
      },
      {
        title: "Mô hình AI",
        href: "/modelops",
        icon: Cpu,
      },
      {
        title: "Cài đặt",
        href: "/settings",
        icon: Settings,
      },
    ],
  },
];

export function AppSidebar() {
  const { pathname } = useLocation();
  const { sidebarCollapsed, toggleSidebar } = useUiStore();

  return (
    <aside
      className={cn(
        "relative flex flex-col border-r border-border/60 bg-card transition-all duration-200 select-none",
        sidebarCollapsed ? "w-16" : "w-64",
      )}
    >
      {/* Sidebar Header: Workspace Switcher */}
      <div className="flex h-14 items-center border-b border-border/60 px-2.5">
        <WorkspaceSwitcher collapsed={sidebarCollapsed} />
      </div>

      {/* Navigation Links */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
        {navigationSections.map((section, idx) => (
          <div key={section.heading || idx} className="space-y-1">
            {section.heading && !sidebarCollapsed && (
              <div className="px-2 py-1 text-[11px] font-medium tracking-wider uppercase text-muted-foreground/80">
                {section.heading}
              </div>
            )}
            <nav className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive =
                  item.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.href);

                return (
                  <Link
                    key={item.href}
                    to={item.href}
                    title={sidebarCollapsed ? item.title : undefined}
                    className={cn(
                      "group flex items-center gap-3 rounded-md px-2.5 py-2 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-primary/10 text-primary font-semibold"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground",
                      sidebarCollapsed && "justify-center px-0",
                    )}
                  >
                    <Icon
                      className={cn(
                        "size-4 shrink-0 transition-colors",
                        isActive
                          ? "text-primary"
                          : "text-muted-foreground group-hover:text-foreground",
                      )}
                      strokeWidth={1.75}
                    />
                    {!sidebarCollapsed && (
                      <span className="truncate flex-1">{item.title}</span>
                    )}
                    {!sidebarCollapsed && item.badge && (
                      <Badge
                        variant={item.badgeVariant || "secondary"}
                        className="ml-auto text-[10px] h-4 px-1.5"
                      >
                        {item.badge}
                      </Badge>
                    )}
                  </Link>
                );
              })}
            </nav>
          </div>
        ))}
      </div>

      {/* Sidebar Footer with Collapse Toggle */}
      <div className="border-t border-border/60 p-3 flex items-center justify-between">
        {!sidebarCollapsed && (
          <div className="flex items-center gap-2 overflow-hidden px-1">
            <div className="size-7 rounded-full bg-primary/15 text-primary flex items-center justify-center text-xs font-semibold">
              QN
            </div>
            <div className="flex flex-col min-w-0">
              <span className="truncate text-xs font-medium text-foreground">
                Quản trị viên
              </span>
              <span className="truncate text-[10px] text-muted-foreground">
                dev@qnu.edu.vn
              </span>
            </div>
          </div>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleSidebar}
          className={cn(
            "size-8 p-0 text-muted-foreground hover:text-foreground",
            sidebarCollapsed && "mx-auto",
          )}
          aria-label={
            sidebarCollapsed ? "Mở rộng thanh bên" : "Thu gọn thanh bên"
          }
        >
          {sidebarCollapsed ? (
            <ChevronRight className="size-4" />
          ) : (
            <ChevronLeft className="size-4" />
          )}
        </Button>
      </div>
    </aside>
  );
}
