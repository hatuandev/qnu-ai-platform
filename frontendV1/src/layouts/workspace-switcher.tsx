import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import { Check, ChevronsUpDown, Plus, Sparkles } from "lucide-react";
import { useState } from "react";
import { isPlatformWorkspaceAdmin, useV1Auth } from "@/app/auth/v1";
import type { CallerWorkspaceRole } from "@/app/auth/v1/permissions";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  useCallerWorkspaceRole,
  useWorkspaceQuery,
  useWorkspacesQuery,
} from "@/features/workspaces/queries";
import { WorkspaceFormDialog } from "@/features/workspaces/workspace-form-dialog";
import { cn } from "@/lib/utils";
import { useFeatureScope } from "@/navigation/use-feature-scope";

function formatWorkspaceRole(role: CallerWorkspaceRole): string {
  if (role.kind === "platform-admin") return "Quản trị nền tảng";
  if (role.kind === "member") {
    switch (role.role) {
      case "admin":
        return "Quản trị viên";
      case "editor":
        return "Biên tập viên";
      case "reviewer":
        return "Kiểm duyệt viên";
      case "member":
        return "Thành viên";
      default:
        return role.role;
    }
  }
  if (role.kind === "unknown") return "Đang xác thực...";
  return "Chưa tham gia";
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

export function WorkspaceSwitcher({
  compact = false,
  variant = "topbar",
  onNavigate,
}: {
  compact?: boolean;
  variant?: "topbar" | "sidebar";
  onNavigate?: () => void;
}) {
  const { actor, isAuthenticated } = useV1Auth();
  const navigate = useNavigate();
  const location = useRouterState({ select: (s) => s.location });
  const { isMobile } = useSidebar();
  const scope = useFeatureScope();
  const [createOpen, setCreateOpen] = useState(false);

  // Queries
  const workspacesQuery = useWorkspacesQuery(
    { page: 1, pageSize: 50 },
    isAuthenticated,
  );
  const workspaces = workspacesQuery.data?.items ?? [];

  // Active workspace id from scope, URL or first available workspace
  const activeWorkspaceId = scope.workspaceId ?? workspaces[0]?.id ?? "";
  const activeWorkspaceQuery = useWorkspaceQuery(activeWorkspaceId);
  const activeWorkspace =
    workspaces.find((w) => w.id === activeWorkspaceId) ??
    activeWorkspaceQuery.data;

  // User role in the active workspace
  const { role, isPending: rolePending } =
    useCallerWorkspaceRole(activeWorkspaceId);
  const isPlatformAdmin = isPlatformWorkspaceAdmin(actor);

  const handleSelectWorkspace = (newWorkspaceId: string) => {
    scope.setWorkspaceId?.(newWorkspaceId);
    if (newWorkspaceId === activeWorkspaceId) return;

    onNavigate?.();

    if (location.pathname === "/dashboard") {
      void navigate({
        to: "/dashboard",
        search: { workspaceId: newWorkspaceId },
      });
      return;
    }

    if (
      location.pathname === "/settings" ||
      location.pathname.startsWith("/settings/") ||
      location.pathname === "/providers" ||
      location.pathname.startsWith("/modelops/")
    ) {
      return;
    }

    // Preserve the current sub-feature if possible (knowledge, assistants, members, etc.)
    const match =
      /^\/workspaces\/[^/]+(\/(?:knowledge|assistants|conversations|members|models|quota|operations|resources|audit))(?:\/.*)?$/.exec(
        location.pathname,
      );

    if (match) {
      const subFeature = match[1];
      void navigate({
        to: `/workspaces/${newWorkspaceId}${subFeature}` as "/",
        search: { page: 1, pageSize: 20 } as never,
      });
    } else {
      void navigate({
        to: "/workspaces/$workspaceId/knowledge",
        params: { workspaceId: newWorkspaceId },
        search: { page: 1, pageSize: 20 },
      });
    }
  };

  const currentName = activeWorkspace?.name || "Chọn đơn vị";
  const currentRoleLabel = rolePending
    ? "Đang tải vai trò..."
    : activeWorkspace
      ? formatWorkspaceRole(role)
      : "Chưa chọn đơn vị";
  const initials = activeWorkspace ? getInitials(activeWorkspace.name) : "ĐV";

  const triggerContent =
    variant === "topbar" ? (
      <button
        type="button"
        aria-label={`Đơn vị đang chọn: ${currentName}`}
        className="inline-flex h-8.5 max-w-[240px] items-center gap-2 rounded-lg border border-border/80 bg-muted/25 px-2.5 text-left text-xs transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:max-w-[280px]"
      >
        <span className="flex size-5 shrink-0 items-center justify-center rounded bg-primary text-[10px] font-bold uppercase tracking-tight text-primary-foreground">
          {activeWorkspace ? initials : <Sparkles className="size-3" />}
        </span>
        <span className="min-w-0 flex-1 truncate font-medium text-foreground">
          {currentName}
        </span>
        <span className="hidden truncate rounded bg-background/80 px-1.5 py-0.5 text-[10px] text-muted-foreground xl:inline-block">
          {currentRoleLabel}
        </span>
        <ChevronsUpDown className="size-3.5 shrink-0 text-muted-foreground" />
      </button>
    ) : (
      <SidebarMenuButton
        className={cn(
          "data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground h-12 w-full transition-colors",
          compact && "justify-center px-0",
        )}
      >
        <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-2xs font-bold text-xs uppercase tracking-tight">
          {activeWorkspace ? initials : <Sparkles className="size-4" />}
        </div>
        {!compact ? (
          <div className="grid flex-1 text-left text-sm leading-tight min-w-0">
            <span className="truncate font-semibold text-foreground">
              {currentName}
            </span>
            <span className="truncate text-xs text-muted-foreground">
              {currentRoleLabel}
            </span>
          </div>
        ) : null}
        {!compact ? (
          <ChevronsUpDown className="ml-auto size-4 shrink-0 text-muted-foreground" />
        ) : null}
      </SidebarMenuButton>
    );

  const dropdown = (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        {compact && variant === "sidebar" ? (
          <Tooltip>
            <TooltipTrigger asChild>{triggerContent}</TooltipTrigger>
            <TooltipContent side="right">
              {currentName} · {currentRoleLabel}
            </TooltipContent>
          </Tooltip>
        ) : (
          triggerContent
        )}
      </DropdownMenuTrigger>

      <DropdownMenuContent
        className="w-64 min-w-56 rounded-xl p-1.5 shadow-md"
        align="start"
        side={
          variant === "topbar"
            ? "bottom"
            : isMobile
              ? "bottom"
              : compact
                ? "right"
                : "bottom"
        }
        sideOffset={6}
      >
        <DropdownMenuLabel className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground px-2 py-1.5">
          Đơn vị làm việc
        </DropdownMenuLabel>

        <div className="max-h-64 overflow-y-auto space-y-0.5">
          {workspaces.map((ws, index) => {
            const isSelected = ws.id === activeWorkspaceId;
            const itemInitials = getInitials(ws.name);
            return (
              <DropdownMenuItem
                key={ws.id}
                onClick={() => handleSelectWorkspace(ws.id)}
                className={cn(
                  "flex items-center gap-2.5 p-2 rounded-lg cursor-pointer transition-colors",
                  isSelected && "bg-accent/60 font-medium",
                )}
              >
                <div
                  className={cn(
                    "flex size-7 shrink-0 items-center justify-center rounded-md font-bold text-[11px]",
                    isSelected
                      ? "bg-primary text-primary-foreground shadow-2xs"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  {itemInitials}
                </div>

                <div className="grid flex-1 text-left min-w-0">
                  <span className="truncate text-xs font-medium text-foreground">
                    {ws.name}
                  </span>
                  <span className="truncate text-[10px] text-muted-foreground">
                    {ws.code}
                  </span>
                </div>

                {isSelected ? (
                  <Check className="size-4 text-primary shrink-0 ml-auto" />
                ) : index < 9 ? (
                  <span className="text-[10px] font-mono text-muted-foreground/70 ml-auto">
                    ⌘{index + 1}
                  </span>
                ) : null}
              </DropdownMenuItem>
            );
          })}

          {workspaces.length === 0 && (
            <div className="px-2 py-3 text-center text-xs text-muted-foreground">
              Không có workspace nào
            </div>
          )}
        </div>

        {isPlatformAdmin ? (
          <>
            <DropdownMenuSeparator className="my-1" />
            <DropdownMenuItem asChild>
              <Link
                to="/workspaces"
                search={{ page: 1, pageSize: 20 }}
                onClick={onNavigate}
              >
                Quản lý workspace
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => setCreateOpen(true)}
              className="flex items-center gap-2 p-2 rounded-lg cursor-pointer text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
            >
              <div className="flex size-6 items-center justify-center rounded-md border border-dashed border-border bg-background">
                <Plus className="size-3.5 text-muted-foreground" />
              </div>
              <span className="text-xs font-medium">Thêm đơn vị mới</span>
            </DropdownMenuItem>
          </>
        ) : null}
      </DropdownMenuContent>
    </DropdownMenu>
  );

  return (
    <>
      {variant === "topbar" ? (
        dropdown
      ) : (
        <SidebarMenu>
          <SidebarMenuItem>{dropdown}</SidebarMenuItem>
        </SidebarMenu>
      )}

      <WorkspaceFormDialog open={createOpen} onOpenChange={setCreateOpen} />
    </>
  );
}
