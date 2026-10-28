import { Link, useNavigate } from "@tanstack/react-router";
import {
  ChevronRight,
  Database,
  FileText,
  FileUp,
  FolderOpen,
  FolderPlus,
  MoreVertical,
  Pencil,
  Search,
} from "lucide-react";
import { useMemo, useState } from "react";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { EmptyState } from "@/components/admin/empty-state";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ViewModeToggle } from "@/components/ui/view-mode-toggle";
import { CollectionFormDialog } from "@/features/knowledge/collection-form-dialog";
import { canManageKnowledge } from "@/features/knowledge/permissions";
import { useCollectionsQuery } from "@/features/knowledge/queries";
import { SourceUploadDialog } from "@/features/knowledge/source-upload-dialog";
import type { KBCollection } from "@/features/knowledge/types";
import { LifecycleActions } from "@/features/lifecycle/lifecycle-actions";
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";
import { formatDateTimeValue } from "@/lib/date-utils";

export function CollectionsPanel({
  workspaceId,
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
}: {
  workspaceId: string;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
}) {
  const navigate = useNavigate();
  const { role, isPending: rolePending } = useCallerWorkspaceRole(workspaceId);
  const collectionsQuery = useCollectionsQuery(workspaceId, { page, pageSize });

  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");
  const [createOpen, setCreateOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [editingCollection, setEditingCollection] =
    useState<KBCollection | null>(null);

  const canManage = !rolePending && canManageKnowledge(role);

  const rawItems = collectionsQuery.data?.items ?? [];
  const total = collectionsQuery.data?.meta.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  // Client-side quick filter on current loaded page
  const items = useMemo(() => {
    if (!searchQuery.trim()) return rawItems;
    const q = searchQuery.toLowerCase().trim();
    return rawItems.filter(
      (item) =>
        item.name.toLowerCase().includes(q) ||
        item.description?.toLowerCase().includes(q),
    );
  }, [rawItems, searchQuery]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold tracking-tight text-foreground flex items-center gap-2">
            <span className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Database className="size-4" />
            </span>
            Kho tri thức
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            Quản lý các kho dữ liệu, thư mục và tài liệu phục vụ huấn luyện và phản hồi của trợ lý AI.
          </p>
        </div>

        {/* Primary and Secondary Action Buttons */}
        <div className="flex items-center gap-2.5 shrink-0">
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5 text-xs h-9"
            disabled={!canManage}
            onClick={() => setCreateOpen(true)}
            title={
              canManage
                ? undefined
                : "Cần vai trò admin hoặc editor để tạo kho tri thức"
            }
          >
            <FolderPlus className="size-4 text-muted-foreground" />
            <span>Tạo kho</span>
          </Button>

          <Button
            size="sm"
            className="gap-1.5 text-xs h-9 shadow-xs"
            disabled={!canManage}
            onClick={() => setUploadOpen(true)}
            title={
              canManage
                ? undefined
                : "Cần vai trò admin hoặc editor để tải tài liệu"
            }
          >
            <FileUp className="size-4" />
            <span>Tải tài liệu</span>
          </Button>
        </div>
      </div>

      {/* Left-Right Split Filter Bar Pattern */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
        <div className="relative w-full sm:w-72 lg:w-80">
          <Search className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-8 text-xs h-9"
            placeholder="Tìm theo tên kho tri thức..."
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
          />
        </div>

        <div className="flex items-center justify-end gap-2">
          <ViewModeToggle value={viewMode} onChange={setViewMode} />
        </div>
      </div>

      {/* Query state handling */}
      {collectionsQuery.isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <Skeleton className="h-36 rounded-xl" />
          <Skeleton className="h-36 rounded-xl" />
          <Skeleton className="h-36 rounded-xl" />
        </div>
      ) : collectionsQuery.isError ? (
        <ErrorState
          error={collectionsQuery.error}
          onRetry={() => void collectionsQuery.refetch()}
        />
      ) : items.length === 0 ? (
        <Card className="rounded-xl shadow-2xs border-border/70">
          <CardContent className="py-12">
            <EmptyState
              icon={FolderOpen}
              title={
                searchQuery.trim()
                  ? "Không tìm thấy kho tri thức phù hợp"
                  : "Chưa có kho tri thức nào"
              }
              description={
                searchQuery.trim()
                  ? `Không có kho tri thức nào khớp với từ khóa "${searchQuery}".`
                  : "Tạo kho đầu tiên để bắt đầu tải lên và tổ chức tài liệu cho workspace này."
              }
              action={
                canManage && !searchQuery.trim()
                  ? {
                      label: "Tạo kho ngay",
                      onClick: () => setCreateOpen(true),
                    }
                  : undefined
              }
            />
          </CardContent>
        </Card>
      ) : viewMode === "grid" ? (
        /* Grid Cards View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((item) => (
            <Card
              key={item.id}
              className="group relative rounded-xl border-border/70 transition-all hover:border-primary/40 hover:shadow-xs flex flex-col justify-between"
            >
              <CardContent className="p-4 flex flex-col justify-between h-full">
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <Link
                      to="/workspaces/$workspaceId/collections/$collectionId"
                      params={{ workspaceId, collectionId: item.id }}
                      search={{ page: 1, pageSize: 20 }}
                      className="flex items-center gap-2.5 min-w-0 flex-1 hover:text-primary transition-colors"
                    >
                      <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <FolderOpen className="size-4" />
                      </span>
                      <span className="font-semibold text-sm truncate text-foreground group-hover:text-primary">
                        {item.name}
                      </span>
                    </Link>

                    {canManage ? (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="size-7 p-0 text-muted-foreground hover:text-foreground shrink-0"
                          >
                            <MoreVertical className="size-3.5" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-40 text-xs">
                          <DropdownMenuItem
                            className="gap-2"
                            onClick={() => setEditingCollection(item)}
                          >
                            <Pencil className="size-3.5" />
                            <span>Sửa thông tin</span>
                          </DropdownMenuItem>
                          <LifecycleActions
                            workspaceId={workspaceId}
                            kind="collection"
                            resourceId={item.id}
                            label={item.name}
                            role={role?.kind}
                          />
                        </DropdownMenuContent>
                      </DropdownMenu>
                    ) : null}
                  </div>

                  <p className="text-xs text-muted-foreground line-clamp-2 min-h-8 mb-3">
                    {item.description || "Chưa có mô tả chi tiết."}
                  </p>
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-border/50 text-[11px] text-muted-foreground">
                  <div className="flex items-center gap-1.5">
                    <FileText className="size-3.5 text-primary/70" />
                    <span>
                      <strong className="text-foreground">{item.source_count}</strong> tài liệu
                    </span>
                  </div>
                  <Link
                    to="/workspaces/$workspaceId/collections/$collectionId"
                    params={{ workspaceId, collectionId: item.id }}
                    search={{ page: 1, pageSize: 20 }}
                    className="flex items-center gap-1 text-primary font-medium hover:underline"
                  >
                    <span>Mở kho</span>
                    <ChevronRight className="size-3" />
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        /* Table View */
        <Card className="rounded-xl shadow-2xs overflow-hidden border-border/70">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[35%]">Tên kho tri thức</TableHead>
                  <TableHead className="w-[35%]">Mô tả</TableHead>
                  <TableHead className="w-[12%] text-center">Tài liệu</TableHead>
                  <TableHead className="w-[18%]">Cập nhật</TableHead>
                  <TableHead className="w-[60px] text-right"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.id} className="group hover:bg-muted/40">
                    <TableCell className="font-medium">
                      <Link
                        to="/workspaces/$workspaceId/collections/$collectionId"
                        params={{ workspaceId, collectionId: item.id }}
                        search={{ page: 1, pageSize: 20 }}
                        className="flex items-center gap-2 text-foreground hover:text-primary transition-colors"
                      >
                        <FolderOpen className="size-4 shrink-0 text-primary" />
                        <span className="truncate">{item.name}</span>
                      </Link>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground max-w-xs truncate">
                      {item.description || "—"}
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge variant="secondary" className="text-xs font-normal">
                        {item.source_count}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                      {formatDateTimeValue(item.updated_at || item.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      {canManage ? (
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="size-7 p-0 text-muted-foreground hover:text-foreground"
                            >
                              <MoreVertical className="size-3.5" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-40 text-xs">
                            <DropdownMenuItem
                              className="gap-2"
                              onClick={() => setEditingCollection(item)}
                            >
                              <Pencil className="size-3.5" />
                              <span>Sửa thông tin</span>
                            </DropdownMenuItem>
                            <LifecycleActions
                              workspaceId={workspaceId}
                              kind="collection"
                              resourceId={item.id}
                              label={item.name}
                              role={role?.kind}
                            />
                          </DropdownMenuContent>
                        </DropdownMenu>
                      ) : null}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
      )}

      {/* Pagination */}
      {total > 0 ? (
        <DataTablePagination
          pageIndex={page - 1}
          pageSize={pageSize}
          pageCount={pageCount}
          totalItems={total}
          canPreviousPage={page > 1}
          canNextPage={page < pageCount}
          onPageChange={(idx) => onPageChange(idx + 1)}
          onPageSizeChange={onPageSizeChange}
        />
      ) : null}

      {/* Upload Dialog: Selects destination collection or creates one */}
      <SourceUploadDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        workspaceId={workspaceId}
        onSuccess={() => {
          void collectionsQuery.refetch();
        }}
      />

      {/* Create Dialog */}
      <CollectionFormDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        workspaceId={workspaceId}
        onSuccess={(created) => {
          void collectionsQuery.refetch();
          void navigate({
            to: "/workspaces/$workspaceId/collections/$collectionId",
            params: { workspaceId, collectionId: created.id },
            search: { page: 1, pageSize: 20 },
          });
        }}
      />

      {/* Edit Dialog */}
      {editingCollection ? (
        <CollectionFormDialog
          open={Boolean(editingCollection)}
          onOpenChange={(open) => !open && setEditingCollection(null)}
          workspaceId={workspaceId}
          collectionToEdit={editingCollection}
          onSuccess={() => {
            void collectionsQuery.refetch();
            setEditingCollection(null);
          }}
        />
      ) : null}
    </div>
  );
}
