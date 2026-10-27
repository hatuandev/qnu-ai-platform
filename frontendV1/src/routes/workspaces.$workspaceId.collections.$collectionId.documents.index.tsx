import { createFileRoute, Link } from "@tanstack/react-router";
import { ChevronRight } from "lucide-react";
import { CompiledDocumentsList } from "@/features/knowledge/compiled-documents-list";
import { canRegisterCompiledDocument } from "@/features/knowledge/permissions";
import { useCollectionQuery } from "@/features/knowledge/queries";
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";
import { pageSearchSchema } from "@/features/workspaces/search";

export const Route = createFileRoute(
  "/workspaces/$workspaceId/collections/$collectionId/documents/",
)({
  validateSearch: (search) => pageSearchSchema.partial().parse(search),
  component: CompiledDocumentsListRoute,
});

function CompiledDocumentsListRoute() {
  const { workspaceId, collectionId } = Route.useParams();
  const navigate = Route.useNavigate();
  const search = Route.useSearch();

  const { role, isPending: rolePending } = useCallerWorkspaceRole(workspaceId);
  const canRegister = !rolePending && canRegisterCompiledDocument(role);

  const collectionQuery = useCollectionQuery(workspaceId, collectionId);
  const collection = collectionQuery.data;

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground flex-wrap">
        <Link
          to="/workspaces/$workspaceId"
          params={{ workspaceId }}
          className="hover:text-foreground transition-colors"
        >
          Workspace
        </Link>
        <ChevronRight className="size-3 text-muted-foreground/60" />
        <Link
          to="/workspaces/$workspaceId/collections"
          params={{ workspaceId }}
          search={{ page: 1, pageSize: 20 }}
          className="hover:text-foreground transition-colors"
        >
          Kho tri thức
        </Link>
        <ChevronRight className="size-3 text-muted-foreground/60" />
        <Link
          to="/workspaces/$workspaceId/collections/$collectionId"
          params={{ workspaceId, collectionId }}
          search={{ page: 1, pageSize: 20, tab: "documents" }}
          className="hover:text-foreground transition-colors truncate max-w-[150px]"
        >
          {collection?.name ?? "Kho tri thức"}
        </Link>
        <ChevronRight className="size-3 text-muted-foreground/60" />
        <span className="font-medium text-foreground">Tài liệu biên soạn</span>
      </div>

      <CompiledDocumentsList
        page={search.page ?? 1}
        pageSize={search.pageSize ?? 20}
        onPageChange={(page) =>
          void navigate({ search: (old) => ({ ...old, page }) })
        }
        onPageSizeChange={(pageSize) =>
          void navigate({ search: (old) => ({ ...old, pageSize, page: 1 }) })
        }
        workspaceId={workspaceId}
        collectionId={collectionId}
        canRegister={canRegister}
        onOpenCompilationTab={() => {
          void navigate({
            to: "/workspaces/$workspaceId/collections/$collectionId",
            params: { workspaceId, collectionId },
            search: { page: 1, pageSize: 20, tab: "compilations" },
          });
        }}
      />
    </div>
  );
}
