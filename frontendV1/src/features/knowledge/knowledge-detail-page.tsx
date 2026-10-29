import { Link, useNavigate } from "@tanstack/react-router";
import {
  Archive,
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  FileSpreadsheet,
  FileText,
  FileUp,
  Folder,
  FolderOpen,
  FolderPlus,
  HardDrive,
  Loader2,
  Pencil,
  Play,
  Settings2,
  Trash2,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { DebouncedSearchInput } from "@/components/admin/debounced-search-input";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
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
import {
  type ViewMode,
  ViewModeToggle,
} from "@/components/ui/view-mode-toggle";
import { CollectionFormDialog } from "@/features/knowledge/collection-form-dialog";
import { ExtractDocumentDialog } from "@/features/knowledge/extract-document-dialog";
import { FolderDeleteDialog } from "@/features/knowledge/folder-delete-dialog";
import { FolderFormDialog } from "@/features/knowledge/folder-form-dialog";
import { FolderMoveDialog } from "@/features/knowledge/folder-move-dialog";
import { FolderTreePanel } from "@/features/knowledge/folder-tree-panel";
import { canManageKnowledge } from "@/features/knowledge/permissions";
import {
  useCollectionQuery,
  useFoldersQuery,
  useSourcesQuery,
} from "@/features/knowledge/queries";
import {
  formatBytes,
  formatProcessingStatus,
  isDocx,
  isPdf,
} from "@/features/knowledge/schemas";
import { SourceActions } from "@/features/knowledge/source-actions";
import { SourceRenameDialog } from "@/features/knowledge/source-rename-dialog";
import { SourceUploadDialog } from "@/features/knowledge/source-upload-dialog";
import type {
  FolderBreadcrumbItem,
  KBFolder,
  KBSource,
} from "@/features/knowledge/types";
import { LifecycleActionDialog } from "@/features/lifecycle/action-dialog";
import { canLifecycleAction } from "@/features/lifecycle/permissions";
import type { LifecycleOperation } from "@/features/lifecycle/types";
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";
import { formatDateTimeValue } from "@/lib/date-utils";
import { cn } from "@/lib/utils";

export type KnowledgeStage =
  | "files"
  | "ocr"
  | "compiler"
  | "publication"
  | "serving";

export function KnowledgeDetailPage({
  workspaceId,
  knowledgeId,
  page = 1,
  pageSize = 20,
  activeStage = "files",
  selectedSourceId: _selectedSourceId,
  onPageChange,
  onPageSizeChange,
  onStageChange: _onStageChange,
  onSelectSourceId: _onSelectSourceId,
}: {
  workspaceId: string;
  knowledgeId: string;
  page?: number;
  pageSize?: number;
  activeStage?: KnowledgeStage;
  selectedSourceId?: string | null;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  onStageChange?: (stage: KnowledgeStage) => void;
  onSelectSourceId?: (sourceId: string | null) => void;
}) {
  const navigate = useNavigate();

  // Queries
  const collectionQuery = useCollectionQuery(workspaceId, knowledgeId);
  const foldersQuery = useFoldersQuery(workspaceId, knowledgeId);
  const { role, isPending: rolePending } = useCallerWorkspaceRole(workspaceId);

  const collection = collectionQuery.data;
  const folders = foldersQuery.data ?? [];
  const canManage = !rolePending && canManageKnowledge(role);

  // Folder Explorer State
  const [currentFolderId, setCurrentFolderId] = useState<string | null>(null);
  const [allFoldersActive, setAllFoldersActive] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");

  // Dialog States
  const [uploadOpen, setUploadOpen] = useState(false);
  const [extractDialogOpen, setExtractDialogOpen] = useState(false);
  const [editCollectionOpen, setEditCollectionOpen] = useState(false);
  const [collectionLifecycleOp, setCollectionLifecycleOp] =
    useState<LifecycleOperation | null>(null);
  const [sourceLifecycle, setSourceLifecycle] = useState<{
    source: KBSource; operation: LifecycleOperation;
  } | null>(null);

  const [folderFormOpen, setFolderFormOpen] = useState(false);
  const [folderToEdit, setFolderToEdit] = useState<KBFolder | null>(null);
  const [folderParentForCreate, setFolderParentForCreate] = useState<{
    id: string | null;
    name: string;
  }>({ id: null, name: "Gốc kho tri thức" });

  const [folderDeleteOpen, setFolderDeleteOpen] = useState(false);
  const [folderToDelete, setFolderToDelete] = useState<KBFolder | null>(null);

  const [moveDialogOpen, setMoveDialogOpen] = useState(false);
  const [itemToMove, setItemToMove] = useState<{
    type: "folder" | "source";
    id: string;
    title: string;
    currentFolderId?: string | null;
  } | null>(null);

  const [renameSourceOpen, setRenameSourceOpen] = useState(false);
  const [sourceToRename, setSourceToRename] = useState<KBSource | null>(null);

  // Current Folder Object
  const currentFolder = useMemo(
    () =>
      currentFolderId
        ? (folders.find((f) => f.id === currentFolderId) ?? null)
        : null,
    [folders, currentFolderId],
  );

  // Direct subfolders of current folder
  const directSubfolders = useMemo(() => {
    if (allFoldersActive) return [];
    return folders.filter((f) => f.parent_id === (currentFolderId ?? null));
  }, [folders, currentFolderId, allFoldersActive]);

  // Breadcrumbs path of current folder
  const folderBreadcrumbs = useMemo<FolderBreadcrumbItem[]>(() => {
    if (allFoldersActive || !currentFolderId) return [];
    const trail: FolderBreadcrumbItem[] = [];
    let cur: KBFolder | undefined = folders.find(
      (f) => f.id === currentFolderId,
    );
    const visited = new Set<string>();
    while (cur && !visited.has(cur.id)) {
      visited.add(cur.id);
      trail.unshift({ id: cur.id, name: cur.name });
      cur = cur.parent_id
        ? folders.find((f) => f.id === cur?.parent_id)
        : undefined;
    }
    return trail;
  }, [folders, currentFolderId, allFoldersActive]);

  // Sources Query in current folder
  const sourcesQuery = useSourcesQuery(workspaceId, knowledgeId, {
    page,
    pageSize,
    folderId: allFoldersActive ? undefined : (currentFolderId ?? null),
    allFolders: allFoldersActive,
  });

  const rawSources = sourcesQuery.data?.items ?? [];
  const total = sourcesQuery.data?.meta.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  // Client search filter
  const sources = useMemo(() => {
    if (!searchQuery.trim()) return rawSources;
    const q = searchQuery.toLowerCase().trim();
    return rawSources.filter(
      (s) =>
        s.title.toLowerCase().includes(q) ||
        s.file_name.toLowerCase().includes(q),
    );
  }, [rawSources, searchQuery]);

  const rootSourceCount = useMemo(() => {
    return Math.max(
      0,
      (collection?.source_count ?? 0) -
        folders.reduce((sum, folder) => sum + folder.source_count, 0),
    );
  }, [folders, collection]);

  if (collectionQuery.isLoading) {
    return (
      <div className="space-y-4 p-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-20 w-full rounded-xl" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  if (collectionQuery.isError || !collection) {
    return (
      <div className="space-y-4">
        <Button asChild size="sm" variant="ghost">
          <Link
            to="/workspaces/$workspaceId/knowledge"
            params={{ workspaceId }}
            search={{ page: 1, pageSize: 20 }}
          >
            <ArrowLeft className="size-4 mr-1" />
            Về danh sách kho tri thức
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
    <div className="min-w-0 space-y-6">
      {/* 1. Header with Breadcrumb, Name & Action Toolbar: Tải tài liệu · Bóc tách · Quản lý */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b pb-4">
        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Link
              to="/workspaces/$workspaceId/knowledge"
              params={{ workspaceId }}
              search={{ page: 1, pageSize: 20 }}
              className="hover:text-foreground transition-colors flex items-center gap-1"
            >
              <ArrowLeft className="size-3" />
              <span>Kho tri thức</span>
            </Link>
            <ChevronRight className="size-3 text-muted-foreground/50" />
            <span className="font-medium text-foreground truncate max-w-[240px]">
              {collection.name}
            </span>
          </div>

          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold tracking-tight text-foreground truncate">
              {collection.name}
            </h1>
            <Badge variant="secondary" className="text-xs font-normal shrink-0">
              {collection.source_count} tài liệu
            </Badge>
          </div>
          {collection.description && (
            <p className="text-xs text-muted-foreground line-clamp-1">
              {collection.description}
            </p>
          )}
        </div>

        {/* Thanh thao tác chính: Tải tài liệu · Bóc tách · Quản lý */}
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
          {/* Nút 1: Tải tài liệu */}
          <Button
            size="sm"
            className="gap-1.5 text-xs h-9 shadow-xs"
            disabled={!canManage || foldersQuery.isError}
            onClick={() => setUploadOpen(true)}
          >
            <FileUp className="size-4" />
            <span>Tải tài liệu</span>
          </Button>

          {/* Nút 2: Bóc tách */}
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5 text-xs h-9"
            disabled={!canManage || collection.source_count === 0}
            onClick={() => setExtractDialogOpen(true)}
          >
            <Play className="size-3.5 text-primary" />
            <span>Bóc tách</span>
          </Button>

          {/* Nút 3: Quản lý (Gộp menu Sửa kho, Tạo thư mục, Lưu trữ, Xóa kho) */}
          {canManage && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5 text-xs h-9 text-muted-foreground hover:text-foreground"
                >
                  <Settings2 className="size-3.5" />
                  <span>Quản lý</span>
                  <ChevronDown className="size-3 opacity-60" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-52 text-xs">
                <DropdownMenuItem
                  className="gap-2"
                  onClick={() => setEditCollectionOpen(true)}
                >
                  <Pencil className="size-3.5 text-muted-foreground" />
                  <span>Sửa thông tin kho</span>
                </DropdownMenuItem>
                <DropdownMenuItem
                  className="gap-2"
                  onClick={() => {
                    setFolderToEdit(null);
                    setFolderParentForCreate({
                      id: currentFolderId,
                      name: currentFolder?.name ?? "Gốc kho tri thức",
                    });
                    setFolderFormOpen(true);
                  }}
                >
                  <FolderPlus className="size-3.5 text-muted-foreground" />
                  <span>Tạo thư mục mới</span>
                </DropdownMenuItem>

                {canLifecycleAction(role, "collection", "archive") && (
                  <DropdownMenuItem
                    className="gap-2"
                    onClick={() => setCollectionLifecycleOp("archive")}
                  >
                    <Archive className="size-3.5 text-muted-foreground" />
                    <span>Lưu trữ kho</span>
                  </DropdownMenuItem>
                )}

                {canLifecycleAction(role, "collection", "delete") && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      className="gap-2 text-destructive focus:text-destructive"
                      onClick={() => setCollectionLifecycleOp("delete")}
                    >
                      <Trash2 className="size-3.5" />
                      <span>Xóa kho tri thức</span>
                    </DropdownMenuItem>
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          )}

          {collectionLifecycleOp && (
            <LifecycleActionDialog
              workspaceId={workspaceId}
              target={{
                kind: "collection",
                resource_id: collection.id,
                action: collectionLifecycleOp,
              }}
              label={collection.name}
              onClose={() => setCollectionLifecycleOp(null)}
            />
          )}
        </div>
      </div>

      {/* 2. KHU VỰC QUẢN LÝ TÀI LIỆU (Cột trái: Cây thư mục | Vùng phải: Danh sách tệp) */}
      {activeStage === "files" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 min-h-[540px]">
          {/* CỘT TRÁI (3 cols): Cây thư mục */}
          <div className="lg:col-span-3">
            <FolderTreePanel
              folders={folders}
              currentFolderId={currentFolderId}
              allFoldersActive={allFoldersActive}
              canManage={canManage}
              rootSourceCount={rootSourceCount}
              totalSourceCount={collection.source_count}
              onSelectFolder={(folderId, all) => {
                setCurrentFolderId(folderId);
                setAllFoldersActive(Boolean(all));
                onPageChange(1);
              }}
              onCreateFolder={() => {
                setFolderToEdit(null);
                setFolderParentForCreate({
                  id: null,
                  name: "Gốc kho tri thức",
                });
                setFolderFormOpen(true);
              }}
              onCreateSubfolder={(parent) => {
                setFolderToEdit(null);
                setFolderParentForCreate({ id: parent.id, name: parent.name });
                setFolderFormOpen(true);
              }}
              onRenameFolder={(f) => {
                setFolderToEdit(f);
                setFolderFormOpen(true);
              }}
              onMoveFolder={(f) => {
                setItemToMove({
                  type: "folder",
                  id: f.id,
                  title: f.name,
                  currentFolderId: f.parent_id,
                });
                setMoveDialogOpen(true);
              }}
              onDeleteFolder={(f) => {
                setFolderToDelete(f);
                setFolderDeleteOpen(true);
              }}
            />
          </div>

          {/* VÙNG PHẢI (9 cols): Danh sách tài liệu */}
          <div className="lg:col-span-9 space-y-4">
            {/* Toolbar phẳng: Breadcrumb đường dẫn thư mục hiện tại, Tìm kiếm & Chế độ xem */}
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between pb-3 border-b border-border/60">
              {/* Breadcrumb đường dẫn thư mục */}
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground flex-wrap">
                <button
                  type="button"
                  onClick={() => {
                    setCurrentFolderId(null);
                    setAllFoldersActive(false);
                    onPageChange(1);
                  }}
                  className={cn(
                    "hover:text-foreground font-medium flex items-center gap-1 transition-colors",
                    !currentFolderId && !allFoldersActive
                      ? "text-primary font-semibold"
                      : "",
                  )}
                >
                  <HardDrive className="size-3.5 text-primary" />
                  <span>Gốc kho</span>
                </button>

                {allFoldersActive ? (
                  <>
                    <ChevronRight className="size-3 text-muted-foreground/40" />
                    <span className="font-semibold text-foreground">
                      Tất cả tài liệu
                    </span>
                  </>
                ) : (
                  folderBreadcrumbs.map((bc, idx) => {
                    const isLast = idx === folderBreadcrumbs.length - 1;
                    return (
                      <div key={bc.id} className="flex items-center gap-1.5">
                        <ChevronRight className="size-3 text-muted-foreground/40" />
                        <button
                          type="button"
                          onClick={() => {
                            setCurrentFolderId(bc.id);
                            setAllFoldersActive(false);
                            onPageChange(1);
                          }}
                          className={cn(
                            "hover:text-foreground transition-colors",
                            isLast ? "font-semibold text-foreground" : "",
                          )}
                        >
                          {bc.name}
                        </button>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Tìm kiếm & Chuyển chế độ xem */}
              <div className="flex items-center gap-2">
                <div className="w-full sm:w-64">
                  <DebouncedSearchInput
                    value={searchQuery}
                    onChange={setSearchQuery}
                    placeholder="Tìm tài liệu..."
                    className="text-xs h-9"
                  />
                </div>

                <ViewModeToggle value={viewMode} onChange={setViewMode} />
              </div>
            </div>

            {foldersQuery.isError && (
              <ErrorState
                error={foldersQuery.error}
                onRetry={() => void foldersQuery.refetch()}
              />
            )}

            {/* Danh sách Thư mục con (nếu có) */}
            {!allFoldersActive && directSubfolders.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                  <FolderOpen className="size-3.5 text-amber-500" />
                  <span>Thư mục con ({directSubfolders.length})</span>
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-2.5">
                  {directSubfolders.map((f) => (
                    <Card
                      key={f.id}
                      onClick={() => {
                        setCurrentFolderId(f.id);
                        setAllFoldersActive(false);
                        onPageChange(1);
                      }}
                      className="p-3 rounded-xl border-border/80 hover:border-primary/60 hover:bg-muted/20 transition-all cursor-pointer group shadow-2xs"
                    >
                      <div className="flex items-center gap-2.5">
                        <Folder className="size-7 text-amber-500/90 group-hover:text-amber-600 transition-colors shrink-0" />
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-semibold text-foreground truncate group-hover:text-primary transition-colors">
                            {f.name}
                          </p>
                          <p className="text-[11px] text-muted-foreground">
                            {f.source_count} tệp · {f.subfolder_count} thư mục
                            con
                          </p>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {/* Danh sách Tệp (Sources) */}
            {sourcesQuery.isLoading ? (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <Skeleton className="h-28 w-full rounded-xl" />
                <Skeleton className="h-28 w-full rounded-xl" />
                <Skeleton className="h-28 w-full rounded-xl" />
              </div>
            ) : sourcesQuery.isError ? (
              <ErrorState
                error={sourcesQuery.error}
                onRetry={() => void sourcesQuery.refetch()}
              />
            ) : sources.length === 0 ? (
              <div className="rounded-xl border border-dashed p-10 text-center space-y-3 bg-muted/10">
                <div className="flex size-12 items-center justify-center rounded-2xl bg-muted mx-auto text-muted-foreground">
                  <FileText className="size-6" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-foreground">
                    {searchQuery
                      ? "Không tìm thấy tài liệu phù hợp"
                      : "Chưa có tài liệu nào trong thư mục này"}
                  </p>
                  <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                    {searchQuery
                      ? "Hãy thử tìm kiếm với từ khóa khác."
                      : "Tải tài liệu PDF hoặc Word (.docx) vào kho để lưu trữ an toàn và bóc tách nội dung."}
                  </p>
                </div>
                {canManage && !searchQuery && (
                  <Button
                    size="sm"
                    className="gap-1.5 text-xs shadow-xs"
                    onClick={() => setUploadOpen(true)}
                  >
                    <FileUp className="size-3.5" />
                    <span>Tải tài liệu vào đây</span>
                  </Button>
                )}
              </div>
            ) : viewMode === "grid" ? (
              /* Chế độ Grid Card */
              <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
                {sources.map((s) => {
                  const pdf = isPdf(s.content_type, s.file_name);
                  const docx = isDocx(s.content_type, s.file_name);
                  const formatLabel = pdf ? "PDF" : docx ? "DOCX" : "XLSX";
                  const statusInfo = formatProcessingStatus(s.processing);

                  return (
                    <Card
                      key={s.id}
                      className="p-4 rounded-xl border-border/70 hover:border-primary/40 hover:shadow-xs transition-all group relative flex flex-col justify-between"
                    >
                      <div className="space-y-2.5">
                        <div className="flex items-start gap-2.5">
                          <div
                            className={cn(
                              "flex size-9 shrink-0 items-center justify-center rounded-lg border",
                              pdf
                                ? "bg-rose-50 text-rose-600 border-rose-200 dark:bg-rose-950/40 dark:border-rose-800"
                                : docx
                                  ? "bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-950/40 dark:border-blue-800"
                                  : "bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-950/40 dark:border-emerald-800",
                            )}
                          >
                            {pdf || docx ? (
                              <FileText className="size-4" />
                            ) : (
                              <FileSpreadsheet className="size-4" />
                            )}
                          </div>

                          <div className="min-w-0 flex-1">
                            <h4 className="text-xs font-semibold text-foreground line-clamp-1 group-hover:text-primary transition-colors">
                              <Link
                                to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId"
                                params={{
                                  workspaceId,
                                  collectionId: knowledgeId,
                                  sourceId: s.id,
                                }}
                                title={s.title}
                              >
                                {s.title}
                              </Link>
                            </h4>
                            <p className="text-[11px] text-muted-foreground truncate mt-0.5">
                              <span className="font-mono">{formatLabel}</span>
                              <span> · </span>
                              <span className="font-mono">
                                v{s.current_revision_no}
                              </span>
                              <span> · </span>
                              <span>{formatBytes(s.size_bytes)}</span>
                            </p>
                          </div>

                          <SourceActions
                            workspaceId={workspaceId}
                            collectionId={knowledgeId}
                            source={s}
                            onLifecycle={(operation, source) => setSourceLifecycle({ source, operation })}
                            role={role}
                            canManage={canManage}
                            onOcr={() => {
                              void navigate({
                                to: "/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId",
                                params: {
                                  workspaceId,
                                  collectionId: knowledgeId,
                                  sourceId: s.id,
                                },
                              });
                            }}
                            onRename={() => {
                              setSourceToRename(s);
                              setRenameSourceOpen(true);
                            }}
                            onMove={() => {
                              setItemToMove({
                                type: "source",
                                id: s.id,
                                title: s.title,
                                currentFolderId: s.folder_id,
                              });
                              setMoveDialogOpen(true);
                            }}
                          />
                        </div>
                      </div>

                      {/* Footer card thanh lịch: Trạng thái & Link điều hướng gọn */}
                      <div className="pt-3 mt-3 border-t border-border/50 flex items-center justify-between gap-2 text-[11px]">
                        <Badge
                          variant={statusInfo.variant}
                          className="text-[10px] py-0 px-1.5 font-normal truncate max-w-[65%]"
                        >
                          {statusInfo.status === "running" ? (
                            <Loader2 className="size-3 animate-spin mr-1 inline" />
                          ) : null}
                          {statusInfo.label}
                        </Badge>

                        <Link
                          to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId"
                          params={{
                            workspaceId,
                            collectionId: knowledgeId,
                            sourceId: s.id,
                          }}
                          className="flex items-center gap-0.5 text-primary font-medium hover:underline shrink-0"
                        >
                          <span>
                            {statusInfo.status === "completed"
                              ? "Đối chiếu"
                              : statusInfo.status === "running"
                                ? "Theo dõi"
                                : "Chi tiết"}
                          </span>
                          <ChevronRight className="size-3" />
                        </Link>
                      </div>
                    </Card>
                  );
                })}
              </div>
            ) : (
              /* Chế độ Bảng Table */
              <Card className="rounded-xl shadow-2xs border-border/70 overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/40">
                      <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3">
                        Tên tài liệu
                      </TableHead>
                      <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3">
                        Định dạng
                      </TableHead>
                      <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3">
                        Kích thước
                      </TableHead>
                      <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3">
                        Phiên bản
                      </TableHead>
                      <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3">
                        Trạng thái bóc tách
                      </TableHead>
                      <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3">
                        Cập nhật
                      </TableHead>
                      <TableHead className="w-[60px] text-right font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sources.map((s) => {
                      const pdf = isPdf(s.content_type, s.file_name);
                      const docx = isDocx(s.content_type, s.file_name);
                      const statusInfo = formatProcessingStatus(s.processing);

                      return (
                        <TableRow
                          key={s.id}
                          className="group hover:bg-muted/40"
                        >
                          <TableCell className="font-medium text-xs text-foreground max-w-xs truncate">
                            <Link
                              to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId"
                              params={{
                                workspaceId,
                                collectionId: knowledgeId,
                                sourceId: s.id,
                              }}
                              className="flex items-center gap-2 hover:text-primary transition-colors"
                            >
                              {pdf ? (
                                <FileText className="size-4 text-rose-500 shrink-0" />
                              ) : docx ? (
                                <FileText className="size-4 text-blue-500 shrink-0" />
                              ) : (
                                <FileSpreadsheet className="size-4 text-emerald-500 shrink-0" />
                              )}
                              <span className="truncate">{s.title}</span>
                            </Link>
                          </TableCell>
                          <TableCell className="text-xs uppercase text-muted-foreground font-mono">
                            {pdf ? "PDF" : docx ? "DOCX" : "XLSX"}
                          </TableCell>
                          <TableCell className="text-xs font-mono text-muted-foreground">
                            {formatBytes(s.size_bytes)}
                          </TableCell>
                          <TableCell className="text-xs font-mono">
                            v{s.current_revision_no}
                          </TableCell>
                          <TableCell className="text-xs">
                            <Badge
                              variant={statusInfo.variant}
                              className="text-[10px] font-normal"
                            >
                              {statusInfo.status === "running" ? (
                                <Loader2 className="size-3 animate-spin mr-1 inline" />
                              ) : null}
                              {statusInfo.label}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                            {formatDateTimeValue(s.updated_at || s.created_at)}
                          </TableCell>
                          <TableCell className="text-right">
                            <SourceActions
                              workspaceId={workspaceId}
                              collectionId={knowledgeId}
                              source={s}
                              onLifecycle={(operation, source) => setSourceLifecycle({ source, operation })}
                              role={role}
                              canManage={canManage}
                              onOcr={() => {
                                void navigate({
                                  to: "/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId",
                                  params: {
                                    workspaceId,
                                    collectionId: knowledgeId,
                                    sourceId: s.id,
                                  },
                                });
                              }}
                              onRename={() => {
                                setSourceToRename(s);
                                setRenameSourceOpen(true);
                              }}
                              onMove={() => {
                                setItemToMove({
                                  type: "source",
                                  id: s.id,
                                  title: s.title,
                                  currentFolderId: s.folder_id,
                                });
                                setMoveDialogOpen(true);
                              }}
                            />
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </Card>
            )}

            {/* Phân trang */}
            {total > 0 && (
              <DataTablePagination
                page={page}
                pageSize={pageSize}
                pageCount={pageCount}
                total={total}
                onPageChange={onPageChange}
                onPageSizeChange={onPageSizeChange}
              />
            )}
          </div>
        </div>
      )}

      {/* Legacy Stages Fallback (đáp ứng điều hướng link /compilations, /documents, /search) */}
      {activeStage === "compiler" && (
        <div className="rounded-xl border border-dashed p-12 text-center space-y-3 bg-muted/10">
          <Button asChild size="sm">
            <Link
              to="/workspaces/$workspaceId/collections/$collectionId/compilations"
              params={{ workspaceId, collectionId: knowledgeId }}
              search={{ page: 1, pageSize: 20 }}
            >
              Mở biên soạn
            </Link>
          </Button>
        </div>
      )}

      {activeStage === "publication" && (
        <div className="rounded-xl border border-dashed p-12 text-center space-y-3 bg-muted/10">
          <Button asChild size="sm">
            <Link
              to="/workspaces/$workspaceId/collections/$collectionId/documents"
              params={{ workspaceId, collectionId: knowledgeId }}
              search={{ page: 1, pageSize: 20 }}
            >
              Mở xuất bản
            </Link>
          </Button>
        </div>
      )}

      {activeStage === "serving" && (
        <div className="rounded-xl border border-dashed p-12 text-center space-y-3 bg-muted/10">
          <Button asChild size="sm">
            <Link
              to="/workspaces/$workspaceId/collections/$collectionId/search"
              params={{ workspaceId, collectionId: knowledgeId }}
              search={{ page: 1, pageSize: 20 }}
            >
              Mở phục vụ AI
            </Link>
          </Button>
        </div>
      )}

      {/* 3. MODALS & DIALOGS */}
      {/* Upload Dialog: Nhận diện đúng kho và thư mục đang chọn */}
      <SourceUploadDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        workspaceId={workspaceId}
        collectionId={knowledgeId}
        folderId={currentFolderId}
        onSuccess={() => {
          void sourcesQuery.refetch();
          void collectionQuery.refetch();
        }}
      />
      {sourceLifecycle ? (
        <LifecycleActionDialog
          workspaceId={workspaceId}
          target={{ kind: "source", resource_id: sourceLifecycle.source.id, action: sourceLifecycle.operation }}
          label={sourceLifecycle.source.title}
          onClose={() => setSourceLifecycle(null)}
          onCompleted={() => {
            toast.success(sourceLifecycle.operation === "delete" ? "Đã xóa vĩnh viễn tài liệu." : "Đã lưu trữ tài liệu.");
            setSourceLifecycle(null);
            void sourcesQuery.refetch();
            void collectionQuery.refetch();
          }}
        />
      ) : null}

      {/* Quick Extract Dialog */}
      {extractDialogOpen && (
        <ExtractDocumentDialog
          open={extractDialogOpen}
          onOpenChange={setExtractDialogOpen}
          workspaceId={workspaceId}
          collectionId={knowledgeId}
        />
      )}

      {/* Tạo / Sửa Thư mục */}
      <FolderFormDialog
        open={folderFormOpen}
        onOpenChange={setFolderFormOpen}
        workspaceId={workspaceId}
        collectionId={knowledgeId}
        parentFolderId={folderParentForCreate.id}
        parentFolderName={folderParentForCreate.name}
        folderToEdit={folderToEdit}
        onSuccess={() => {
          void foldersQuery.refetch();
        }}
      />

      {/* Xóa Thư mục */}
      <FolderDeleteDialog
        open={folderDeleteOpen}
        onOpenChange={setFolderDeleteOpen}
        workspaceId={workspaceId}
        collectionId={knowledgeId}
        folder={folderToDelete}
        onSuccess={() => {
          if (folderToDelete?.id === currentFolderId) {
            setCurrentFolderId(null);
          }
          void foldersQuery.refetch();
          void sourcesQuery.refetch();
        }}
      />

      {/* Di chuyển Tệp hoặc Thư mục */}
      {itemToMove && (
        <FolderMoveDialog
          open={moveDialogOpen}
          onOpenChange={(open) => {
            setMoveDialogOpen(open);
            if (!open) setItemToMove(null);
          }}
          workspaceId={workspaceId}
          collectionId={knowledgeId}
          itemType={itemToMove.type}
          itemId={itemToMove.id}
          itemTitle={itemToMove.title}
          currentFolderId={itemToMove.currentFolderId}
          onSuccess={() => {
            void foldersQuery.refetch();
            void sourcesQuery.refetch();
          }}
        />
      )}

      {/* Đổi tên Tệp */}
      <SourceRenameDialog
        open={renameSourceOpen}
        onOpenChange={(open) => {
          setRenameSourceOpen(open);
          if (!open) setSourceToRename(null);
        }}
        workspaceId={workspaceId}
        collectionId={knowledgeId}
        source={sourceToRename}
        onSuccess={() => {
          void sourcesQuery.refetch();
        }}
      />

      {/* Sửa Thông tin Kho */}
      <CollectionFormDialog
        open={editCollectionOpen}
        onOpenChange={setEditCollectionOpen}
        workspaceId={workspaceId}
        collection={collection}
        onSuccess={() => {
          void collectionQuery.refetch();
        }}
      />
    </div>
  );
}
