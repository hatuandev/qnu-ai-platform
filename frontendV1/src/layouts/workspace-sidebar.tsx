import { Link, useRouterState } from "@tanstack/react-router";
import { LayoutDashboard, Settings2 } from "lucide-react";
import { useV1Auth } from "@/app/auth/v1";
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import {
  isPrimarySidebarFeatureActive,
  isSettingsRouteActive,
  primaryWorkspaceFeatureKeys,
  workspaceFeatures,
} from "@/navigation/config";
import { useFeatureScope } from "@/navigation/use-feature-scope.tsx";
import { featureTarget } from "@/navigation/workspace-features";

export function WorkspaceSidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { isAuthenticated } = useV1Auth();
  const scope = useFeatureScope();
  const location = useRouterState({ select: (state) => state.location });
  if (!isAuthenticated) return null;

  const isDashboardActive = location.pathname === "/dashboard";
  const isSettingsActive = isSettingsRouteActive(
    location.pathname,
    location.search,
  );

  return (
    <SidebarGroup>
      <SidebarGroupLabel>Điều hướng</SidebarGroupLabel>
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton
            asChild
            tooltip="Tổng quan"
            isActive={isDashboardActive}
          >
            <Link
              to="/dashboard"
              search={{ workspaceId: scope.workspaceId }}
              onClick={onNavigate}
              aria-current={isDashboardActive ? "page" : undefined}
            >
              <LayoutDashboard className="size-4 shrink-0" />
              <span>Tổng quan</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>

        {primaryWorkspaceFeatureKeys.map((key) => {
          const { title, icon: Icon } = workspaceFeatures[key];
          const active = isPrimarySidebarFeatureActive(
            key,
            location.pathname,
            location.search,
          );
          return (
            <SidebarMenuItem key={key}>
              <SidebarMenuButton asChild tooltip={title} isActive={active}>
                <Link
                  {...featureTarget(key, scope)}
                  onClick={onNavigate}
                  aria-current={active ? "page" : undefined}
                >
                  <Icon className="size-4 shrink-0" />
                  <span>{title}</span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          );
        })}

        <SidebarMenuItem>
          <SidebarMenuButton
            asChild
            tooltip="Cấu hình"
            isActive={isSettingsActive}
          >
            <Link
              to="/settings"
              onClick={onNavigate}
              aria-current={isSettingsActive ? "page" : undefined}
            >
              <Settings2 className="size-4 shrink-0" />
              <span>Cấu hình</span>
            </Link>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarGroup>
  );
}
