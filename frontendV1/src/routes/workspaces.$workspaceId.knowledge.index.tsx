import { createFileRoute } from "@tanstack/react-router";
import { CollectionsPanel } from "@/features/knowledge/collections-panel";
import { pageSearchSchema } from "@/features/workspaces/search";

export const Route = createFileRoute("/workspaces/$workspaceId/knowledge/")({
  validateSearch: (search) => pageSearchSchema.parse(search),
  component: KnowledgeListRoute,
});

function KnowledgeListRoute() {
  const { workspaceId } = Route.useParams();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();

  return (
    <CollectionsPanel
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

