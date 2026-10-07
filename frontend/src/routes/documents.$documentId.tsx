import { createFileRoute } from "@tanstack/react-router";
import { DocumentDetailPage } from "@/features/documents/document-detail-page";

export const Route = createFileRoute("/documents/$documentId")({
  component: DocumentDetailRoute,
});

function DocumentDetailRoute() {
  return <DocumentDetailPage />;
}
