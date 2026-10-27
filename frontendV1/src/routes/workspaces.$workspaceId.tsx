import { createFileRoute } from "@tanstack/react-router";
import { WorkspaceDetailLayout } from "@/features/workspaces/workspace-detail-layout";

export const Route = createFileRoute("/workspaces/$workspaceId")({
  component: () => (
    <WorkspaceDetailLayout workspaceId={Route.useParams().workspaceId} />
  ),
});
