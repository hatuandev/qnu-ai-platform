import { createFileRoute } from "@tanstack/react-router";
import { OperationsPage } from "@/features/operations/operations-page";
import { operationsSearchSchema } from "@/features/operations/search";
export const Route = createFileRoute("/workspaces/$workspaceId/operations")({
  validateSearch: (search) => operationsSearchSchema.parse(search),
  component: OperationsRoute,
});
function OperationsRoute() {
  const { workspaceId } = Route.useParams();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  return (
    <OperationsPage
      workspaceId={workspaceId}
      search={search}
      onSearch={(patch) =>
        void navigate({ search: (previous) => ({ ...previous, ...patch }) })
      }
    />
  );
}
