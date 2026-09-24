import { createFileRoute } from "@tanstack/react-router";
import { CollectionDetailPage } from "@/features/knowledge/collection-detail-page";

export const Route = createFileRoute("/knowledge/$collectionId")({
  component: CollectionDetailRoute,
});

function CollectionDetailRoute() {
  const { collectionId } = Route.useParams();
  return <CollectionDetailPage collectionId={collectionId} />;
}
