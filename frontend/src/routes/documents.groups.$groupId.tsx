import { createFileRoute } from "@tanstack/react-router";
import { DocumentGroupDetailPage } from "@/features/documents/document-group-detail-page";

export const Route = createFileRoute("/documents/groups/$groupId")({
  component: DocumentGroupDetailRoute,
});

function DocumentGroupDetailRoute() {
  const { groupId } = Route.useParams();
  return <DocumentGroupDetailPage groupId={groupId} />;
}
