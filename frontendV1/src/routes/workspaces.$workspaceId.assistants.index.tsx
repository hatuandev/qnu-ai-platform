import { createFileRoute } from "@tanstack/react-router";
import { AssistantsPanel } from "@/features/assistants/assistants-panel";
import { assistantListSearchSchema } from "@/features/assistants/schemas";

export const Route = createFileRoute("/workspaces/$workspaceId/assistants/")({
  validateSearch: (search) => assistantListSearchSchema.parse(search),
  component: AssistantsRoute,
});

function AssistantsRoute() {
  const { workspaceId } = Route.useParams();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();

  return (
    <AssistantsPanel
      workspaceId={workspaceId}
      limit={search.limit}
      offset={search.offset}
      onOffsetChange={(offset) =>
        void navigate({ search: (previous) => ({ ...previous, offset }) })
      }
    />
  );
}
