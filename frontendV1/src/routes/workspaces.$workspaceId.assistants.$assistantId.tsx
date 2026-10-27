import { createFileRoute } from "@tanstack/react-router";
import { AssistantDetailPage } from "@/features/assistants/assistant-detail-page";

export const Route = createFileRoute(
  "/workspaces/$workspaceId/assistants/$assistantId",
)({
  component: AssistantDetailRoute,
});

function AssistantDetailRoute() {
  const { workspaceId, assistantId } = Route.useParams();

  return (
    <AssistantDetailPage workspaceId={workspaceId} assistantId={assistantId} />
  );
}
