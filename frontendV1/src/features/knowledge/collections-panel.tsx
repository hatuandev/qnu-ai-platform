import { Link } from "@tanstack/react-router";
import {
  ChevronRight,
  FolderOpen,
  FolderPlus,
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
import { CollectionFormDialog } from "@/features/knowledge/collection-form-dialog";
import { canManageKnowledge } from "@/features/knowledge/permissions";
import { useCollectionsQuery } from "@/features/knowledge/queries";
import type { KBCollection } from "@/features/knowledge/types";
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
  const { role, isPending: rolePending } = useCallerWorkspaceRole(workspaceId);
  const collectionsQuery = useCollectionsQuery(workspaceId, { page, pageSize });

  const [searchQuery, setSearchQuery] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
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
    <div className="space-y-4">
      {/* Compact Toolbar */}
      <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 sm:max-w-xs">
          <Search className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-8 text-xs h-8"
            placeholder="Tìm theo tên bộ sưu tập..."
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
          />
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            className="gap-1.5 text-xs h-8"
            disabled={!canManage}
            onClick={() => setCreateOpen(true)}
            title={
              canManage
                ? undefined
                : "Cần vai trò admin hoặc editor để tạo bộ sưu tập"
            }
          >
            <FolderPlus className="size-3.5" />
            <span>Tạo bộ sưu tập</span>
          </Button>
        </div>
      </div>

      {/* Query state handling */}
      {collectionsQuery.isLoading ? (
        <Card className="rounded-xl shadow-2xs">
          <div className="space-y-3 p-4">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        </Card>
      ) : collectionsQuery.isError ? (
        <ErrorState
          error={collectionsQuery.error}
          onRetry={() => void collectionsQuery.refetch()}
        />
      ) : items.length === 0 ? (
        <Card className="rounded-xl shadow-2xs">
          <CardContent className="py-12">
            <EmptyState
              icon={FolderOpen}
              title={
                searchQuery.trim()
                  ? "Không tìm thấy bộ sưu tập phù hợp"
                  : "Chưa có bộ sưu tập nào"
              }
              description={
                searchQuery.trim()
                  ? `Không có bộ sưu tập nào khớp với từ khóa "${searchQuery}".`
                  : "Tạo bộ sưu tập đầu tiên để bắt đầu lưu trữ tài liệu tri thức cho workspace này."
              }
              action={
                canManage && !searchQuery.trim()
                  ? {
                      label: "Tạo bộ sưu tập ngay",
                      onClick: () => setCreateOpen(true),
                    }
                  : undefined
              }
            />
          </CardContent>
        </Card>
      ) : (
        <Card className="rounded-xl shadow-2xs overflow-hidden">
          {/* Desktop Table View */}
          <div className="hidden sm:block overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[30%]">Tên bộ sưu tập</TableHead>
                  <TableHead className="w-[30%]">Mô tả</TableHead>
                  <TableHead className="w-[12%] text-center">
                    Số nguồn
                  </TableHead>
                  <TableHead className="w-[13%]">Người tạo</TableHead>
                  <TableHead className="w-[15%]">Ngày tạo</TableHead>
                  <TableHead className="w-[100px] text-right">
                    Thao tác
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((collection) => (
                  <TableRow key={collection.id} className="group">
                    <TableCell>
                      <Link
                        to="/workspaces/$workspaceId/collections/$collectionId"
                        params={{
                          workspaceId,
                          collectionId: collection.id,
                        }}
                        search={{ page: 1, pageSize: 20 }}
                        className="font-medium text-foreground hover:text-primary transition-colors flex items-center gap-1.5"
                      >
                        <FolderOpen className="size-4 shrink-0 text-muted-foreground group-hover:text-primary transition-colors" />
                        <span className="truncate">{collection.name}</span>
                      </Link>
                    </TableCell>

                    <TableCell className="text-xs text-muted-foreground">
                      <span
                        className="line-clamp-2"
                        title={collection.description ?? ""}
                      >
                        {collection.description || "—"}
                      </span>
                    </TableCell>

                    <TableCell className="text-center">
                      <Badge variant="secondary" className="font-mono text-xs">
                        {collection.source_count}
                      </Badge>
                    </TableCell>

                    <TableCell className="font-mono text-xs text-muted-foreground truncate">
                      {collection.created_by}
                    </TableCell>

                    <TableCell className="text-xs text-muted-foreground">
                      {formatDateTimeValue(collection.created_at)}
                    </TableCell>

                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="size-7 p-0"
                          disabled={!canManage}
                          title={
                            canManage
                              ? "Sửa bộ sưu tập"
                              : "Cần vai trò admin/editor"
                          }
                          onClick={() => setEditingCollection(collection)}
                        >
                          <Pencil className="size-3.5 text-muted-foreground" />
                          <span className="sr-only">Sửa</span>
                        </Button>

                        <Button
                          asChild
                          size="sm"
                          variant="ghost"
                          className="size-7 p-0"
                        >
                          <Link
                            to="/workspaces/$workspaceId/collections/$collectionId"
                            params={{
                              workspaceId,
                              collectionId: collection.id,
                            }}
                            search={{ page: 1, pageSize: 20 }}
                            title="Xem chi tiết bộ sưu tập"
                          >
                            <ChevronRight className="size-3.5 text-muted-foreground" />
                            <span className="sr-only">Chi tiết</span>
                          </Link>
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Mobile Card View */}
          <div className="divide-y sm:hidden">
            {items.map((collection) => (
              <div key={collection.id} className="p-4 space-y-2.5">
                <div className="flex items-start justify-between gap-2">
                  <Link
                    to="/workspaces/$workspaceId/collections/$collectionId"
                    params={{
                      workspaceId,
                      collectionId: collection.id,
                    }}
                    search={{ page: 1, pageSize: 20 }}
                    className="font-medium text-sm text-foreground hover:text-primary transition-colors flex items-center gap-1.5"
                  >
                    <FolderOpen className="size-4 shrink-0 text-primary" />
                    <span>{collection.name}</span>
                  </Link>

                  <Badge
                    variant="secondary"
                    className="font-mono text-xs shrink-0"
                  >
                    {collection.source_count} nguồn
                  </Badge>
                </div>

                {collection.description ? (
                  <p className="text-xs text-muted-foreground line-clamp-2">
                    {collection.description}
                  </p>
                ) : null}

                <div className="flex items-center justify-between pt-1 text-[11px] text-muted-foreground border-t">
                  <span>{formatDateTimeValue(collection.created_at)}</span>
                  <div className="flex items-center gap-1">
                    {canManage ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 px-2 text-[11px]"
                        onClick={() => setEditingCollection(collection)}
                      >
                        <Pencil className="size-3 mr-1" />
                        Sửa
                      </Button>
                    ) : null}

                    <Button
                      asChild
                      size="sm"
                      variant="outline"
                      className="h-6 px-2 text-[11px]"
                    >
                      <Link
                        to="/workspaces/$workspaceId/collections/$collectionId"
                        params={{
                          workspaceId,
                          collectionId: collection.id,
                        }}
                        search={{ page: 1, pageSize: 20 }}
                      >
                        Xem
                        <ChevronRight className="size-3 ml-0.5" />
                      </Link>
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {total > 0 ? (
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

      {/* Dialog for Create */}
      <CollectionFormDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        workspaceId={workspaceId}
      />

      {/* Dialog for Edit */}
      <CollectionFormDialog
        open={Boolean(editingCollection)}
        onOpenChange={(open) => {
          if (!open) setEditingCollection(null);
        }}
        workspaceId={workspaceId}
        collection={editingCollection}
      />
    </div>
  );
}
