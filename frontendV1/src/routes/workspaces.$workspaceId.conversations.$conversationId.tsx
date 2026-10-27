import { createFileRoute } from "@tanstack/react-router";
import { ConversationsPage } from "@/features/conversations/conversations-page";

export const Route = createFileRoute(
  "/workspaces/$workspaceId/conversations/$conversationId",
)({
  component: ConversationDetailRoute,
});

function ConversationDetailRoute() {
  const { workspaceId, conversationId } = Route.useParams();
  return (
    <ConversationsPage
      workspaceId={workspaceId}
      conversationId={conversationId}
    />
  );
}
