import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { CollectionDetailPage } from "@/features/knowledge/collection-detail-page";

const searchSchema = z.object({
  docId: z.string().optional(),
  tab: z.enum(["sources", "documents", "facts", "tasks", "models"]).optional(),
});

export const Route = createFileRoute("/knowledge/$collectionId")({
  validateSearch: (search) => searchSchema.parse(search),
  component: CollectionDetailRoute,
});

function CollectionDetailRoute() {
  const { collectionId } = Route.useParams();
  const { tab } = Route.useSearch();
  const effectiveTab = tab === "documents" ? "sources" : tab;
  return (
    <CollectionDetailPage
      collectionId={collectionId}
      initialTab={effectiveTab}
    />
  );
}
