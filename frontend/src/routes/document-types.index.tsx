import { createFileRoute } from "@tanstack/react-router";
import { DocumentTypesPage } from "@/features/document-types/document-types-page";

export const Route = createFileRoute("/document-types/")({
  component: DocumentTypesIndexRoute,
});

function DocumentTypesIndexRoute() {
  return <DocumentTypesPage />;
}
