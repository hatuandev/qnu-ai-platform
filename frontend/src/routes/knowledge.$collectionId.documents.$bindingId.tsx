import { createFileRoute } from "@tanstack/react-router";
import { BindingDetailPage } from "@/features/knowledge/binding-detail-page";

export const Route = createFileRoute(
  "/knowledge/$collectionId/documents/$bindingId",
)({
  component: BindingDetailRoute,
});

function BindingDetailRoute() {
  const { collectionId, bindingId } = Route.useParams() as {
    collectionId: string;
    bindingId: string;
  };
  return (
    <BindingDetailPage collectionId={collectionId} bindingId={bindingId} />
  );
}
