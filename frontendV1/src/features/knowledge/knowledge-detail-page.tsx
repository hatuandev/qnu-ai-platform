import { Link, useNavigate } from "@tanstack/react-router";
import {
  Archive,
  ArrowLeft,
  BookMarked,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  FileText,
  FileUp,
  Folder,
  FolderOpen,
  FolderPlus,
  MoreVertical,
  Pencil,
  RotateCcw,
  Settings2,
  Trash2,
} from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { useV1Auth } from "@/app/auth/v1";
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
import {
  DocumentTypeIcon,
  FolderItemIcon,
  getDocumentFormatInfo,
} from "@/features/knowledge/document-file-icon";
import { FolderDeleteDialog } from "@/features/knowledge/folder-delete-dialog";
import { FolderFormDialog } from "@/features/knowledge/folder-form-dialog";
import { FolderMoveDialog } from "@/features/knowledge/folder-move-dialog";
import { IndexPanel } from "@/features/knowledge/index-panel";
import { KnowledgeBreadcrumbs } from "@/features/knowledge/knowledge-breadcrumbs";
import {
  canCreateOrEditCompilation,
  canManageKnowledge,
  canRegisterCompiledDocument,
} from "@/features/knowledge/permissions";
import { ProcessingProgress } from "@/features/knowledge/processing-progress";
import {
  useCollectionQuery,
  useFoldersQuery,
  useMoveSource,
  useSourcesQuery,
} from "@/features/knowledge/queries";
import {
  formatBytes,
  formatProcessingStatus,
} from "@/features/knowledge/schemas";
import { SourceActions } from "@/features/knowledge/source-actions";
import { SourceReextractDialog } from "@/features/knowledge/source-reextract-dialog";
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
  const { sessionId } = useV1Auth();

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
  const [sourceToExtract, setSourceToExtract] = useState<KBSource | null>(null);
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

  // Drag & Drop State
  const [draggingSourceId, setDraggingSourceId] = useState<string | null>(null);
  const [dragOverTargetId, setDragOverTargetId] = useState<string | null>(null);
  const activeDrag = useRef<{
    sourceId: string;
    workspaceId: string;
    collectionId: string;
    sessionId: typeof sessionId;
  } | null>(null);
  const moveSourceMutation = useMoveSource(workspaceId, knowledgeId);

  const handleDragStart = (
    e: React.DragEvent<HTMLElement>,
    source: KBSource,
  ) => {
    if (!canManage || moveSourceMutation.isPending) {
      e.preventDefault();
      return;
    }
    activeDrag.current = {
      sourceId: source.id,
      workspaceId,
      collectionId: knowledgeId,
      sessionId,
    };
    setDraggingSourceId(source.id);
    e.dataTransfer.setData("application/qnu-source-id", source.id);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragEnd = () => {
    activeDrag.current = null;
    setDraggingSourceId(null);
    setDragOverTargetId(null);
  };

  const getDraggedSource = () => {
    const drag = activeDrag.current;
    if (
      !canManage ||
      moveSourceMutation.isPending ||
      !drag ||
      drag.workspaceId !== workspaceId ||
      drag.collectionId !== knowledgeId ||
      drag.sessionId !== sessionId
    )
      return undefined;
    return sources.find(
      (source) =>
        source.id === drag.sourceId && source.collection_id === knowledgeId,
    );
  };

  const handleFolderDragOver = (
    e: React.DragEvent<HTMLElement>,
    folderId: string,
  ) => {
    if (
      !getDraggedSource() ||
      !e.dataTransfer.types.includes("application/qnu-source-id")
    )
      return;
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = "move";
    if (dragOverTargetId !== folderId) {
      setDragOverTargetId(folderId);
    }
  };

  const handleFolderDragLeave = (
    e: React.DragEvent<HTMLElement>,
    folderId: string,
  ) => {
    e.preventDefault();
    e.stopPropagation();
    if (dragOverTargetId === folderId) {
      setDragOverTargetId(null);
    }
  };

  const handleDropOnFolder = (
    e: React.DragEvent<HTMLElement>,
    targetFolderId: string | null,
    targetFolderName: string,
  ) => {
    e.preventDefault();
    e.stopPropagation();
    const source = getDraggedSource();
    const sourceId = e.dataTransfer.getData("application/qnu-source-id");
    // Consume the local drag before starting I/O; repeated drops cannot resubmit it.
    handleDragEnd();
    if (
      !source ||
      sourceId !== source.id ||
      source.folder_id === targetFolderId ||
      (targetFolderId !== null &&
        !folders.some((folder) => folder.id === targetFolderId))
    ) {
      return;
    }

    const sourceTitle = source.title;

    moveSourceMutation.mutate(
      { sourceId, targetFolderId },
      {
        onSuccess: () => {
          toast.success(
            targetFolderId
              ? `Đã di chuyển "${sourceTitle}" vào thư mục "${targetFolderName}"`
              : `Đã di chuyển "${sourceTitle}" ra Gốc kho tri thức`,
          );
        },
        onError: (err) => {
          toast.error(
            `Không thể di chuyển tài liệu: ${
              err instanceof Error ? err.message : "Đã xảy ra lỗi"
            }`,
          );
        },
      },
    );
  };

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
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-muted/60 text-[11px] font-medium border border-border/40">
              <FileText className="size-3 text-primary" />
              <span>{collection.source_count} tài liệu</span>
            </span>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-muted/60 text-[11px] font-medium border border-border/40">
              <Folder className="size-3 text-amber-500 fill-amber-500/20" />
              <span>{folders.length} thư mục</span>
            </span>
          </div>

          {/* Tab Giai đoạn (Tài liệu / Chuẩn bị nội dung / Xuất bản) */}
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
              <span>Chuẩn bị nội dung</span>
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
              <span>Xuất bản</span>
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

          {canManage && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  aria-label="Quản lý kho"
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
            {/* Đường dẫn Breadcrumb phong cách Google Drive (Hỗ trợ Drop target tệp) */}
            <KnowledgeBreadcrumbs
              currentFolderId={currentFolderId}
              allFoldersActive={allFoldersActive}
              parentFolder={parentFolder}
              folderBreadcrumbs={folderBreadcrumbs}
              rootSourceCount={rootSourceCount}
              totalSourceCount={collection.source_count}
              dragOverTargetId={dragOverTargetId}
              draggingSourceId={draggingSourceId}
              onSelectFolder={(folderId) => {
                setCurrentFolderId(folderId);
                setAllFoldersActive(false);
                onPageChange(1);
              }}
              onToggleAllFolders={() => {
                setAllFoldersActive(!allFoldersActive);
                onPageChange(1);
              }}
              onDragOverTarget={handleFolderDragOver}
              onDragLeaveTarget={handleFolderDragLeave}
              onDropTarget={handleDropOnFolder}
            />

            {/* Nhóm công cụ bên phải: Tìm kiếm + Chế độ xem */}
            <div className="flex min-w-0 flex-wrap items-center justify-end gap-2 sm:flex-1">
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
                {directSubfolders.map((f) => {
                  const isHoveredTarget = dragOverTargetId === f.id;
                  return (
                    <Card
                      key={f.id}
                      onDragOver={(e) => handleFolderDragOver(e, f.id)}
                      onDragLeave={(e) => handleFolderDragLeave(e, f.id)}
                      onDrop={(e) => handleDropOnFolder(e, f.id, f.name)}
                      onClick={() => {
                        setCurrentFolderId(f.id);
                        setAllFoldersActive(false);
                        onPageChange(1);
                      }}
                      className={cn(
                        "p-3 rounded-xl border transition-all cursor-pointer group shadow-2xs hover:shadow-xs flex items-center justify-between gap-2",
                        isHoveredTarget
                          ? "border-primary ring-2 ring-primary/40 bg-primary/10 scale-[1.03] shadow-md"
                          : "border-border/70 hover:border-primary/50 hover:bg-muted/30",
                      )}
                    >
                      <div className="flex items-center gap-2.5 min-w-0 flex-1">
                        <div
                          className={cn(
                            "flex size-9 shrink-0 items-center justify-center rounded-lg border transition-colors",
                            isHoveredTarget
                              ? "bg-primary text-primary-foreground border-primary"
                              : "bg-amber-100/60 dark:bg-amber-950/40 border-amber-200/60 dark:border-amber-800/40 text-amber-600 dark:text-amber-400",
                          )}
                        >
                          <FolderItemIcon
                            open={isHoveredTarget}
                            className={cn(
                              "size-5",
                              isHoveredTarget
                                ? "text-primary-foreground fill-primary-foreground/30"
                                : "text-amber-600 dark:text-amber-400",
                            )}
                          />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-semibold text-foreground truncate group-hover:text-primary transition-colors">
                            {f.name}
                          </p>
                          <p className="text-[11px] text-muted-foreground truncate">
                            {isHoveredTarget ? (
                              <span className="text-primary font-medium">
                                Thả để chuyển vào
                              </span>
                            ) : (
                              <>
                                {f.source_count} tệp
                                {f.subfolder_count > 0
                                  ? ` · ${f.subfolder_count} con`
                                  : ""}
                              </>
                            )}
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
                  );
                })}
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
                      : "Tải lên tài liệu PDF hoặc Word (.docx) để lưu trữ an toàn và đọc nội dung."
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
                  const formatInfo = getDocumentFormatInfo(
                    s.content_type,
                    s.file_name,
                  );
                  const statusInfo = formatProcessingStatus(s.processing);

                  const isDragging = draggingSourceId === s.id;

                  return (
                    <Card
                      key={s.id}
                      draggable={canManage}
                      onDragStart={(e) => handleDragStart(e, s)}
                      onDragEnd={handleDragEnd}
                      onClick={() => {
                        void navigate({
                          to: "/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId",
                          params: {
                            workspaceId,
                            collectionId: knowledgeId,
                            sourceId: s.id,
                          },
                        });
                      }}
                      className={cn(
                        "min-w-0 p-4 rounded-xl border border-border/70 hover:border-primary/50 hover:bg-muted/20 hover:shadow-xs transition-all group relative flex flex-col justify-between select-none cursor-pointer",
                        isDragging &&
                          "opacity-40 scale-95 border-dashed border-primary ring-2 ring-primary/20",
                      )}
                    >
                      <div className="space-y-2.5">
                        <div className="flex items-start gap-2.5">
                          <div
                            className={cn(
                              "flex size-9 shrink-0 items-center justify-center rounded-lg border",
                              formatInfo.containerClass,
                            )}
                          >
                            <DocumentTypeIcon
                              contentType={s.content_type}
                              fileName={s.file_name}
                              className="size-5"
                            />
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
                            <p className="text-[11px] text-muted-foreground truncate mt-0.5 flex items-center gap-1.5">
                              <span
                                className={cn(
                                  "font-mono font-semibold px-1 py-0.2 rounded text-[10px] border",
                                  formatInfo.badgeClass,
                                )}
                              >
                                {formatInfo.label}
                              </span>
                              <span>·</span>
                              <span className="font-mono">
                                v{s.current_revision_no}
                              </span>
                              <span>·</span>
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
                            onReextract={() => setSourceToExtract(s)}
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
                        Trạng thái đọc nội dung
                      </TableHead>
                      <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3">
                        Cập nhật
                      </TableHead>
                      <TableHead className="w-[60px] text-right font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sources.map((s) => {
                      const formatInfo = getDocumentFormatInfo(
                        s.content_type,
                        s.file_name,
                      );
                      const statusInfo = formatProcessingStatus(s.processing);

                      const isDragging = draggingSourceId === s.id;

                      return (
                        <TableRow
                          key={s.id}
                          draggable={canManage}
                          onDragStart={(e) => handleDragStart(e, s)}
                          onDragEnd={handleDragEnd}
                          onClick={() => {
                            void navigate({
                              to: "/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId",
                              params: {
                                workspaceId,
                                collectionId: knowledgeId,
                                sourceId: s.id,
                              },
                            });
                          }}
                          className={cn(
                            "group hover:bg-muted/50 transition-colors select-none cursor-pointer",
                            isDragging &&
                              "opacity-40 bg-primary/5 border-dashed",
                          )}
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
                              <DocumentTypeIcon
                                contentType={s.content_type}
                                fileName={s.file_name}
                                className="size-4 shrink-0"
                              />
                              <span className="truncate">{s.title}</span>
                            </Link>
                          </TableCell>
                          <TableCell className="text-xs font-mono">
                            <span
                              className={cn(
                                "font-mono font-semibold px-1.5 py-0.5 rounded text-[10px] border",
                                formatInfo.badgeClass,
                              )}
                            >
                              {formatInfo.label}
                            </span>
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
                              onReextract={() => setSourceToExtract(s)}
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

      {/* Khu vực Chuẩn bị nội dung trực tiếp trong kho (không qua màn trung gian) */}
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

      {/* Khu vực Xuất bản trực tiếp trong kho (không qua màn trung gian) */}
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

      {sourceToExtract && canManage && (
        <SourceReextractDialog
          key={`${sessionId}:${workspaceId}:${knowledgeId}:${sourceToExtract.id}`}
          workspaceId={workspaceId}
          collectionId={knowledgeId}
          source={sourceToExtract}
          onClose={() => setSourceToExtract(null)}
          onStarted={(revisionId, runId) => {
            setSourceToExtract(null);
            void sourcesQuery.refetch();
            void navigate({
              to: "/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId",
              params: {
                workspaceId,
                collectionId: knowledgeId,
                sourceId: sourceToExtract.id,
              },
              search: { revisionId, runId },
            });
          }}
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
