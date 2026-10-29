import { createFileRoute } from "@tanstack/react-router";
import { WorkspaceLinkBridge } from "@/features/workspaces/workspace-link-bridge";

export const Route = createFileRoute("/$workspaceCode/$")({
  validateSearch: (search: Record<string, unknown>) => search,
  component: WorkspaceLinkBridge,
});
