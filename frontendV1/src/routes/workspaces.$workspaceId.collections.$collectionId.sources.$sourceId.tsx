import { createFileRoute, useLocation } from "@tanstack/react-router";
import { z } from "zod";
import { SourceDetailPage } from "@/features/knowledge/source-detail-page";
import { preserveWorkspaceMask } from "@/navigation/workspace-links";

const sourceDetailSearchSchema = z.object({
  revisionId: z.string().optional(),
  runId: z.string().optional(),
  checkId: z.string().min(1).max(64).optional(),
  page: z.coerce.number().int().min(1).optional(),
  tab: z.enum(["preview", "ocr"]).optional(),
  subTab: z.enum(["runs", "comparison", "review", "artifacts"]).optional(),
});

export const Route = createFileRoute(
  "/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId",
)({
  validateSearch: (search) => sourceDetailSearchSchema.parse(search),
  component: SourceDetailRoute,
});

function SourceDetailRoute() {
  const { workspaceId, collectionId, sourceId } = Route.useParams();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const maskedPath = useLocation({
    select: (location) => location.maskedLocation?.pathname,
  });

  return (
    <SourceDetailPage
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
