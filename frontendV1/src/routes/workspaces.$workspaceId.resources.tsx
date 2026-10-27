import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { ResourcesPage } from "@/features/lifecycle/resources-page";

const schema = z.object({
  page: z.coerce.number().int().min(1).max(100000).default(1),
  actionId: z.string().min(1).max(64).optional(),
});
export const Route = createFileRoute("/workspaces/$workspaceId/resources")({
  validateSearch: (search) => schema.parse(search),
  component: ResourcesRoute,
});
function ResourcesRoute() {
  const { workspaceId } = Route.useParams();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  return (
    <ResourcesPage
      workspaceId={workspaceId}
      page={search.page}
      actionId={search.actionId}
      onPageChange={(page) =>
        void navigate({ search: (previous) => ({ ...previous, page }) })
      }
    />
  );
}
