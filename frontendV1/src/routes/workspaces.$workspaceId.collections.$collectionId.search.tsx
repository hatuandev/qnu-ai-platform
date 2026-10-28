import { createFileRoute, Link } from "@tanstack/react-router";
import { ChevronRight } from "lucide-react";
import { IndexPanel } from "@/features/knowledge/index-panel";
import { canManageKnowledge } from "@/features/knowledge/permissions";
import { useCollectionQuery } from "@/features/knowledge/queries";
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";
import { pageSearchSchema } from "@/features/workspaces/search";

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
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground flex-wrap">
        <Link
          to="/workspaces/$workspaceId"
          params={{ workspaceId }}
          className="hover:text-foreground transition-colors"
        >
          Workspace
        </Link>
        <ChevronRight className="size-3 text-muted-foreground/60" />
        <Link
          to="/workspaces/$workspaceId/collections"
          params={{ workspaceId }}
          search={{ page: 1, pageSize: 20 }}
          className="hover:text-foreground transition-colors"
        >
          Kho tri thức
        </Link>
        <ChevronRight className="size-3 text-muted-foreground/60" />
        <Link
          to="/workspaces/$workspaceId/collections/$collectionId"
          params={{ workspaceId, collectionId }}
          search={{ page: 1, pageSize: 20 }}
          className="hover:text-foreground transition-colors truncate max-w-[180px]"
        >
          {collection?.name ?? "Kho tri thức"}
        </Link>
        <ChevronRight className="size-3 text-muted-foreground/60" />
        <span className="font-semibold text-foreground">Tìm kiếm & Chỉ mục</span>
      </div>

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

