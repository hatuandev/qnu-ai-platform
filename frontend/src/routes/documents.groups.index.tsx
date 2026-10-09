import { createFileRoute } from "@tanstack/react-router";
import { DocumentGroupsPage } from "@/features/documents/document-groups-page";

export const Route = createFileRoute("/documents/groups/")({
  component: DocumentGroupsRoute,
});

function DocumentGroupsRoute() {
  return <DocumentGroupsPage />;
}
