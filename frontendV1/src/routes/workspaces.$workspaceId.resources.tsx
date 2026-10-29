import { createFileRoute, Navigate } from "@tanstack/react-router";
import { z } from "zod";

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
  return (
    <Navigate
      to="/workspaces/$workspaceId/operations"
      params={{ workspaceId }}
      search={{ page: 1, pageSize: 20, lifecycleActionId: search.actionId }}
      replace
    />
  );
}
