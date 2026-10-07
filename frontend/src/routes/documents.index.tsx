import { createFileRoute } from "@tanstack/react-router";
import { DocumentsPage } from "@/features/documents/documents-page";

export const Route = createFileRoute("/documents/")({
  component: DocumentsIndexRoute,
});

function DocumentsIndexRoute() {
  return <DocumentsPage />;
}
