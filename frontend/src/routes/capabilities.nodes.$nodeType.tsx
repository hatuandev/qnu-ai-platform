import { createFileRoute } from "@tanstack/react-router";
import { NodeDetailPage } from "@/features/capabilities/nodes/node-detail-page";

export const Route = createFileRoute("/capabilities/nodes/$nodeType")({
  component: NodeDetailRoute,
});

function NodeDetailRoute() {
  const { nodeType } = Route.useParams();
  return <NodeDetailPage nodeType={nodeType} />;
}
