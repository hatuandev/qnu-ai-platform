import { createFileRoute } from "@tanstack/react-router";
import { NodeCatalogPage } from "@/features/capabilities/nodes/node-catalog-page";

export const Route = createFileRoute("/capabilities/nodes/")({
  component: NodeCatalogRoute,
});

function NodeCatalogRoute() {
  return <NodeCatalogPage />;
}
