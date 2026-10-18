import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { CollectionDetailPage } from "@/features/knowledge/collection-detail-page";

const searchSchema = z.object({
  docId: z.string().optional(),
  tab: z
    .enum([
      "sources",
      "documents",
      "facts",
      "tasks",
      "glossary",
      "scores",
      "models",
    ])
    .optional()
    .catch(undefined),
});

export const Route = createFileRoute("/knowledge/$collectionId")({
  validateSearch: (search) => searchSchema.parse(search),
  component: CollectionDetailRoute,
});

function CollectionDetailRoute() {
  const { collectionId } = Route.useParams();
  const { tab } = Route.useSearch();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const effectiveTab = tab === "documents" ? "sources" : tab;
  return (
    <CollectionDetailPage
      collectionId={collectionId}
      initialTab={effectiveTab}
      onTabChange={(tab) => navigate({ search: { ...search, tab } })}
    />
  );
}
