import { createFileRoute } from "@tanstack/react-router";
import { WorkspaceModelsPanel } from "@/features/workspaces/models-panel";

export const Route = createFileRoute("/workspaces/$workspaceId/models")({
  component: () => (
    <WorkspaceModelsPanel workspaceId={Route.useParams().workspaceId} />
  ),
});
