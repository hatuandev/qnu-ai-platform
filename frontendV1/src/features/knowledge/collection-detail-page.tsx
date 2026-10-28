import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  BookMarked,
  BookOpen,
  ChevronRight,
  FileText,
  FileUp,
  FolderOpen,
  Pencil,
  Search,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CollectionFormDialog } from "@/features/knowledge/collection-form-dialog";
import { CompilationDialog } from "@/features/knowledge/compilation-dialog";
import { CompilationRunsList } from "@/features/knowledge/compilation-runs-list";
import { CompiledDocumentsList } from "@/features/knowledge/compiled-documents-list";
import { IndexPanel } from "@/features/knowledge/index-panel";
import {
  canManageKnowledge,
  canRegisterCompiledDocument,
} from "@/features/knowledge/permissions";
import {
  useCollectionQuery,
  useSourcesQuery,
} from "@/features/knowledge/queries";
import {
  formatBytes,
  formatSourceStatus,
  isDocx,
  isPdf,
} from "@/features/knowledge/schemas";
import { SourceUploadDialog } from "@/features/knowledge/source-upload-dialog";
import { LifecycleActions } from "@/features/lifecycle/lifecycle-actions";
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";
import { formatDateTimeValue } from "@/lib/date-utils";

export type CollectionTab = "sources" | "compilations" | "documents" | "index";

export function CollectionDetailPage({
  workspaceId,
  collectionId,
  sourceAction,
  page,
  pageSize,
  tab = "sources",
  onPageChange,
  onPageSizeChange,
  onTabChange,
}: {
  sourceAction?: "ocr";
  workspaceId: string;
  collectionId: string;
  page: number;
  pageSize: number;
  tab?: CollectionTab;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  onTabChange?: (tab: CollectionTab) => void;
}) {
  const navigate = useNavigate();
  const { role, isPending: rolePending } = useCallerWorkspaceRole(workspaceId);
  const collectionQuery = useCollectionQuery(workspaceId, collectionId);
  const sourcesQuery = useSourcesQuery(workspaceId, collectionId, {
    page,
    pageSize,
  });

  const [activeTab, setActiveTab] = useState<CollectionTab>(tab);
  const [searchQuery, setSearchQuery] = useState("");
  const [editOpen, setEditOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [compilationOpen, setCompilationOpen] = useState(false);

  // Sync tab prop changes
  useEffect(() => {
    if (tab) {
      setActiveTab(tab);
    }
  }, [tab]);

  const canManage = !rolePending && canManageKnowledge(role);
  const canRegister = !rolePending && canRegisterCompiledDocument(role);
  const collection = collectionQuery.data;

  const rawSources = sourcesQuery.data?.items ?? [];
  const total = sourcesQuery.data?.meta.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  const sources = useMemo(() => {
    if (!searchQuery.trim()) return rawSources;
    const q = searchQuery.toLowerCase().trim();
    return rawSources.filter(
      (s) =>
        s.title.toLowerCase().includes(q) ||
        s.file_name.toLowerCase().includes(q),
    );
  }, [rawSources, searchQuery]);

  if (collectionQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (collectionQuery.isError || !collection) {
    return (
      <div className="space-y-4">
        <Button asChild variant="ghost" size="sm" className="gap-1.5 text-xs">
          <Link
            to="/workspaces/$workspaceId/collections"
            params={{ workspaceId }}
            search={{ page: 1, pageSize: 20 }}
          >
            <ArrowLeft className="size-3.5" />
            Danh sách bộ sưu tập
          </Link>
        </Button>
        <ErrorState
          error={collectionQuery.error}
          onRetry={() => void collectionQuery.refetch()}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb & Navigation */}
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
        <span className="font-medium text-foreground truncate max-w-[200px] sm:max-w-md">
          {collection.name}
        </span>
      </div>

      {/* Collection Header Card */}
      <Card className="rounded-xl shadow-2xs">
        <CardContent className="p-4 sm:p-6 space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="space-y-1 min-w-0">
              <div className="flex items-center gap-2">
                <FolderOpen className="size-5 text-primary shrink-0" />
                <h1 className="type-page-title m-0 truncate text-lg sm:text-xl font-bold">
                  {collection.name}
                </h1>
              </div>
              {collection.description ? (
                <p className="text-xs sm:text-sm text-muted-foreground pt-1 whitespace-pre-wrap">
                  {collection.description}
                </p>
              ) : (
                <p className="text-xs text-muted-foreground/70 italic pt-1">
                  Chưa có mô tả cho bộ sưu tập này.
                </p>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2 shrink-0">
              <Button variant="outline" size="sm" asChild>
                <Link
                  to="/workspaces/$workspaceId/collections/$collectionId/answers"
                  params={{ workspaceId, collectionId }}
                >
                  <Search className="size-3.5" />
                  Hỏi đáp thử
                </Link>
              </Button>
              <LifecycleActions
                workspaceId={workspaceId}
                kind="collection"
                resourceId={collectionId}
                label={collection.name}
                role={role}
              />
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 text-xs h-8"
                disabled={!canManage}
                onClick={() => setEditOpen(true)}
                title={canManage ? undefined : "Cần quyền admin/editor để sửa"}
              >
                <Pencil className="size-3.5" />
                <span>Sửa thông tin</span>
              </Button>

              <Button
                size="sm"
                variant="outline"
                className="gap-1.5 text-xs h-8 text-primary border-primary/30 hover:bg-primary/5"
                disabled={!canManage}
                onClick={() => setCompilationOpen(true)}
                title={
                  canManage ? undefined : "Cần quyền admin/editor để biên soạn"
                }
              >
                <BookOpen className="size-3.5" />
                <span>Biên soạn</span>
              </Button>

              <Button
                size="sm"
                className="gap-1.5 text-xs h-8"
                disabled={!canManage}
                onClick={() => setUploadOpen(true)}
                title={
                  canManage ? undefined : "Cần quyền admin/editor để tải lên"
                }
              >
                <FileUp className="size-3.5" />
                <span>Tải lên tài liệu</span>
              </Button>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-y-2 gap-x-6 pt-2 border-t text-xs text-muted-foreground">
            <div>
              <span className="font-semibold text-foreground">
                {collection.source_count}
              </span>{" "}
              nguồn tài liệu
            </div>
            <div>
              Người tạo:{" "}
              <span className="font-mono text-foreground">
                {collection.created_by}
              </span>
            </div>
            <div>Ngày tạo: {formatDateTimeValue(collection.created_at)}</div>
            <div>Cập nhật: {formatDateTimeValue(collection.updated_at)}</div>
          </div>
        </CardContent>
      </Card>

      {/* Main Tabs: Sources vs Compilations vs Documents */}
      <Tabs
        value={activeTab}
        onValueChange={(val) => {
          const nextTab = val as CollectionTab;
          setActiveTab(nextTab);
          onTabChange?.(nextTab);
        }}
        className="space-y-4"
      >
        <div className="flex items-center justify-between border-b pb-1">
          <TabsList className="h-9">
            <TabsTrigger value="sources" className="gap-1.5 text-xs">
              <FileText className="size-3.5" />
              <span>Tài liệu nguồn ({collection.source_count})</span>
            </TabsTrigger>
            <TabsTrigger value="compilations" className="gap-1.5 text-xs">
              <BookOpen className="size-3.5" />
              <span>Biên soạn tri thức</span>
            </TabsTrigger>
            <TabsTrigger value="documents" className="gap-1.5 text-xs">
              <BookMarked className="size-3.5" />
              <span>Tài liệu biên soạn</span>
            </TabsTrigger>
            <TabsTrigger value="index" className="gap-1.5 text-xs">
              <Search className="size-3.5" />
              <span>Chỉ mục &amp; Tìm kiếm</span>
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="sources" className="space-y-3 m-0">
          <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-sm font-semibold text-foreground">
                Danh sách tài liệu trong bộ sưu tập
              </h2>
              <p className="text-xs text-muted-foreground">
                Các tệp gốc đã lưu trữ. Nhấn vào tài liệu để xem lịch sử phiên
                bản hoặc tải bản gốc.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <div className="relative flex-1 sm:w-60">
                <Search className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                <Input
                  className="pl-8 text-xs h-8"
                  placeholder="Lọc tiêu đề, tên tệp..."
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Sources Query State */}
          {sourcesQuery.isLoading ? (
            <Card className="rounded-xl shadow-2xs p-4 space-y-3">
              <Skeleton className="h-6 w-36" />
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </Card>
          ) : sourcesQuery.isError ? (
            <ErrorState
              error={sourcesQuery.error}
              onRetry={() => void sourcesQuery.refetch()}
            />
          ) : sources.length === 0 ? (
            <Card className="rounded-xl shadow-2xs">
              <CardContent className="py-12">
                <EmptyState
                  icon={FileText}
                  title={
                    searchQuery.trim()
                      ? "Không tìm thấy tài liệu phù hợp"
                      : "Chưa có tài liệu nào"
                  }
                  description={
                    searchQuery.trim()
                      ? `Không tìm thấy tài liệu nào khớp với từ khóa "${searchQuery}".`
                      : "Tải lên tệp PDF hoặc DOCX đầu tiên để bắt đầu lưu trữ vào bộ sưu tập này."
                  }
                  action={
                    canManage && !searchQuery.trim()
                      ? {
                          label: "Tải lên tài liệu ngay",
                          onClick: () => setUploadOpen(true),
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
                      <TableHead className="w-[30%]">
                        Tiêu đề tài liệu
                      </TableHead>
                      <TableHead className="w-[20%]">Tên tệp gốc</TableHead>
                      <TableHead className="w-[12%]">Định dạng</TableHead>
                      <TableHead className="w-[10%]">Dung lượng</TableHead>
                      <TableHead className="w-[10%] text-center">
                        Phiên bản
                      </TableHead>
                      <TableHead className="w-[10%]">Trạng thái</TableHead>
                      <TableHead className="w-[8%] text-right">
                        Thao tác
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sources.map((source) => (
                      <TableRow key={source.id} className="group">
                        <TableCell>
                          <Link
                            to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId"
                            search={
                              sourceAction === "ocr"
                                ? { tab: "ocr", subTab: "runs" }
                                : {}
                            }
                            params={{
                              workspaceId,
                              collectionId,
                              sourceId: source.id,
                            }}
                            className="font-medium text-foreground hover:text-primary transition-colors flex items-center gap-1.5"
                          >
                            <FileText className="size-4 shrink-0 text-muted-foreground group-hover:text-primary transition-colors" />
                            <span className="truncate">{source.title}</span>
                          </Link>
                        </TableCell>

                        <TableCell
                          className="text-xs text-muted-foreground font-mono truncate max-w-[180px]"
                          title={source.file_name}
                        >
                          {source.file_name}
                        </TableCell>

                        <TableCell>
                          {isPdf(source.content_type, source.file_name) ? (
                            <Badge
                              variant="info"
                              className="text-[11px] font-mono"
                            >
                              PDF
                            </Badge>
                          ) : isDocx(source.content_type, source.file_name) ? (
                            <Badge
                              variant="secondary"
                              className="text-[11px] font-mono"
                            >
                              DOCX
                            </Badge>
                          ) : (
                            <Badge
                              variant="outline"
                              className="text-[11px] font-mono"
                            >
                              Khác
                            </Badge>
                          )}
                        </TableCell>

                        <TableCell className="text-xs font-mono text-muted-foreground">
                          {formatBytes(source.size_bytes)}
                        </TableCell>

                        <TableCell className="text-center">
                          <Badge
                            variant="outline"
                            className="font-mono text-xs"
                          >
                            v{source.current_revision_no}
                          </Badge>
                        </TableCell>

                        <TableCell>
                          <Badge variant="success" className="text-[11px]">
                            {formatSourceStatus(source.status)}
                          </Badge>
                        </TableCell>

                        <TableCell className="text-right">
                          <Button
                            asChild
                            size="sm"
                            variant="ghost"
                            className="size-7 p-0"
                          >
                            <Link
                              to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId"
                              search={
                                sourceAction === "ocr"
                                  ? { tab: "ocr", subTab: "runs" }
                                  : {}
                              }
                              params={{
                                workspaceId,
                                collectionId,
                                sourceId: source.id,
                              }}
                              title="Xem chi tiết nguồn tài liệu"
                            >
                              <ChevronRight className="size-3.5 text-muted-foreground" />
                              <span className="sr-only">Chi tiết</span>
                            </Link>
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Mobile Card View */}
              <div className="divide-y sm:hidden">
                {sources.map((source) => (
                  <div key={source.id} className="p-4 space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <Link
                        to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId"
                        search={
                          sourceAction === "ocr"
                            ? { tab: "ocr", subTab: "runs" }
                            : {}
                        }
                        params={{
                          workspaceId,
                          collectionId,
                          sourceId: source.id,
                        }}
                        className="font-medium text-sm text-foreground hover:text-primary transition-colors flex items-center gap-1.5"
                      >
                        <FileText className="size-4 shrink-0 text-primary" />
                        <span>{source.title}</span>
                      </Link>

                      <Badge
                        variant="outline"
                        className="font-mono text-xs shrink-0"
                      >
                        v{source.current_revision_no}
                      </Badge>
                    </div>

                    <p className="text-xs text-muted-foreground font-mono truncate">
                      {source.file_name} · {formatBytes(source.size_bytes)}
                    </p>

                    <div className="flex items-center justify-between pt-1 border-t text-[11px]">
                      <Badge variant="success" className="text-[10px]">
                        {formatSourceStatus(source.status)}
                      </Badge>

                      <Button
                        asChild
                        size="sm"
                        variant="outline"
                        className="h-6 px-2 text-[11px]"
                      >
                        <Link
                          to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId"
                          search={
                            sourceAction === "ocr"
                              ? { tab: "ocr", subTab: "runs" }
                              : {}
                          }
                          params={{
                            workspaceId,
                            collectionId,
                            sourceId: source.id,
                          }}
                        >
                          Chi tiết
                          <ChevronRight className="size-3 ml-0.5" />
                        </Link>
                      </Button>
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
        </TabsContent>

        <TabsContent value="compilations" className="space-y-3 m-0">
          <CompilationRunsList
            page={page}
            pageSize={pageSize}
            onPageChange={onPageChange}
            onPageSizeChange={onPageSizeChange}
            workspaceId={workspaceId}
            collectionId={collectionId}
            canManage={canManage}
            onOpenCreateDialog={() => setCompilationOpen(true)}
          />
        </TabsContent>

        <TabsContent value="documents" className="space-y-3 m-0">
          <CompiledDocumentsList
            page={page}
            pageSize={pageSize}
            onPageChange={onPageChange}
            onPageSizeChange={onPageSizeChange}
            workspaceId={workspaceId}
            collectionId={collectionId}
            canRegister={canRegister}
            onOpenCompilationTab={() => {
              setActiveTab("compilations");
              onTabChange?.("compilations");
            }}
          />
        </TabsContent>

        <TabsContent value="index" className="space-y-3 m-0">
          {canManage ? (
            <Button asChild variant="outline" size="sm">
              <Link
                to="/workspaces/$workspaceId/collections/$collectionId/evaluations"
                params={{ workspaceId, collectionId }}
                search={{ page: 1 }}
              >
                Đánh giá RAG
              </Link>
            </Button>
          ) : null}
          <IndexPanel
            page={page}
            pageSize={pageSize}
            onPageChange={onPageChange}
            onPageSizeChange={onPageSizeChange}
            workspaceId={workspaceId}
            collectionId={collectionId}
            canManage={canManage}
            role={role}
          />
        </TabsContent>
      </Tabs>

      {/* Edit Collection Dialog */}
      <CollectionFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        workspaceId={workspaceId}
        collection={collection}
      />

      {/* Upload Source Dialog */}
      <SourceUploadDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        workspaceId={workspaceId}
        collectionId={collectionId}
        onSuccess={(sourceId) => {
          void navigate({
            to: "/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId",
            params: { workspaceId, collectionId, sourceId },
            search:
              sourceAction === "ocr" ? { tab: "ocr", subTab: "runs" } : {},
          });
        }}
      />

      {/* Compilation Dialog */}
      <CompilationDialog
        isOpen={compilationOpen}
        onClose={() => setCompilationOpen(false)}
        workspaceId={workspaceId}
        collectionId={collectionId}
      />
    </div>
  );
}
