import { createFileRoute } from "@tanstack/react-router";
import { MembersPanel } from "@/features/workspaces/members-panel";
import { pageSearchSchema } from "@/features/workspaces/search";

export const Route = createFileRoute("/workspaces/$workspaceId/members")({
  validateSearch: (search) => pageSearchSchema.parse(search),
  component: MembersRoute,
});

function MembersRoute() {
  const { workspaceId } = Route.useParams();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();

  return (
    <MembersPanel
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
