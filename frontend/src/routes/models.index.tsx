import { createFileRoute } from "@tanstack/react-router";
import { ModelOpsPage } from "@/features/modelops/modelops-page";

export const Route = createFileRoute("/models/")({
  component: ModelsIndexRoute,
});

function ModelsIndexRoute() {
  return <ModelOpsPage />;
}
