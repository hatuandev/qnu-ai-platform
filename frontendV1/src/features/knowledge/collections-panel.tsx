import { Link, useNavigate } from "@tanstack/react-router";
import {
  ChevronRight,
  Database,
  Eye,
  FileText,
  FolderOpen,
  FolderTree,
  MoreHorizontal,
  Pencil,
  Plus,
  RotateCcw,
  ScanLine,
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
  const [editingCollection, setEditingCollection] =
    useState<KBCollection | null>(null);

  const canManage = !rolePending && canManageKnowledge(role);

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

  return (
    <div className="space-y-6">
      {/* 1. Page Header (Tái dùng PageHeader chuẩn của Admin Design System) */}
      <PageHeader
        eyebrow="QNU AI · TRI THỨC"
        title="Kho tri thức"
        description="Quản lý các kho dữ liệu, thư mục và tài liệu phục vụ huấn luyện và phản hồi của trợ lý AI."
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

      {/* 2. KPI Metrics Summary Cards (Chuẩn KpiMetric như các trang KTX) */}
      <Card className="overflow-hidden border bg-card shadow-xs">
        <CardContent className="grid p-0 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x">
          <KpiMetric
            icon={Database}
            label="Tổng số kho tri thức"
            value={total.toLocaleString("vi-VN")}
            helper="Kho dữ liệu trong workspace này"
          />
          <KpiMetric
            icon={FileText}
            label="Tài liệu trong các kho trên trang"
            value={totalDocuments.toLocaleString("vi-VN")}
          />
        </CardContent>
      </Card>

      {/* 3. Toolbar: DebouncedSearchInput & View Mode Toggle */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
        <div className="w-full sm:w-80">
          <DebouncedSearchInput
            placeholder="Tìm kho trong trang này..."
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
          <Skeleton className="h-44 rounded-xl" />
          <Skeleton className="h-44 rounded-xl" />
          <Skeleton className="h-44 rounded-xl" />
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
            <Card
              key={item.id}
              className="group relative rounded-xl border-border/70 transition-all hover:border-primary/40 hover:shadow-xs flex flex-col justify-between"
            >
              <CardContent className="p-4 flex flex-col justify-between h-full">
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <Link
                      to="/workspaces/$workspaceId/knowledge/$knowledgeId"
                      params={{ workspaceId, knowledgeId: item.id }}
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
                        <DropdownMenuItem
                          onClick={() =>
                            void navigate({
                              to: "/workspaces/$workspaceId/knowledge/$knowledgeId",
                              params: { workspaceId, knowledgeId: item.id },
                              search: { page: 1, pageSize: 20, stage: "files" },
                            })
                          }
                        >
                          <FolderTree className="size-3.5 mr-2 text-muted-foreground" />
                          <span>1. Quản lý Tài liệu & Thư mục</span>
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() =>
                            void navigate({
                              to: "/workspaces/$workspaceId/knowledge/$knowledgeId",
                              params: { workspaceId, knowledgeId: item.id },
                              search: { page: 1, pageSize: 20, stage: "ocr" },
                            })
                          }
                        >
                          <ScanLine className="size-3.5 mr-2 text-muted-foreground" />
                          <span>2. OCR & Hiệu đính AI</span>
                        </DropdownMenuItem>
                        {canManage ? (
                          <>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() => setEditingCollection(item)}
                            >
                              <Pencil className="size-3.5 mr-2 text-muted-foreground" />
                              <span>Sửa thông tin kho</span>
                            </DropdownMenuItem>
                          </>
                        ) : null}
                      </DropdownMenuContent>
                    </DropdownMenu>
                    <LifecycleActions
                      workspaceId={workspaceId}
                      kind="collection"
                      resourceId={item.id}
                      label={item.name}
                      role={role}
                    />
                  </div>

                  <p className="text-xs text-muted-foreground line-clamp-2 min-h-8 mb-3">
                    {item.description || "Chưa có mô tả chi tiết."}
                  </p>

                  <div className="flex flex-wrap items-center gap-1.5 mb-3">
                    <Link
                      to="/workspaces/$workspaceId/knowledge/$knowledgeId"
                      params={{ workspaceId, knowledgeId: item.id }}
                      search={{ page: 1, pageSize: 20, stage: "files" }}
                      className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md bg-muted/70 hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <span>1. Tài liệu & Thư mục</span>
                    </Link>
                    <Link
                      to="/workspaces/$workspaceId/knowledge/$knowledgeId"
                      params={{ workspaceId, knowledgeId: item.id }}
                      search={{ page: 1, pageSize: 20, stage: "ocr" }}
                      className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md bg-muted/70 hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <span>2. OCR & Hiệu đính</span>
                    </Link>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-border/50 text-[11px] text-muted-foreground">
                  <div className="flex items-center gap-1.5">
                    <FileText className="size-3.5 text-primary/70" />
                    <span>
                      <strong className="text-foreground">
                        {item.source_count}
                      </strong>{" "}
                      tài liệu
                    </span>
                  </div>
                  <Link
                    to="/workspaces/$workspaceId/knowledge/$knowledgeId"
                    params={{ workspaceId, knowledgeId: item.id }}
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
        /* 6. Table View (Chuẩn Table của Admin) */
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
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="size-7 p-0 text-muted-foreground hover:text-foreground"
                            aria-label={`Thao tác với ${item.name}`}
                          >
                            <MoreHorizontal className="size-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent
                          align="end"
                          className="w-48 text-xs"
                        >
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
                          <DropdownMenuItem
                            onClick={() =>
                              void navigate({
                                to: "/workspaces/$workspaceId/knowledge/$knowledgeId",
                                params: { workspaceId, knowledgeId: item.id },
                                search: {
                                  page: 1,
                                  pageSize: 20,
                                  stage: "files",
                                },
                              })
                            }
                          >
                            <FolderTree className="size-3.5 mr-2 text-muted-foreground" />
                            <span>1. Tài liệu & Thư mục</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() =>
                              void navigate({
                                to: "/workspaces/$workspaceId/knowledge/$knowledgeId",
                                params: { workspaceId, knowledgeId: item.id },
                                search: { page: 1, pageSize: 20, stage: "ocr" },
                              })
                            }
                          >
                            <ScanLine className="size-3.5 mr-2 text-muted-foreground" />
                            <span>2. OCR & Hiệu đính AI</span>
                          </DropdownMenuItem>
                          {canManage ? (
                            <>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                onClick={() => setEditingCollection(item)}
                              >
                                <Pencil className="size-3.5 mr-2 text-muted-foreground" />
                                <span>Sửa thông tin kho</span>
                              </DropdownMenuItem>
                            </>
                          ) : null}
                        </DropdownMenuContent>
                      </DropdownMenu>
                      <LifecycleActions
                        workspaceId={workspaceId}
                        kind="collection"
                        resourceId={item.id}
                        label={item.name}
                        role={role}
                      />
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
    </div>
  );
}
