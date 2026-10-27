import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { CompiledDocumentDetailPage } from "@/features/knowledge/compiled-document-detail-page";
import { pageSearchSchema } from "@/features/workspaces/search";

export const Route = createFileRoute(
  "/workspaces/$workspaceId/collections/$collectionId/documents/$documentId/",
)({
  validateSearch: (search) =>
    pageSearchSchema
      .partial()
      .extend({ tab: z.enum(["versions", "history"]).optional() })
      .parse(search),
  component: CompiledDocumentDetailRoute,
});

function CompiledDocumentDetailRoute() {
  const { workspaceId, collectionId, documentId } = Route.useParams();

  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  return (
    <CompiledDocumentDetailPage
      page={search.page ?? 1}
      pageSize={search.pageSize ?? 20}
      initialTab={search.tab}
      onSearchChange={(patch) =>
        void navigate({ search: (old) => ({ ...old, ...patch }) })
      }
      workspaceId={workspaceId}
      collectionId={collectionId}
      documentId={documentId}
    />
  );
}
