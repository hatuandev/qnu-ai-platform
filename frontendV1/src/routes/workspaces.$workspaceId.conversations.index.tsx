import { createFileRoute } from "@tanstack/react-router";
import { ConversationsPage } from "@/features/conversations/conversations-page";

export const Route = createFileRoute("/workspaces/$workspaceId/conversations/")(
  {
    component: ConversationsIndexRoute,
  },
);

function ConversationsIndexRoute() {
  const { workspaceId } = Route.useParams();
  return <ConversationsPage workspaceId={workspaceId} />;
}
