import { Link, useRouterState } from "@tanstack/react-router";
import { ArrowLeftRight } from "lucide-react";
import { useV1Auth } from "@/app/auth/v1";
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useCollectionQuery } from "@/features/knowledge/queries";
import { useWorkspaceQuery } from "@/features/workspaces/queries";
import {
  workspaceFeatureGroups,
  workspaceFeatureKeys,
  workspaceFeatures,
} from "@/navigation/config";
import { useFeatureScope } from "@/navigation/use-feature-scope.tsx";
import {
  type FeatureScope,
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
      <SidebarGroup>
        <SidebarGroupLabel>Đang làm việc</SidebarGroupLabel>
        <ScopeLabel scope={scope} onNavigate={onNavigate} />
      </SidebarGroup>
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

function ScopeLabel({
  scope,
  onNavigate,
}: {
  scope: FeatureScope;
  onNavigate?: () => void;
}) {
  const workspace = useWorkspaceQuery(scope.workspaceId ?? "");
  const collection = useCollectionQuery(
    scope.workspaceId ?? "",
    scope.collectionId ?? "",
  );
  return (
    <div className="space-y-1 px-2 text-xs text-muted-foreground group-data-[collapsible=icon]:sr-only">
      <p className="truncate" title={workspace.data?.name}>
        {scope.workspaceId
          ? (workspace.data?.name ?? "Workspace đã chọn")
          : "Chưa chọn workspace"}
      </p>
      {scope.collectionId && (
        <p className="truncate" title={collection.data?.name}>
          Kho: {collection.data?.name ?? "Đã chọn"}
        </p>
      )}
      <Link
        to="/workspaces/choose/$feature"
        params={{ feature: "collections" }}
        search={{ page: 1 }}
        onClick={onNavigate}
        className="flex items-center gap-1 text-primary hover:underline"
      >
        <ArrowLeftRight className="size-3" />
        {scope.workspaceId ? "Đổi workspace" : "Chọn workspace"}
      </Link>
      {scope.workspaceId && (
        <Link
          to="/workspaces/choose/$feature"
          params={{ feature: "ocr" }}
          search={{ workspaceId: scope.workspaceId, page: 1 }}
          onClick={onNavigate}
          className="flex items-center gap-1 text-primary hover:underline"
        >
          <ArrowLeftRight className="size-3" />
          {scope.collectionId ? "Đổi kho" : "Chọn kho tri thức"}
        </Link>
      )}
    </div>
  );
}
