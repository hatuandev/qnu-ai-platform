import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { ModelOpsPage } from "@/features/modelops/modelops-page";

const searchSchema = z.object({
  providerId: z.string().optional(),
});

export const Route = createFileRoute("/models")({
  validateSearch: (search) => searchSchema.parse(search),
  component: ModelsRoute,
});

function ModelsRoute() {
  const search = Route.useSearch();
  return (
    <ModelOpsPage
      currentPath={
        search.providerId ? `/models/${search.providerId}` : "/models"
      }
    />
  );
}
