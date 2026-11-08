import { Link, useRouterState } from "@tanstack/react-router";
import { LayoutDashboard, Settings2 } from "lucide-react";
import { isV1Route } from "@/app/api/v1/endpoints";
import { hasV1Permission, useV1Auth } from "@/app/auth/v1";
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";
import {
  activePrimaryWorkspaceFeature,
  isSettingsRouteActive,
  providerNavigation,
  workspaceFeatures,
  workspacePrimaryFeatures,
} from "@/navigation/config";
import { useFeatureScope } from "@/navigation/use-feature-scope.tsx";
import {
  featureTarget,
  isProviderRouteActive,
} from "@/navigation/workspace-features";

export function WorkspaceSidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { isAuthenticated, actor } = useV1Auth();
  const scope = useFeatureScope();
  const location = useRouterState({ select: (state) => state.location });
  const role = useCallerWorkspaceRole(
    isV1Route(location.pathname) ? (scope.workspaceId ?? "") : "",
  );
  if (!isAuthenticated) return null;

  const primaryFeatures = workspacePrimaryFeatures(
    role.isPending ? undefined : role.role,
  );
  const activePrimary = activePrimaryWorkspaceFeature(
    primaryFeatures,
    location.pathname,
    location.search,
  );
  const isDashboardActive = location.pathname === "/dashboard";
  const isProviderActive = isProviderRouteActive(location.pathname);
  const ProviderIcon = providerNavigation.icon;
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

        {primaryFeatures.map((key) => {
          const { title, icon: Icon } = workspaceFeatures[key];
          const active = activePrimary === key;
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

        {hasV1Permission(actor, providerNavigation.permission) ? (
          <SidebarMenuItem>
            <SidebarMenuButton
              asChild
              tooltip={providerNavigation.title}
              isActive={isProviderActive}
            >
              <Link
                to={providerNavigation.to}
                onClick={onNavigate}
                aria-current={isProviderActive ? "page" : undefined}
              >
                <ProviderIcon className="size-4 shrink-0" />
                <span>{providerNavigation.title}</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        ) : null}
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
