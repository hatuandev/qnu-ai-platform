import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { CollectionDetailPage } from "@/features/knowledge/collection-detail-page";
import { pageSearchSchema } from "@/features/workspaces/search";

const collectionDetailSearchSchema = pageSearchSchema.extend({
  sourceAction: z.enum(["ocr"]).optional(),
  tab: z
    .enum(["sources", "compilations", "documents", "index"])
    .optional()
    .catch("sources"),
});

export const Route = createFileRoute(
  "/workspaces/$workspaceId/collections/$collectionId/",
)({
  validateSearch: (search) => collectionDetailSearchSchema.parse(search),
  component: CollectionDetailRoute,
});

function CollectionDetailRoute() {
  const { workspaceId, collectionId } = Route.useParams();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();

  return (
    <CollectionDetailPage
      workspaceId={workspaceId}
      collectionId={collectionId}
      page={search.page}
      pageSize={search.pageSize}
      tab={search.tab ?? "sources"}
      sourceAction={search.sourceAction}
      onPageChange={(page) =>
        void navigate({ search: (previous) => ({ ...previous, page }) })
      }
      onPageSizeChange={(pageSize) =>
        void navigate({
          search: (previous) => ({ ...previous, pageSize, page: 1 }),
        })
      }
      onTabChange={(tab) =>
        void navigate({ search: (previous) => ({ ...previous, tab, page: 1 }) })
      }
    />
  );
}
