import { createFileRoute, useLocation } from "@tanstack/react-router";
import { z } from "zod";
import { OcrReviewPage } from "@/features/knowledge/ocr-review-page";
import { preserveWorkspaceMask } from "@/navigation/workspace-links";

const ocrReviewSearchSchema = z.object({
  revisionId: z.string().optional(),
  runId: z.string().optional(),
  checkId: z.string().min(1).max(64).optional(),
  page: z.coerce.number().int().min(1).optional(),
  subTab: z.enum(["runs", "comparison", "review", "artifacts"]).optional(),
});

export const Route = createFileRoute(
  "/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId/ocr",
)({
  validateSearch: (search) => ocrReviewSearchSchema.parse(search),
  component: OcrReviewRoute,
});

function OcrReviewRoute() {
  const { workspaceId, collectionId, sourceId } = Route.useParams();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const maskedPath = useLocation({
    select: (location) => location.maskedLocation?.pathname,
  });

  return (
    <OcrReviewPage
      workspaceId={workspaceId}
      collectionId={collectionId}
      sourceId={sourceId}
      search={search}
      onSearchChange={(newParams) => {
        void navigate({
          search: (prev) => ({ ...prev, ...newParams }),
          replace: true,
          mask: preserveWorkspaceMask(maskedPath, { ...search, ...newParams }),
        });
      }}
    />
  );
}
