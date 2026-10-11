import { createFileRoute } from "@tanstack/react-router";
import { SourceDetailPage } from "@/features/knowledge/source-detail-page";

export const Route = createFileRoute(
  "/knowledge/$collectionId_/sources/$sourceId",
)({
  validateSearch: (search: Record<string, unknown>) => ({
    view: search.view === "studio" ? ("studio" as const) : undefined,
    revision: typeof search.revision === "string" ? search.revision : undefined,
  }),
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
      onStudioModeChange={(isOpen) =>
        navigate({ search: { ...search, view: isOpen ? "studio" : undefined } })
      }
    />
  );
}
