import { createFileRoute } from "@tanstack/react-router";
import { AnswersPage } from "@/features/knowledge/answers-page";
export const Route = createFileRoute(
  "/workspaces/$workspaceId/collections/$collectionId/answers",
)({ component: AnswersRoute });
function AnswersRoute() {
  const { workspaceId, collectionId } = Route.useParams();
  return <AnswersPage workspaceId={workspaceId} collectionId={collectionId} />;
}
