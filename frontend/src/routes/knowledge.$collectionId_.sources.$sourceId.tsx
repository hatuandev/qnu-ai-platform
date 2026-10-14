import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { SourceDetailPage } from "@/features/knowledge/source-detail-page";

export const Route = createFileRoute(
  "/knowledge/$collectionId_/sources/$sourceId",
)({
  validateSearch: (search) =>
    z
      .object({
        view: z.enum(["studio"]).optional().catch(undefined),
        revision: z.string().trim().min(1).optional().catch(undefined),
        tab: z
          .enum(["content", "quality", "chunks", "revisions"])
          .optional()
          .catch(undefined),
      })
      .parse(search),
  component: SourceDetailRoute,
});

function SourceDetailRoute() {
  const { collectionId, sourceId } = Route.useParams() as {
    collectionId: string;
    sourceId: string;
  };
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  return (
    <SourceDetailPage
      collectionId={collectionId}
      sourceId={sourceId}
      isStudioMode={search.view === "studio"}
      key={`${collectionId}:${sourceId}`}
      revisionId={search.revision}
      activeTab={search.tab ?? "content"}
      onTabChange={(tab) => navigate({ search: { ...search, tab } })}
      onRevisionChange={(revision) =>
        navigate({ search: { ...search, revision }, replace: true })
      }
      onStudioModeChange={(isOpen) =>
        navigate({
          search: { ...search, view: isOpen ? "studio" : undefined },
          replace: true,
        })
      }
    />
  );
}
