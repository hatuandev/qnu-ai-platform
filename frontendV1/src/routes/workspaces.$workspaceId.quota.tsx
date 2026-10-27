import { createFileRoute } from "@tanstack/react-router";
import { WorkspaceQuotaPanel } from "@/features/workspaces/quota-panel";
import { pageSearchSchema } from "@/features/workspaces/search";

export const Route = createFileRoute("/workspaces/$workspaceId/quota")({
  validateSearch: (search) => pageSearchSchema.parse(search),
  component: QuotaRoute,
});

function QuotaRoute() {
  const { workspaceId } = Route.useParams();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();

  return (
    <WorkspaceQuotaPanel
      workspaceId={workspaceId}
      usagePage={search.page}
      usagePageSize={search.pageSize}
      onUsagePageChange={(page) =>
        void navigate({ search: (previous) => ({ ...previous, page }) })
      }
      onUsagePageSizeChange={(pageSize) =>
        void navigate({
          search: (previous) => ({ ...previous, pageSize, page: 1 }),
        })
      }
    />
  );
}
