import { createFileRoute } from "@tanstack/react-router";
import { DocumentTypeDetailPage } from "@/features/document-types/document-type-detail-page";

export const Route = createFileRoute("/document-types/$code")({
  component: DocumentTypeDetailRoute,
});

function DocumentTypeDetailRoute() {
  const { code } = Route.useParams();
  return <DocumentTypeDetailPage code={code} />;
}
