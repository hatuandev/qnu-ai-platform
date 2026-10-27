import { Boxes, Plus, RefreshCw } from "lucide-react";
import { useState } from "react";
import { isPlatformWorkspaceAdmin, useV1Auth } from "@/app/auth/v1";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { EmptyState } from "@/components/admin/empty-state";
import { ErrorState } from "@/components/admin/error-state";
import { PageHeader } from "@/components/admin/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useWorkspacesQuery } from "@/features/workspaces/queries";
import type { Workspace } from "@/features/workspaces/types";
import { WorkspaceFormDialog } from "@/features/workspaces/workspace-form-dialog";
import { WorkspacesTable } from "@/features/workspaces/workspaces-table";
import { cn } from "@/lib/utils";

export function WorkspacesPage({
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
  onOpenWorkspace,
}: {
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  onOpenWorkspace: (workspace: Workspace) => void;
}) {
  const { actor } = useV1Auth();
  const [createOpen, setCreateOpen] = useState(false);
  const query = useWorkspacesQuery({ page, pageSize });
  const canCreate = isPlatformWorkspaceAdmin(actor);

  const total = query.data?.meta.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const items = query.data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="QNU AI · ĐƠN VỊ"
        title="Workspaces"
        description="Đơn vị là biên giới quyền của backendV1. Danh sách chỉ chứa workspace mà tài khoản hiện tại được xem; quyền vẫn do máy chủ quyết định."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs font-semibold"
              onClick={() => void query.refetch()}
              disabled={query.isFetching}
            >
              <RefreshCw
                className={cn("size-3.5", query.isFetching && "animate-spin")}
              />
              <span>Làm mới</span>
            </Button>
            {canCreate ? (
              <Button
                size="sm"
                className="gap-1.5 text-xs font-semibold"
                onClick={() => setCreateOpen(true)}
              >
                <Plus className="size-3.5" />
                <span>Tạo workspace</span>
              </Button>
            ) : null}
          </div>
        }
      />

      {query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <Card className="overflow-hidden rounded-xl shadow-2xs">
          {!query.isLoading && items.length === 0 ? (
            <EmptyState
              icon={Boxes}
              title="Chưa có workspace nào"
              description={
                canCreate
                  ? "Tạo workspace đầu tiên để cấp quyền cho đơn vị."
                  : "Tài khoản của bạn chưa là thành viên của workspace nào. Liên hệ quản trị nền tảng để được cấp quyền."
              }
              action={
                canCreate
                  ? {
                      label: "Tạo workspace",
                      onClick: () => setCreateOpen(true),
                    }
                  : undefined
              }
            />
          ) : (
            <WorkspacesTable
              workspaces={items}
              isLoading={query.isLoading}
              onOpen={onOpenWorkspace}
            />
          )}
          {items.length > 0 ? (
            <div className="border-t px-3">
              <DataTablePagination
                page={page}
                pageSize={pageSize}
                pageCount={pageCount}
                total={total}
                onPageChange={onPageChange}
                onPageSizeChange={onPageSizeChange}
              />
            </div>
          ) : null}
        </Card>
      )}

      <WorkspaceFormDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}
