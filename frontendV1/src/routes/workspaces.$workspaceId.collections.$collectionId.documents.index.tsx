import { createFileRoute } from "@tanstack/react-router";
import { Building2, FileCheck, FolderOpen, Library } from "lucide-react";
import { PageBreadcrumbs } from "@/components/admin/page-breadcrumbs";
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
      <PageBreadcrumbs
        items={[
          {
            label: "Workspace",
            to: "/workspaces/$workspaceId",
            params: { workspaceId },
            icon: Building2,
          },
          {
            label: "Kho tri thức",
            to: "/workspaces/$workspaceId/collections",
            params: { workspaceId },
            search: { page: 1, pageSize: 20 },
            icon: Library,
          },
          {
            label: collection?.name ?? "Kho tri thức",
            to: "/workspaces/$workspaceId/collections/$collectionId",
            params: { workspaceId, collectionId },
            search: { page: 1, pageSize: 20, tab: "documents" },
            icon: FolderOpen,
            maxChars: 24,
          },
          {
            label: "Tài liệu biên soạn",
            icon: FileCheck,
            current: true,
          },
        ]}
      />

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
