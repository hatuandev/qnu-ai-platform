import { createFileRoute } from "@tanstack/react-router";
import { Building2, FolderOpen, Library } from "lucide-react";
import { PageBreadcrumbs } from "@/components/admin/page-breadcrumbs";
import { IndexPanel } from "@/features/knowledge/index-panel";
import { canManageKnowledge } from "@/features/knowledge/permissions";
import { useCollectionQuery } from "@/features/knowledge/queries";
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";
import { pageSearchSchema } from "@/features/workspaces/search";
import { workspaceFeatureBreadcrumb } from "@/navigation/workspace-features";

export const Route = createFileRoute(
  "/workspaces/$workspaceId/collections/$collectionId/search",
)({
  validateSearch: (search) => pageSearchSchema.partial().parse(search),
  component: CollectionSearchRoute,
});

function CollectionSearchRoute() {
  const { workspaceId, collectionId } = Route.useParams();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();

  const { role, isPending: rolePending } = useCallerWorkspaceRole(workspaceId);
  const canManage = !rolePending && canManageKnowledge(role);
  const collectionQuery = useCollectionQuery(workspaceId, collectionId);
  const collection = collectionQuery.data;

  const page = search.page ?? 1;
  const pageSize = search.pageSize ?? 20;

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <PageBreadcrumbs
        items={[
          {
            label: "Workspace",
            to: "/workspaces/$workspaceId",
            params: { workspaceId },
            icon: Building2,
          },
          {
            label: "Kho tri thức",
            to: "/workspaces/$workspaceId/collections",
            params: { workspaceId },
            search: { page: 1, pageSize: 20 },
            icon: Library,
          },
          {
            label: collection?.name ?? "Kho tri thức",
            to: "/workspaces/$workspaceId/collections/$collectionId",
            params: { workspaceId, collectionId },
            search: { page: 1, pageSize: 20 },
            icon: FolderOpen,
            maxChars: 24,
          },
          {
            ...workspaceFeatureBreadcrumb("search", {
              workspaceId,
              collectionId,
            }),
            current: true,
          },
        ]}
      />

      <IndexPanel
        workspaceId={workspaceId}
        collectionId={collectionId}
        canManage={canManage}
        role={role}
        page={page}
        pageSize={pageSize}
        onPageChange={(newPage) => {
          void navigate({
            search: (prev) => ({ ...prev, page: newPage }),
            replace: true,
          });
        }}
        onPageSizeChange={(newPageSize) => {
          void navigate({
            search: (prev) => ({ ...prev, pageSize: newPageSize, page: 1 }),
            replace: true,
          });
        }}
      />
    </div>
  );
}
