import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { CompilationDetailPage } from "@/features/knowledge/compilation-detail-page";
import { pageSearchSchema } from "@/features/workspaces/search";

const compilationDetailSearchSchema = z.object({
  tab: z.enum(["draft", "review", "edit"]).optional(),
  reviewPage: pageSearchSchema.shape.page.optional(),
  reviewPageSize: pageSearchSchema.shape.pageSize.optional(),
  reviewId: z.string().min(1).max(64).optional(),
});

export const Route = createFileRoute(
  "/workspaces/$workspaceId/collections/$collectionId/compilations/$runId",
)({
  validateSearch: (search) => compilationDetailSearchSchema.parse(search),
  component: CompilationDetailRoute,
});

function CompilationDetailRoute() {
  const { workspaceId, collectionId, runId } = Route.useParams();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();

  return (
    <CompilationDetailPage
      workspaceId={workspaceId}
      collectionId={collectionId}
      runId={runId}
      initialTab={search.tab}
      reviewPage={search.reviewPage ?? 1}
      reviewPageSize={search.reviewPageSize ?? 20}
      reviewId={search.reviewId}
      onReviewSearch={(patch) =>
        void navigate({ search: (old) => ({ ...old, ...patch }) })
      }
    />
  );
}
