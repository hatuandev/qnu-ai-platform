import { Link, useNavigate } from "@tanstack/react-router";
import {
  Archive,
  Database,
  Eye,
  FileText,
  FolderOpen,
  MoreHorizontal,
  Pencil,
  Plus,
  RotateCcw,
  Trash2,
} from "lucide-react";
import { useMemo, useState } from "react";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { DebouncedSearchInput } from "@/components/admin/debounced-search-input";
import { EmptyState } from "@/components/admin/empty-state";
import { ErrorState } from "@/components/admin/error-state";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ViewModeToggle } from "@/components/ui/view-mode-toggle";
import {
  CollectionCard,
  CollectionCardSkeleton,
} from "@/features/knowledge/collection-card";
import { CollectionFormDialog } from "@/features/knowledge/collection-form-dialog";
import { canManageKnowledge } from "@/features/knowledge/permissions";
import { useCollectionsQuery } from "@/features/knowledge/queries";
import type { KBCollection } from "@/features/knowledge/types";
import { LifecycleActionDialog } from "@/features/lifecycle/action-dialog";
import { canLifecycleAction } from "@/features/lifecycle/permissions";
import type { LifecycleOperation } from "@/features/lifecycle/types";
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
  const [editingCollection, setEditingCollection] =
    useState<KBCollection | null>(null);
  const [lifecycleTarget, setLifecycleTarget] = useState<{
    collection: KBCollection;
    action: LifecycleOperation;
  } | null>(null);

  const canManage = !rolePending && canManageKnowledge(role);
  const canArchive = canLifecycleAction(role, "collection", "archive");
  const canDelete = canLifecycleAction(role, "collection", "delete");

  const rawItems = collectionsQuery.data?.items ?? [];
  const total = collectionsQuery.data?.meta.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  // Quick summary counts for KPI metrics
  const totalDocuments = useMemo(
    () => rawItems.reduce((acc, c) => acc + (c.source_count || 0), 0),
    [rawItems],
  );

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

  const renderCollectionMenu = (item: KBCollection) => (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="size-7 p-0 text-muted-foreground hover:text-foreground shrink-0"
          aria-label={`Thao tác với ${item.name}`}
        >
          <MoreHorizontal className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48 text-xs">
        <DropdownMenuItem
          onClick={() =>
            void navigate({
              to: "/workspaces/$workspaceId/knowledge/$knowledgeId",
              params: { workspaceId, knowledgeId: item.id },
              search: { page: 1, pageSize: 20 },
            })
          }
        >
          <Eye className="size-3.5 mr-2 text-muted-foreground" />
          <span>Mở kho tri thức</span>
        </DropdownMenuItem>
        {canManage ? (
          <DropdownMenuItem onClick={() => setEditingCollection(item)}>
            <Pencil className="size-3.5 mr-2 text-muted-foreground" />
            <span>Sửa thông tin kho</span>
          </DropdownMenuItem>
        ) : null}
        {canArchive || canDelete ? <DropdownMenuSeparator /> : null}
        {canArchive ? (
          <DropdownMenuItem
            onClick={() =>
              setLifecycleTarget({ collection: item, action: "archive" })
            }
          >
            <Archive className="size-3.5 mr-2 text-muted-foreground" />
            <span>Lưu trữ kho</span>
          </DropdownMenuItem>
        ) : null}
        {canDelete ? (
          <DropdownMenuItem
            className="text-destructive focus:text-destructive"
            onClick={() =>
              setLifecycleTarget({ collection: item, action: "delete" })
            }
          >
            <Trash2 className="size-3.5 mr-2" />
            <span>Xóa kho tri thức</span>
          </DropdownMenuItem>
        ) : null}
      </DropdownMenuContent>
    </DropdownMenu>
  );

  return (
    <div className="space-y-6">
      {/* 1. Page Header */}
      <PageHeader
        eyebrow="QNU AI · TRI THỨC"
        title="Kho tri thức"
        description="Quản lý các kho tài liệu, tổ chức thư mục, đọc nội dung và hiệu đính."
        actions={
          canManage ? (
            <Button
              size="sm"
              className="gap-1.5 text-xs font-semibold h-9"
              onClick={() => setCreateOpen(true)}
            >
              <Plus className="size-3.5" />
              <span>Tạo kho</span>
            </Button>
          ) : undefined
        }
      />

      {/* 2. KPI Metrics Summary Cards */}
      <Card className="overflow-hidden border bg-card shadow-xs">
        <CardContent className="grid p-0 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x">
          <KpiMetric
            icon={Database}
            label="Tổng số kho tri thức"
            value={total.toLocaleString("vi-VN")}
          />
          <KpiMetric
            icon={FileText}
            label="Tổng số tài liệu"
            value={totalDocuments.toLocaleString("vi-VN")}
          />
        </CardContent>
      </Card>

      {/* 3. Toolbar: DebouncedSearchInput & View Mode Toggle */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
        <div className="w-full sm:w-80">
          <DebouncedSearchInput
            placeholder="Tìm kho tri thức..."
            value={searchQuery}
            onChange={setSearchQuery}
            className="text-xs h-9"
          />
        </div>

        <div className="flex items-center justify-end gap-2">
          {searchQuery ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-9 px-2.5 text-xs text-muted-foreground hover:text-foreground"
              onClick={() => setSearchQuery("")}
            >
              <RotateCcw className="size-3.5 mr-1" />
              <span>Đặt lại</span>
            </Button>
          ) : null}
          <ViewModeToggle value={viewMode} onChange={setViewMode} />
        </div>
      </div>

      {/* 4. Query State Handling: Skeleton / ErrorState / EmptyState */}
      {collectionsQuery.isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <CollectionCardSkeleton />
          <CollectionCardSkeleton />
          <CollectionCardSkeleton />
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
        /* 5. Grid View Cards */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((item) => (
            <CollectionCard
              key={item.id}
              collection={item}
              workspaceId={workspaceId}
              canManage={canManage}
              canArchive={canArchive}
              canDelete={canDelete}
              onEdit={setEditingCollection}
              onArchive={(col) =>
                setLifecycleTarget({ collection: col, action: "archive" })
              }
              onDelete={(col) =>
                setLifecycleTarget({ collection: col, action: "delete" })
              }
            />
          ))}
        </div>
      ) : (
        /* 6. Table View */
        <Card className="rounded-xl shadow-2xs overflow-hidden border-border/70">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40">
                  <TableHead className="w-[35%] font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3">
                    Tên kho tri thức
                  </TableHead>
                  <TableHead className="w-[35%] font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3">
                    Mô tả
                  </TableHead>
                  <TableHead className="w-[12%] text-center font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3">
                    Tài liệu
                  </TableHead>
                  <TableHead className="w-[18%] font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3">
                    Cập nhật
                  </TableHead>
                  <TableHead className="w-[60px] text-right font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.id} className="group hover:bg-muted/40">
                    <TableCell className="font-medium">
                      <Link
                        to="/workspaces/$workspaceId/knowledge/$knowledgeId"
                        params={{ workspaceId, knowledgeId: item.id }}
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
                      <Badge
                        variant="secondary"
                        className="text-xs font-normal"
                      >
                        {item.source_count}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                      {formatDateTimeValue(item.updated_at || item.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      {renderCollectionMenu(item)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
      )}

      {/* 7. Pagination (Tái dùng DataTablePagination chuẩn của Admin) */}
      {total > 0 ? (
        <DataTablePagination
          page={page}
          pageSize={pageSize}
          pageCount={pageCount}
          total={total}
          onPageChange={onPageChange}
          onPageSizeChange={onPageSizeChange}
        />
      ) : null}

      {/* 8. Dialogs (Tái dùng CollectionFormDialog) */}
      <CollectionFormDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        workspaceId={workspaceId}
        onSuccess={(created) => {
          void collectionsQuery.refetch();
          void navigate({
            to: "/workspaces/$workspaceId/knowledge/$knowledgeId",
            params: { workspaceId, knowledgeId: created.id },
            search: { page: 1, pageSize: 20 },
          });
        }}
      />

      {editingCollection ? (
        <CollectionFormDialog
          open={Boolean(editingCollection)}
          onOpenChange={(open) => !open && setEditingCollection(null)}
          workspaceId={workspaceId}
          collection={editingCollection}
          onSuccess={() => {
            void collectionsQuery.refetch();
            setEditingCollection(null);
          }}
        />
      ) : null}

      {lifecycleTarget ? (
        <LifecycleActionDialog
          workspaceId={workspaceId}
          label={lifecycleTarget.collection.name}
          target={{
            kind: "collection",
            resource_id: lifecycleTarget.collection.id,
            action: lifecycleTarget.action,
          }}
          onClose={() => {
            setLifecycleTarget(null);
            void collectionsQuery.refetch();
          }}
        />
      ) : null}
    </div>
  );
}
