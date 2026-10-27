import { createFileRoute, Link } from "@tanstack/react-router";
import { ChevronRight } from "lucide-react";
import { useState } from "react";
import { z } from "zod";
import { CompilationDialog } from "@/features/knowledge/compilation-dialog";
import { CompilationRunsList } from "@/features/knowledge/compilation-runs-list";
import { canCreateOrEditCompilation } from "@/features/knowledge/permissions";
import { useCollectionQuery } from "@/features/knowledge/queries";
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";
import { pageSearchSchema } from "@/features/workspaces/search";

const compilationsSearchSchema = pageSearchSchema.partial().extend({
  create: z.boolean().optional(),
  ocrRunId: z.string().optional(),
  sourceId: z.string().optional(),
  sourceTitle: z.string().optional(),
  revisionId: z.string().optional(),
  revisionNo: z.coerce.number().int().optional(),
  generation: z.coerce.number().int().optional(),
  version: z.coerce.number().int().optional(),
});

export const Route = createFileRoute(
  "/workspaces/$workspaceId/collections/$collectionId/compilations/",
)({
  validateSearch: (search) => compilationsSearchSchema.parse(search),
  component: CompilationsListRoute,
});

function CompilationsListRoute() {
  const { workspaceId, collectionId } = Route.useParams();
  const search = Route.useSearch();
  const navigate = Route.useNavigate();

  const [dialogOpen, setDialogOpen] = useState<boolean>(
    Boolean(search.create || search.ocrRunId),
  );

  const { role, isPending: rolePending } = useCallerWorkspaceRole(workspaceId);
  const canManage = !rolePending && canCreateOrEditCompilation(role);

  const collectionQuery = useCollectionQuery(workspaceId, collectionId);
  const collection = collectionQuery.data;

  const initialRun = search.ocrRunId
    ? {
        runId: search.ocrRunId,
        sourceId: search.sourceId ?? "",
        sourceTitle: search.sourceTitle ?? "Tài liệu",
        revisionId: search.revisionId ?? "",
        revisionNo: search.revisionNo ?? 1,
        generation: search.generation ?? 1,
        textVersion: search.version ?? 0,
      }
    : null;

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
          search={{ page: 1, pageSize: 20, tab: "compilations" }}
          className="hover:text-foreground transition-colors truncate max-w-[150px]"
        >
          {collection?.name ?? "Bộ sưu tập"}
        </Link>
        <ChevronRight className="size-3 text-muted-foreground/60" />
        <span className="font-medium text-foreground">Biên soạn tri thức</span>
      </div>

      <CompilationRunsList
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
        canManage={canManage}
        onOpenCreateDialog={() => setDialogOpen(true)}
      />

      <CompilationDialog
        workspaceId={workspaceId}
        collectionId={collectionId}
        isOpen={dialogOpen}
        initialRun={initialRun}
        onClose={() => {
          setDialogOpen(false);
          // clear create search params
          void navigate({
            search: (old) => ({
              ...old,
              create: undefined,
              ocrRunId: undefined,
            }),
            replace: true,
          });
        }}
        onSuccess={(runId) => {
          void navigate({
            to: "/workspaces/$workspaceId/collections/$collectionId/compilations/$runId",
            params: {
              workspaceId,
              collectionId,
              runId,
            },
          });
        }}
      />
    </div>
  );
}
