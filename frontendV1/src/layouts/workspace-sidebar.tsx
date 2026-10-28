import { Link, useRouterState } from "@tanstack/react-router";
import { useV1Auth } from "@/app/auth/v1";
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import {
  workspaceFeatureGroups,
  workspaceFeatureKeys,
  workspaceFeatures,
} from "@/navigation/config";
import { useFeatureScope } from "@/navigation/use-feature-scope.tsx";
import {
  featureTarget,
  isFeatureActive,
} from "@/navigation/workspace-features";

export function WorkspaceSidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { isAuthenticated } = useV1Auth();
  const scope = useFeatureScope();
  const location = useRouterState({ select: (state) => state.location });
  if (!isAuthenticated) return null;
  return (
    <>
      {workspaceFeatureGroups.map((group) => (
        <SidebarGroup key={group}>
          <SidebarGroupLabel>{group}</SidebarGroupLabel>
          <SidebarMenu>
            {workspaceFeatureKeys
              .filter((key) => workspaceFeatures[key].group === group)
              .map((key) => {
                const { title, icon: Icon } = workspaceFeatures[key];
                const active = isFeatureActive(
                  key,
                  location.pathname,
                  location.search,
                );
                return (
                  <SidebarMenuItem key={key}>
                    <SidebarMenuButton
                      asChild
                      tooltip={title}
                      isActive={active}
                    >
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
          </SidebarMenu>
        </SidebarGroup>
      ))}
    </>
  );
}
