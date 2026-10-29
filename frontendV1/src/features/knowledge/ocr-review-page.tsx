import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  ChevronRight,
  ClipboardList,
  Cpu,
} from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CompilationDialog } from "@/features/knowledge/compilation-dialog";
import { OcrTabContainer, type OcrSubTab } from "@/features/knowledge/ocr-tab-container";
import { canCreateOrEditCompilation, canManageKnowledge } from "@/features/knowledge/permissions";
import {
  useCollectionQuery,
  useRevisionsQuery,
  useSourceQuery,
} from "@/features/knowledge/queries";
import type { KBRevision } from "@/features/knowledge/types";
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";

export interface OcrReviewSearchParams {
  revisionId?: string;
  runId?: string;
  checkId?: string;
  page?: number;
  subTab?: OcrSubTab;
}

export function OcrReviewPage({
  workspaceId,
  collectionId,
  sourceId,
  search,
  onSearchChange,
}: {
  workspaceId: string;
  collectionId: string;
  sourceId: string;
  search?: OcrReviewSearchParams;
  onSearchChange?: (params: Partial<OcrReviewSearchParams>) => void;
}) {
  const navigate = useNavigate();
  const { role, isPending: rolePending } = useCallerWorkspaceRole(workspaceId);
  const collectionQuery = useCollectionQuery(workspaceId, collectionId);
  const sourceQuery = useSourceQuery(workspaceId, collectionId, sourceId);
  const revisionsQuery = useRevisionsQuery(workspaceId, collectionId, sourceId);

  const [compilationDialogOpen, setCompilationDialogOpen] = useState(false);

  const canManage = !rolePending && canManageKnowledge(role);
  const canCompile = !rolePending && canCreateOrEditCompilation(role);

  const collection = collectionQuery.data;
  const source = sourceQuery.data;
  const revisions = revisionsQuery.data ?? [];

  // Active revision (defaults to revisionId in search or latest revision)
  const activeRevision: KBRevision | undefined =
    revisions.find((r) => r.id === search?.revisionId) ?? revisions[0];

  const activeRevisionId = activeRevision?.id ?? "";
  const activeRevisionNo = activeRevision?.revision_no ?? 1;

  if (sourceQuery.isLoading || revisionsQuery.isLoading) {
    return (
      <div className="space-y-4 p-4">
        <Skeleton className="h-6 w-64" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Breadcrumb Navigation */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between pb-3 border-b border-border/60">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground flex-wrap mb-1">
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
              search={{ page: 1, pageSize: 20 }}
              className="hover:text-foreground transition-colors truncate max-w-[150px]"
            >
              {collection?.name ?? "Kho tri thức"}
            </Link>
            <ChevronRight className="size-3 text-muted-foreground/60" />
            <Link
              to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId"
              params={{ workspaceId, collectionId, sourceId }}
              className="hover:text-foreground transition-colors truncate max-w-[180px]"
            >
              {source?.title ?? "Tài liệu"}
            </Link>
            <ChevronRight className="size-3 text-muted-foreground/60" />
            <span className="font-semibold text-foreground">OCR & Hiệu đính</span>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="flex size-7 items-center justify-center rounded bg-primary/10 text-primary">
              <Cpu className="size-4" />
            </span>
            <h1 className="text-lg sm:text-xl font-bold tracking-tight text-foreground truncate">
              OCR & Hiệu đính: {source?.title}
            </h1>
            <Badge variant="outline" className="text-xs font-mono h-5">
              v{activeRevisionNo}
            </Badge>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2 shrink-0">
          <Button
            size="sm"
            variant="outline"
            className="text-xs h-9 gap-1.5"
            onClick={() =>
              void navigate({
                to: "/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId",
                params: { workspaceId, collectionId, sourceId },
              })
            }
          >
            <ArrowLeft className="size-3.5" />
            <span>Quay lại tài liệu</span>
          </Button>

          {canCompile && search?.runId ? (
            <Button
              size="sm"
              className="text-xs h-9 gap-1.5 shadow-xs"
              onClick={() => setCompilationDialogOpen(true)}
            >
              <ClipboardList className="size-3.5" />
              <span>Chuyển sang biên soạn</span>
            </Button>
          ) : null}
        </div>
      </div>

      {/* OCR Core Container (Comparison View, Runs, Review, Spell Check, Artifacts) */}
      {activeRevisionId ? (
        <OcrTabContainer
          workspaceId={workspaceId}
          collectionId={collectionId}
          sourceId={sourceId}
          revisionId={activeRevisionId}
          revisionNo={activeRevisionNo}
          fileName={activeRevision?.file_name ?? source?.file_name ?? ""}
          contentType={activeRevision?.content_type ?? source?.content_type ?? ""}
          canManage={canManage}
          initialRunId={search?.runId}
          initialPage={search?.page}
          initialSubTab={search?.subTab ?? "comparison"}
          checkId={search?.checkId}
          onDeepLinkChange={(params) => {
            onSearchChange?.({
              runId: params.runId,
              page: params.page,
              subTab: params.subTab,
              checkId: params.checkId,
            });
          }}
        />
      ) : (
        <Card className="rounded-xl border-dashed p-8 text-center text-xs text-muted-foreground">
          Chưa tìm thấy phiên bản tệp để thực hiện OCR.
        </Card>
      )}

      {/* Compilation Dialog (to seamlessly continue pipeline to Compiler) */}
      {search?.runId ? (
        <CompilationDialog
          isOpen={compilationDialogOpen}
          onClose={() => setCompilationDialogOpen(false)}
          workspaceId={workspaceId}
          collectionId={collectionId}
          initialRun={{
            runId: search.runId,
            sourceId,
            sourceTitle: source?.title ?? "Tài liệu",
            revisionId: activeRevisionId,
            revisionNo: activeRevisionNo,
            generation: 1,
          }}
          onSuccess={(runId) => {
            void navigate({
              to: "/workspaces/$workspaceId/collections/$collectionId/compilations/$runId",
              params: { workspaceId, collectionId, runId },
            });
          }}
        />
      ) : null}
    </div>
  );
}

