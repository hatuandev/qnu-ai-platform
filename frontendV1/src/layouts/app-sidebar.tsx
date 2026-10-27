import { Link, useRouterState } from "@tanstack/react-router";
import { ChevronDown, ChevronsUpDown, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { isV1Route } from "@/app/api/v1/endpoints";
import { useAuth } from "@/app/auth";
import { hasV1Permission, useV1Auth } from "@/app/auth/v1";
import { AccountMenuContent } from "@/components/admin/account-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { navigationGroups } from "@/navigation/config";
import type { NavItem } from "@/navigation/types";
import { filterNavigationGroups, isItemActive } from "@/navigation/utils";
import { useRbac } from "@/rbac/context";

function NavLeaf({
  item,
  pathname,
  onNavigate,
  child = false,
}: {
  item: NavItem;
  pathname: string;
  onNavigate?: () => void;
  child?: boolean;
}) {
  const { state, isMobile } = useSidebar();
  if (!item.to) return null;
  const active = pathname === item.to;
  const Icon = item.icon;
  const compact = state === "collapsed" && !isMobile;
  const content = (
    <Link to={item.to} onClick={onNavigate}>
      {Icon ? <Icon className="size-4 shrink-0" /> : null}
      <span className={cn("truncate", compact && "sr-only")}>{item.title}</span>
      {item.badge !== undefined && !compact ? (
        <Badge variant="secondary" className="ml-auto">
          {item.badge}
        </Badge>
      ) : null}
    </Link>
  );
  return (
    <SidebarMenuItem>
      {child ? (
        <SidebarMenuSubButton asChild isActive={active}>
          {content}
        </SidebarMenuSubButton>
      ) : (
        <SidebarMenuButton asChild tooltip={item.title} isActive={active}>
          {content}
        </SidebarMenuButton>
      )}
    </SidebarMenuItem>
  );
}

function CollapsedParent({
  item,
  pathname,
  onNavigate,
}: {
  item: NavItem;
  pathname: string;
  onNavigate?: () => void;
}) {
  const active = isItemActive(item, pathname);
  const Icon = item.icon;
  return (
    <SidebarMenuItem>
      <DropdownMenu>
        <Tooltip>
          <TooltipTrigger asChild>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                aria-label={item.title}
                className={cn(
                  "relative flex h-[var(--sidebar-item-height)] w-full items-center justify-center gap-2 rounded-md px-2.5 text-left text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
                  active && "bg-accent font-semibold text-accent-foreground",
                )}
              >
                {Icon ? <Icon className="size-4 shrink-0" /> : null}
              </button>
            </DropdownMenuTrigger>
          </TooltipTrigger>
          <TooltipContent side="right">{item.title}</TooltipContent>
        </Tooltip>
        <DropdownMenuContent side="right" align="start" className="w-48">
          <DropdownMenuLabel>{item.title}</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {item.children?.map((child) =>
            child.to ? (
              <DropdownMenuItem key={child.id} asChild>
                <Link to={child.to} onClick={onNavigate}>
                  {child.title}
                </Link>
              </DropdownMenuItem>
            ) : null,
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    </SidebarMenuItem>
  );
}

function NavParent({
  item,
  pathname,
  onNavigate,
}: {
  item: NavItem;
  pathname: string;
  onNavigate?: () => void;
}) {
  const { state, isMobile } = useSidebar();
  const active = isItemActive(item, pathname);
  const [open, setOpen] = useState(active);
  useEffect(() => {
    if (active) setOpen(true);
  }, [active]);
  const Icon = item.icon;
  if (state === "collapsed" && !isMobile)
    return (
      <CollapsedParent
        item={item}
        pathname={pathname}
        onNavigate={onNavigate}
      />
    );
  return (
    <SidebarMenuItem>
      <Collapsible open={open} onOpenChange={setOpen} className="space-y-0.5">
        <CollapsibleTrigger asChild>
          <button
            type="button"
            className={cn(
              "relative flex h-[var(--sidebar-item-height)] w-full items-center gap-2.5 rounded-md px-2.5 text-left text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
              active && "font-semibold text-foreground",
              active &&
                "before:absolute before:inset-y-2 before:-left-[9px] before:w-0.5 before:rounded-full before:bg-primary",
            )}
            aria-expanded={open}
          >
            {Icon ? <Icon className="size-4 shrink-0" /> : null}
            <span className="truncate">{item.title}</span>
            {item.badge !== undefined ? (
              <Badge variant="secondary" className="ml-auto">
                {item.badge}
              </Badge>
            ) : null}
            <ChevronDown
              className={cn(
                "size-4 shrink-0 transition-transform duration-[var(--motion-base)] ease-out",
                item.badge === undefined && "ml-auto",
                open && "rotate-180",
              )}
            />
          </button>
        </CollapsibleTrigger>
        <CollapsibleContent className="overflow-hidden transition-opacity duration-[var(--motion-base)] ease-out data-[state=open]:animate-collapsible-down data-[state=open]:opacity-100 data-[state=closed]:animate-collapsible-up data-[state=closed]:opacity-0">
          <SidebarMenuSub>
            {item.children?.map((child) => (
              <NavLeaf
                key={child.id}
                item={child}
                pathname={pathname}
                onNavigate={onNavigate}
                child
              />
            ))}
          </SidebarMenuSub>
        </CollapsibleContent>
      </Collapsible>
    </SidebarMenuItem>
  );
}

function SidebarHeaderBrand({
  compact,
  onNavigate,
  isQnuV1,
}: {
  compact: boolean;
  onNavigate?: () => void;
  isQnuV1?: boolean;
}) {
  const title = isQnuV1 ? "QNU AI Platform" : "Quản Lý Ký Túc Xá";
  const subtitle = isQnuV1 ? "v1alpha1 · backendV1" : "Dormitory Management";
  const content = (
    <Link
      to="/"
      onClick={onNavigate}
      className={cn(
        "flex h-[52px] w-full items-center gap-3 rounded-lg px-2 text-sidebar-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
        compact && "justify-center px-0",
      )}
    >
      <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
        <Sparkles className="size-4" />
      </div>
      {!compact ? (
        <div className="min-w-0 flex-1 text-left">
          <div className="truncate text-sm font-semibold tracking-tight">
            {title}
          </div>
          <div className="truncate text-xs text-muted-foreground">
            {subtitle}
          </div>
        </div>
      ) : null}
    </Link>
  );

  return (
    <SidebarHeader className={cn("px-3", compact && "justify-center px-0")}>
      {compact ? (
        <Tooltip>
          <TooltipTrigger asChild>{content}</TooltipTrigger>
          <TooltipContent side="right">
            {title} · {subtitle}
          </TooltipContent>
        </Tooltip>
      ) : (
        content
      )}
    </SidebarHeader>
  );
}

function AccountMenu({
  compact,
  onNavigate,
}: {
  compact: boolean;
  onNavigate?: () => void;
}) {
  const { user } = useAuth();
  const v1 = useV1Auth();
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  });
  // On v1 routes the footer must show the real backendV1 actor, not the demo user.
  const isQnuV1 = isV1Route(pathname);
  const displayName = isQnuV1
    ? (v1.actor?.display_name ?? "Chưa đăng nhập v1")
    : user?.name || "Người dùng";
  const displayEmail = isQnuV1
    ? (v1.actor?.email ?? v1.actor?.actor_id ?? "Phiên v1 chưa xác thực")
    : user?.email || "";
  const initials = displayName
    .split(/\s+/)
    .filter((part: string) => Boolean(part))
    .map((part: string) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  const trigger = (
    <DropdownMenuTrigger asChild>
      <SidebarMenuButton
        asChild
        className={cn("h-12", compact && "justify-center px-2")}
      >
        <button type="button" aria-label="Mở menu tài khoản">
          <Avatar className="size-8 shrink-0">
            <AvatarFallback>{initials || "ND"}</AvatarFallback>
          </Avatar>
          {!compact ? (
            <div className="min-w-0 flex-1 text-left">
              <div className="truncate text-sm font-semibold">
                {displayName}
              </div>
              <div className="truncate text-xs text-muted-foreground">
                {displayEmail}
              </div>
            </div>
          ) : null}
          {!compact ? (
            <ChevronsUpDown className="ml-auto size-4 shrink-0 text-muted-foreground" />
          ) : null}
        </button>
      </SidebarMenuButton>
    </DropdownMenuTrigger>
  );
  return (
    <DropdownMenu>
      {compact ? (
        <Tooltip>
          <TooltipTrigger asChild>{trigger}</TooltipTrigger>
          <TooltipContent side="right">{displayName}</TooltipContent>
        </Tooltip>
      ) : (
        trigger
      )}
      <AccountMenuContent
        side={compact ? "right" : "top"}
        align="start"
        onNavigate={onNavigate}
      />
    </DropdownMenu>
  );
}

function SidebarBody({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  });
  const { can, isAccessVerified } = useRbac();
  const { user } = useAuth();
  const v1 = useV1Auth();
  const { state, isMobile, setOpenMobile } = useSidebar();
  const compact = state === "collapsed" && !isMobile;
  const handleNavigate = isMobile ? () => setOpenMobile(false) : onNavigate;
  const canV1 = (permission?: string) =>
    v1.isAuthenticated && hasV1Permission(v1.actor, permission);
  const groups = filterNavigationGroups(
    navigationGroups,
    isAccessVerified ? can : (permission) => permission === undefined,
    user?.userType,
    canV1,
  );
  return (
    <>
      <SidebarHeaderBrand
        compact={compact}
        onNavigate={handleNavigate}
        isQnuV1={isV1Route(pathname)}
      />
      <SidebarContent>
        {groups.map((group) => (
          <SidebarGroup key={group.id}>
            <SidebarGroupLabel className="flex items-center gap-1.5">
              <span className="truncate">{group.label}</span>
              {group.template ? (
                <Badge
                  variant="secondary"
                  className="h-4 px-1.5 text-[10px] font-medium leading-none text-muted-foreground"
                >
                  Mẫu
                </Badge>
              ) : null}
            </SidebarGroupLabel>
            <SidebarMenu>
              {group.items.map((item) =>
                item.children ? (
                  <NavParent
                    key={item.id}
                    item={item}
                    pathname={pathname}
                    onNavigate={handleNavigate}
                  />
                ) : (
                  <NavLeaf
                    key={item.id}
                    item={item}
                    pathname={pathname}
                    onNavigate={handleNavigate}
                  />
                ),
              )}
            </SidebarMenu>
          </SidebarGroup>
        ))}
      </SidebarContent>
      <SidebarFooter className={cn("px-3", compact && "px-0")}>
        <AccountMenu compact={compact} onNavigate={handleNavigate} />
      </SidebarFooter>
    </>
  );
}

export function AppSidebar() {
  return (
    <Sidebar>
      <SidebarBody />
      <SidebarRail />
    </Sidebar>
  );
}
