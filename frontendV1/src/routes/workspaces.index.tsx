import { createFileRoute } from "@tanstack/react-router";
import { pageSearchSchema } from "@/features/workspaces/search";
import { WorkspacesPage } from "@/features/workspaces/workspaces-page";

export const Route = createFileRoute("/workspaces/")({
  validateSearch: (search) => pageSearchSchema.parse(search),
  component: WorkspacesIndex,
});

function WorkspacesIndex() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();

  return (
    <WorkspacesPage
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
      onOpenWorkspace={(workspace) =>
        void navigate({
          to: "/workspaces/$workspaceId",
          params: { workspaceId: workspace.id },
        })
      }
    />
  );
}
