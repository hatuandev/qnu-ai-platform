import { createFileRoute } from "@tanstack/react-router";
import { WorkspaceAuditPanel } from "@/features/workspaces/audit-panel";
import { pageSearchSchema } from "@/features/workspaces/search";

export const Route = createFileRoute("/workspaces/$workspaceId/audit")({
  validateSearch: (search) => pageSearchSchema.parse(search),
  component: AuditRoute,
});

function AuditRoute() {
  const { workspaceId } = Route.useParams();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();

  return (
    <WorkspaceAuditPanel
      workspaceId={workspaceId}
      page={search.page}
      pageSize={search.pageSize}
      onPageChange={(page) =>
        void navigate({ search: (previous) => ({ ...previous, page }) })
      }
      onPageSizeChange={(pageSize) =>
        void navigate({
          search: (previous) => ({ ...previous, pageSize, page: 1 }),
        })
      }
    />
  );
}
