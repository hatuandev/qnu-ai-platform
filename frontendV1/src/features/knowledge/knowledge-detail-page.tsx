import { Link, useNavigate } from "@tanstack/react-router";
import {
  Archive,
  ArrowLeft,
  BookMarked,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  FileSpreadsheet,
  FileText,
  FileUp,
  Folder,
  FolderOpen,
  FolderPlus,
  Gauge,
  HardDrive,
  Layers,
  MessageSquare,
  MoreVertical,
  Pencil,
  Play,
  RotateCcw,
  Settings2,
  SlidersHorizontal,
  Trash2,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { DataTablePagination } from "@/components/admin/data-table/data-table-pagination";
import { DebouncedSearchInput } from "@/components/admin/debounced-search-input";
import { EmptyState } from "@/components/admin/empty-state";
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
import { CompilationDialog } from "@/features/knowledge/compilation-dialog";
import { CompilationRunsList } from "@/features/knowledge/compilation-runs-list";
import { CompiledDocumentsList } from "@/features/knowledge/compiled-documents-list";
import { ExtractDocumentDialog } from "@/features/knowledge/extract-document-dialog";
import { FolderDeleteDialog } from "@/features/knowledge/folder-delete-dialog";
import { FolderFormDialog } from "@/features/knowledge/folder-form-dialog";
import { FolderMoveDialog } from "@/features/knowledge/folder-move-dialog";
import { IndexPanel } from "@/features/knowledge/index-panel";
import {
  canCreateOrEditCompilation,
  canManageKnowledge,
  canRegisterCompiledDocument,
} from "@/features/knowledge/permissions";
import { ProcessingProgress } from "@/features/knowledge/processing-progress";
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
import { PendingSourceDeletions } from "@/features/lifecycle/pending-source-deletions";
import {
  canLifecycleAction,
  isLifecycleAdmin,
} from "@/features/lifecycle/permissions";
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
  onStageChange,
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
  const canCompile = !rolePending && canCreateOrEditCompilation(role);
  const canPublish = !rolePending && canRegisterCompiledDocument(role);

  // Folder Explorer State
  const [currentFolderId, setCurrentFolderId] = useState<string | null>(null);
  const [allFoldersActive, setAllFoldersActive] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");

  // Dialog States
  const [uploadOpen, setUploadOpen] = useState(false);
  const [extractDialogOpen, setExtractDialogOpen] = useState(false);
  const [compilationDialogOpen, setCompilationDialogOpen] = useState(false);
  const [editCollectionOpen, setEditCollectionOpen] = useState(false);
  const [collectionLifecycleOp, setCollectionLifecycleOp] =
    useState<LifecycleOperation | null>(null);
  const [sourceLifecycle, setSourceLifecycle] = useState<{
    source: KBSource;
    operation: LifecycleOperation;
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

  const parentFolder = useMemo(() => {
    if (!currentFolder || !currentFolder.parent_id) return null;
    return folders.find((f) => f.id === currentFolder.parent_id) ?? null;
  }, [currentFolder, folders]);

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
    <div className="min-w-0 space-y-4">
      {/* 1. Header tinh gọn tối đa: Tên kho · Giai đoạn · Thao tác chính */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-border/60 pb-3">
        {/* Bên trái: Breadcrumb quay lại + Tên kho + Badge đếm + Tab giai đoạn */}
        <div className="flex flex-wrap items-center gap-2.5 min-w-0">
          <Link
            to="/workspaces/$workspaceId/knowledge"
            params={{ workspaceId }}
            search={{ page: 1, pageSize: 20 }}
            className="hover:text-foreground text-muted-foreground transition-colors flex items-center gap-1 text-xs font-medium"
          >
            <ArrowLeft className="size-3.5" />
            <span>Kho tri thức</span>
          </Link>
          <ChevronRight className="size-3 text-muted-foreground/40" />
          <h1 className="text-base sm:text-lg font-bold tracking-tight text-foreground truncate max-w-[280px]">
            {collection.name}
          </h1>
          <Badge variant="secondary" className="font-normal text-[11px] h-5">
            {collection.source_count} tài liệu · {folders.length} thư mục
          </Badge>

          {/* Tab Giai đoạn (Tài liệu / Biên soạn / Phát hành) */}
          <div
            role="tablist"
            aria-label="Giai đoạn kho tri thức"
            className="inline-flex items-center gap-0.5 rounded-lg bg-muted/60 p-0.5 ml-2"
          >
            <button
              type="button"
              role="tab"
              aria-selected={activeStage === "files" || activeStage === "ocr"}
              onClick={() => onStageChange?.("files")}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                activeStage === "files" || activeStage === "ocr"
                  ? "bg-background text-foreground shadow-2xs font-semibold"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <FileText className="size-3" />
              <span>Tài liệu</span>
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeStage === "compiler"}
              onClick={() => onStageChange?.("compiler")}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                activeStage === "compiler"
                  ? "bg-background text-foreground shadow-2xs font-semibold"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <ClipboardList className="size-3" />
              <span>Biên soạn</span>
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeStage === "publication"}
              onClick={() => onStageChange?.("publication")}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                activeStage === "publication"
                  ? "bg-background text-foreground shadow-2xs font-semibold"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <BookMarked className="size-3" />
              <span>Phát hành</span>
            </button>
          </div>
        </div>

        {/* Bên phải: Nút hành động */}
        <div className="flex items-center gap-2 shrink-0">
          <Button
            size="sm"
            className="gap-1.5 shadow-xs text-xs h-8"
            disabled={!canManage || foldersQuery.isError}
            onClick={() => setUploadOpen(true)}
          >
            <FileUp className="size-3.5" />
            <span>Tải tài liệu</span>
          </Button>

          <Button
            size="sm"
            variant="outline"
            className="gap-1.5 shadow-xs text-xs h-8"
            disabled={!canManage || collection.source_count === 0}
            onClick={() => setExtractDialogOpen(true)}
          >
            <Play className="size-3 text-primary" />
            <span>Bóc tách</span>
          </Button>

          {canManage && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1 shadow-xs text-xs h-8 text-muted-foreground hover:text-foreground"
                >
                  <Settings2 className="size-3.5" />
                  <span className="hidden sm:inline">Quản lý</span>
                  <ChevronDown className="size-3 opacity-60" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56 text-xs">
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

                <DropdownMenuSeparator />

                <DropdownMenuItem asChild>
                  <Link
                    to="/workspaces/$workspaceId/collections/$collectionId/answers"
                    params={{ workspaceId, collectionId: knowledgeId }}
                    className="flex items-center gap-2"
                  >
                    <MessageSquare className="size-3.5 text-muted-foreground" />
                    <span>Hỏi đáp trên kho</span>
                  </Link>
                </DropdownMenuItem>

                <DropdownMenuItem asChild>
                  <Link
                    to="/workspaces/$workspaceId/collections/$collectionId/search"
                    params={{ workspaceId, collectionId: knowledgeId }}
                    search={{ page: 1, pageSize: 20 }}
                    className="flex items-center gap-2"
                  >
                    <SlidersHorizontal className="size-3.5 text-muted-foreground" />
                    <span>Quản trị chỉ mục</span>
                  </Link>
                </DropdownMenuItem>

                <DropdownMenuItem asChild>
                  <Link
                    to="/workspaces/$workspaceId/collections/$collectionId/evaluations"
                    params={{ workspaceId, collectionId: knowledgeId }}
                    search={{ page: 1 }}
                    className="flex items-center gap-2"
                  >
                    <Gauge className="size-3.5 text-muted-foreground" />
                    <span>Đánh giá RAG</span>
                  </Link>
                </DropdownMenuItem>

                {canLifecycleAction(role, "collection", "archive") && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      className="gap-2"
                      onClick={() => setCollectionLifecycleOp("archive")}
                    >
                      <Archive className="size-3.5 text-muted-foreground" />
                      <span>Lưu trữ kho</span>
                    </DropdownMenuItem>
                  </>
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
              onCompleted={() =>
                void navigate({
                  to: "/workspaces/$workspaceId/knowledge",
                  params: { workspaceId },
                  search: { page: 1, pageSize: 20 },
                })
              }
            />
          )}
        </div>
      </div>

      {/* 2. KHU VỰC KHÁM PHÁ THƯ MỤC & TÀI LIỆU (Google Drive Canvas — Toàn Chiều Rộng) */}
      {(activeStage === "files" || activeStage === "ocr") && (
        <div className="space-y-4">
          {/* Thanh Breadcrumb vị trí & Công cụ Lọc/Xem */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between pb-3 border-b border-border/60">
            {/* Đường dẫn Breadcrumb hiện tại */}
            <div className="flex items-center gap-1 text-xs text-muted-foreground flex-wrap min-w-0">
              {currentFolderId ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground gap-1 -ml-1 mr-1"
                  onClick={() => {
                    setCurrentFolderId(parentFolder ? parentFolder.id : null);
                    setAllFoldersActive(false);
                    onPageChange(1);
                  }}
                  title="Quay lại thư mục cấp trên"
                >
                  <ArrowLeft className="size-3.5" />
                  <span>Lên một cấp</span>
                </Button>
              ) : null}

              <button
                type="button"
                onClick={() => {
                  setCurrentFolderId(null);
                  setAllFoldersActive(false);
                  onPageChange(1);
                }}
                className={cn(
                  "hover:text-foreground font-medium flex items-center gap-1.5 transition-colors px-2 py-1 rounded-md",
                  !currentFolderId && !allFoldersActive
                    ? "bg-muted font-semibold text-foreground shadow-2xs"
                    : "text-muted-foreground",
                )}
              >
                <HardDrive className="size-3.5 text-primary" />
                <span>Gốc kho</span>
                <span className="text-[10px] text-muted-foreground/80 font-normal">
                  ({rootSourceCount})
                </span>
              </button>

              {allFoldersActive ? (
                <>
                  <ChevronRight className="size-3 text-muted-foreground/40" />
                  <span className="font-semibold text-foreground flex items-center gap-1 px-2 py-1 rounded-md bg-muted shadow-2xs">
                    <Layers className="size-3 text-muted-foreground" />
                    <span>Tất cả tài liệu</span>
                  </span>
                </>
              ) : (
                folderBreadcrumbs.map((bc, idx) => {
                  const isLast = idx === folderBreadcrumbs.length - 1;
                  return (
                    <div key={bc.id} className="flex items-center gap-1">
                      <ChevronRight className="size-3 text-muted-foreground/40" />
                      <button
                        type="button"
                        onClick={() => {
                          setCurrentFolderId(bc.id);
                          setAllFoldersActive(false);
                          onPageChange(1);
                        }}
                        className={cn(
                          "hover:text-foreground transition-colors flex items-center gap-1 px-2 py-1 rounded-md",
                          isLast
                            ? "bg-muted font-semibold text-foreground shadow-2xs"
                            : "text-muted-foreground",
                        )}
                      >
                        <Folder className="size-3 text-amber-500" />
                        <span>{bc.name}</span>
                      </button>
                    </div>
                  );
                })
              )}

              {/* Lối tắt xem tất cả tài liệu */}
              <button
                type="button"
                onClick={() => {
                  setAllFoldersActive(!allFoldersActive);
                  onPageChange(1);
                }}
                className={cn(
                  "ml-2 text-[11px] px-2 py-0.5 rounded-full border transition-colors flex items-center gap-1",
                  allFoldersActive
                    ? "border-primary bg-primary/10 text-primary font-medium"
                    : "border-border/70 text-muted-foreground hover:text-foreground hover:bg-muted/40",
                )}
              >
                <Layers className="size-3" />
                <span>Xem toàn bộ ({collection.source_count})</span>
              </button>
            </div>

            {/* Nhóm công cụ bên phải: Thêm thư mục + Tìm kiếm + Chế độ xem */}
            <div className="flex items-center justify-end gap-2 shrink-0">
              {canManage && (
                <Button
                  size="sm"
                  variant="outline"
                  className="h-8 px-2.5 text-xs gap-1.5 shadow-2xs"
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
                  <span>Thư mục mới</span>
                </Button>
              )}

              <div className="w-full sm:w-52 lg:w-64">
                <DebouncedSearchInput
                  value={searchQuery}
                  onChange={setSearchQuery}
                  placeholder="Tìm tài liệu..."
                  className="text-xs h-8"
                />
              </div>

              {searchQuery ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground"
                  onClick={() => setSearchQuery("")}
                >
                  <RotateCcw className="size-3 mr-1" />
                  <span>Đặt lại</span>
                </Button>
              ) : null}

              <ViewModeToggle value={viewMode} onChange={setViewMode} />
            </div>
          </div>

          {foldersQuery.isError && (
            <ErrorState
              error={foldersQuery.error}
              onRetry={() => void foldersQuery.refetch()}
            />
          )}

          {/* 1. KHU VỰC THƯ MỤC CON (Hiển thị dạng thẻ Google Drive Grid) */}
          {!allFoldersActive && directSubfolders.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                  <FolderOpen className="size-3.5 text-amber-500" />
                  <span>Thư mục ({directSubfolders.length})</span>
                </h2>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
                {directSubfolders.map((f) => (
                  <Card
                    key={f.id}
                    onClick={() => {
                      setCurrentFolderId(f.id);
                      setAllFoldersActive(false);
                      onPageChange(1);
                    }}
                    className="p-3 rounded-xl border border-border/70 hover:border-primary/50 hover:bg-muted/30 transition-all cursor-pointer group shadow-2xs hover:shadow-xs flex items-center justify-between gap-2"
                  >
                    <div className="flex items-center gap-2.5 min-w-0 flex-1">
                      <Folder className="size-5 sm:size-6 text-amber-500 group-hover:text-amber-600 transition-colors shrink-0" />
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-semibold text-foreground truncate group-hover:text-primary transition-colors">
                          {f.name}
                        </p>
                        <p className="text-[11px] text-muted-foreground truncate">
                          {f.source_count} tệp
                          {f.subfolder_count > 0
                            ? ` · ${f.subfolder_count} con`
                            : ""}
                        </p>
                      </div>
                    </div>

                    {canManage && (
                      <DropdownMenu>
                        <DropdownMenuTrigger
                          asChild
                          onClick={(e) => e.stopPropagation()}
                        >
                          <button
                            type="button"
                            aria-label="Thao tác thư mục"
                            className="size-6 shrink-0 opacity-0 group-hover:opacity-100 flex items-center justify-center rounded-md hover:bg-muted transition-opacity text-muted-foreground hover:text-foreground"
                          >
                            <MoreVertical className="size-3.5" />
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent
                          align="end"
                          className="w-44 text-xs"
                        >
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              setFolderToEdit(null);
                              setFolderParentForCreate({
                                id: f.id,
                                name: f.name,
                              });
                              setFolderFormOpen(true);
                            }}
                            className="gap-2"
                          >
                            <FolderPlus className="size-3.5 text-muted-foreground" />
                            <span>Tạo thư mục con</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              setFolderToEdit(f);
                              setFolderFormOpen(true);
                            }}
                            className="gap-2"
                          >
                            <Pencil className="size-3.5 text-muted-foreground" />
                            <span>Đổi tên</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              setItemToMove({
                                type: "folder",
                                id: f.id,
                                title: f.name,
                                currentFolderId: f.parent_id,
                              });
                              setMoveDialogOpen(true);
                            }}
                            className="gap-2"
                          >
                            <Folder className="size-3.5 text-muted-foreground" />
                            <span>Di chuyển</span>
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              setFolderToDelete(f);
                              setFolderDeleteOpen(true);
                            }}
                            className="gap-2 text-destructive focus:text-destructive"
                          >
                            <Trash2 className="size-3.5" />
                            <span>Xóa thư mục</span>
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    )}
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* 2. KHU VỰC TÀI LIỆU */}
          <div className="space-y-2">
            {!allFoldersActive && directSubfolders.length > 0 && (
              <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5 pt-2">
                <FileText className="size-3.5 text-primary" />
                <span>Tài liệu ({total})</span>
              </h2>
            )}

            {sourcesQuery.isLoading ? (
              <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5">
                <Skeleton className="h-28 w-full rounded-xl" />
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
              <Card className="rounded-xl border border-dashed bg-muted/10 shadow-none">
                <EmptyState
                  icon={FileUp}
                  title={
                    searchQuery
                      ? "Không tìm thấy tài liệu phù hợp"
                      : "Chưa có tài liệu nào trong thư mục này"
                  }
                  description={
                    searchQuery
                      ? "Hãy thử tìm kiếm với từ khóa hoặc tên tệp khác."
                      : "Tải lên tài liệu PDF hoặc Word (.docx) để lưu trữ an toàn và tiến hành bóc tách OCR."
                  }
                  action={
                    canManage && !searchQuery
                      ? {
                          label: "Tải tài liệu vào đây",
                          onClick: () => setUploadOpen(true),
                        }
                      : undefined
                  }
                  secondaryAction={
                    canManage && !searchQuery
                      ? {
                          label: "Tạo thư mục con",
                          onClick: () => {
                            setFolderToEdit(null);
                            setFolderParentForCreate({
                              id: currentFolderId,
                              name: currentFolder?.name ?? "Gốc kho tri thức",
                            });
                            setFolderFormOpen(true);
                          },
                        }
                      : undefined
                  }
                  className="py-12 max-w-md mx-auto"
                />
              </Card>
            ) : viewMode === "grid" ? (
              /* Chế độ Grid Card Full-Width */
              <div className="grid gap-3.5 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5">
                {sources.map((s) => {
                  const pdf = isPdf(s.content_type, s.file_name);
                  const docx = isDocx(s.content_type, s.file_name);
                  const formatLabel = pdf ? "PDF" : docx ? "DOCX" : "XLSX";
                  const statusInfo = formatProcessingStatus(s.processing);

                  return (
                    <Card
                      key={s.id}
                      className="p-4 rounded-xl border border-border/70 hover:border-primary/40 hover:shadow-xs transition-all group relative flex flex-col justify-between"
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
                            onLifecycle={(operation, source) =>
                              setSourceLifecycle({ source, operation })
                            }
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

                      {/* Tiến độ xử lý (nếu đang chạy/hàng đợi hoặc đã xử lý) & Footer */}
                      {s.processing ? (
                        <div className="pt-2.5 mt-2.5 border-t border-border/50 space-y-2">
                          <ProcessingProgress
                            compact
                            progress={{
                              status: s.processing.status,
                              pages_total: s.processing.pages_total,
                              pages_done: s.processing.pages_done,
                              pages_failed: s.processing.pages_failed,
                              results_ready: s.processing.results_ready,
                              dispatch_pending: s.processing.dispatch_pending,
                              error_code: s.processing.error_code,
                            }}
                            isPollError={sourcesQuery.isError}
                          />
                          <div className="flex items-center justify-end text-[11px]">
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
                                  ? "Đối chiếu & hiệu đính"
                                  : statusInfo.status === "running" ||
                                      statusInfo.status === "queued"
                                    ? "Theo dõi tiến độ"
                                    : "Chi tiết"}
                              </span>
                              <ChevronRight className="size-3" />
                            </Link>
                          </div>
                        </div>
                      ) : (
                        <div className="pt-3 mt-3 border-t border-border/50 flex items-center justify-between gap-2 text-[11px]">
                          <Badge
                            variant={statusInfo.variant}
                            className="text-[10px] py-0 px-1.5 font-normal truncate max-w-[65%]"
                          >
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
                            <span>Chi tiết</span>
                            <ChevronRight className="size-3" />
                          </Link>
                        </div>
                      )}
                    </Card>
                  );
                })}
              </div>
            ) : (
              /* Chế độ Bảng Table Full-Width */
              <div className="rounded-xl border border-border/70 overflow-hidden bg-card shadow-2xs">
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
                          <TableCell className="text-xs min-w-[180px]">
                            {s.processing ? (
                              <ProcessingProgress
                                compact
                                progress={{
                                  status: s.processing.status,
                                  pages_total: s.processing.pages_total,
                                  pages_done: s.processing.pages_done,
                                  pages_failed: s.processing.pages_failed,
                                  results_ready: s.processing.results_ready,
                                  dispatch_pending:
                                    s.processing.dispatch_pending,
                                  error_code: s.processing.error_code,
                                }}
                                isPollError={sourcesQuery.isError}
                              />
                            ) : (
                              <Badge
                                variant={statusInfo.variant}
                                className="text-[10px] font-normal"
                              >
                                {statusInfo.label}
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                            {formatDateTimeValue(s.updated_at || s.created_at)}
                          </TableCell>
                          <TableCell className="text-right">
                            <SourceActions
                              workspaceId={workspaceId}
                              collectionId={knowledgeId}
                              source={s}
                              onLifecycle={(operation, source) =>
                                setSourceLifecycle({ source, operation })
                              }
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
              </div>
            )}
          </div>

          {/* Phân trang */}
          {total > 0 && (
            <div className="pt-2">
              <DataTablePagination
                page={page}
                pageSize={pageSize}
                pageCount={pageCount}
                total={total}
                onPageChange={onPageChange}
                onPageSizeChange={onPageSizeChange}
              />
            </div>
          )}
        </div>
      )}

      {/* Khu vực Biên soạn trực tiếp trong kho (không qua màn trung gian) */}
      {activeStage === "compiler" && (
        <div className="space-y-4">
          <CompilationRunsList
            workspaceId={workspaceId}
            collectionId={knowledgeId}
            canManage={canCompile}
            onOpenCreateDialog={() => setCompilationDialogOpen(true)}
            page={page}
            pageSize={pageSize}
            onPageChange={onPageChange}
            onPageSizeChange={onPageSizeChange}
          />
          <CompilationDialog
            workspaceId={workspaceId}
            collectionId={knowledgeId}
            isOpen={compilationDialogOpen}
            onClose={() => setCompilationDialogOpen(false)}
          />
        </div>
      )}

      {/* Khu vực Phát hành trực tiếp trong kho (không qua màn trung gian) */}
      {activeStage === "publication" && (
        <CompiledDocumentsList
          workspaceId={workspaceId}
          collectionId={knowledgeId}
          canRegister={canPublish}
          onOpenCompilationTab={() => onStageChange?.("compiler")}
          page={page}
          pageSize={pageSize}
          onPageChange={onPageChange}
          onPageSizeChange={onPageSizeChange}
        />
      )}

      {/* Khu vực Chỉ mục & Tìm kiếm thử trực tiếp trong kho */}
      {activeStage === "serving" && (
        <IndexPanel
          workspaceId={workspaceId}
          collectionId={knowledgeId}
          canManage={canPublish}
          role={role}
          page={page}
          pageSize={pageSize}
          onPageChange={onPageChange}
          onPageSizeChange={onPageSizeChange}
        />
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
      <PendingSourceDeletions
        workspaceId={workspaceId}
        collectionId={knowledgeId}
        enabled={isLifecycleAdmin(role)}
      />
      {sourceLifecycle ? (
        <LifecycleActionDialog
          workspaceId={workspaceId}
          target={{
            kind: "source",
            resource_id: sourceLifecycle.source.id,
            action: sourceLifecycle.operation,
          }}
          label={sourceLifecycle.source.title}
          onClose={() => setSourceLifecycle(null)}
          onCompleted={() => {
            toast.success(
              sourceLifecycle.operation === "delete"
                ? "Đã xóa vĩnh viễn tài liệu."
                : "Đã lưu trữ tài liệu.",
            );
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
