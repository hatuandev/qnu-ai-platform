import { createFileRoute } from "@tanstack/react-router";
import { WorkspaceOverview } from "@/features/workspaces/workspace-overview";

export const Route = createFileRoute("/workspaces/$workspaceId/")({
  component: () => (
    <WorkspaceOverview workspaceId={Route.useParams().workspaceId} />
  ),
});
