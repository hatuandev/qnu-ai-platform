import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { CollectionDetailPage } from "@/features/knowledge/collection-detail-page";

const searchSchema = z.object({
  docId: z.string().optional(),
});

export const Route = createFileRoute("/knowledge/$collectionId")({
  validateSearch: (search) => searchSchema.parse(search),
  component: CollectionDetailRoute,
});

function CollectionDetailRoute() {
  const { collectionId } = Route.useParams();
  const { docId } = Route.useSearch();
  return (
    <CollectionDetailPage collectionId={collectionId} initialDocId={docId} />
  );
}
