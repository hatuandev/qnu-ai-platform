import { createFileRoute } from "@tanstack/react-router";
import { CompiledVersionDetailPage } from "@/features/knowledge/compiled-version-detail-page";

export const Route = createFileRoute(
  "/workspaces/$workspaceId/collections/$collectionId/documents/$documentId/versions/$versionId",
)({
  component: CompiledVersionDetailRoute,
});

function CompiledVersionDetailRoute() {
  const { workspaceId, collectionId, documentId, versionId } =
    Route.useParams();

  return (
    <CompiledVersionDetailPage
      workspaceId={workspaceId}
      collectionId={collectionId}
      documentId={documentId}
      versionId={versionId}
    />
  );
}
