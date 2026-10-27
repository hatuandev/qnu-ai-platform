import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { EvaluationPage } from "@/features/evaluation/evaluation-page";

const searchSchema = z.object({
  page: z.coerce.number().int().min(1).catch(1),
  runId: z.string().min(1).max(64).optional(),
});
export const Route = createFileRoute(
  "/workspaces/$workspaceId/collections/$collectionId/evaluations",
)({
  validateSearch: (search) => searchSchema.parse(search),
  component: EvaluationRoute,
});
function EvaluationRoute() {
  const params = Route.useParams();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  return (
    <EvaluationPage
      {...params}
      {...search}
      onSearch={(patch) =>
        void navigate({ search: (previous) => ({ ...previous, ...patch }) })
      }
    />
  );
}
