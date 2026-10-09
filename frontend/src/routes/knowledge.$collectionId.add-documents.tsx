import { createFileRoute } from "@tanstack/react-router";
import { AddDocumentsPage } from "@/features/knowledge/add-documents-page";

export const Route = createFileRoute("/knowledge/$collectionId/add-documents")({
  component: AddDocumentsRoute,
});

function AddDocumentsRoute() {
  const { collectionId } = Route.useParams() as { collectionId: string };
  return <AddDocumentsPage collectionId={collectionId} />;
}
