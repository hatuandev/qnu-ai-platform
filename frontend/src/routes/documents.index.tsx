import { createFileRoute } from "@tanstack/react-router";
import { DocumentGroupsPage } from "@/features/documents/document-groups-page";

export const Route = createFileRoute("/documents/")({
  component: DocumentsIndexRoute,
});

function DocumentsIndexRoute() {
  return <DocumentGroupsPage />;
}
