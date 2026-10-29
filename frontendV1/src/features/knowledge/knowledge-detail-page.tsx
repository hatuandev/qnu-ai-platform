import { Link } from "@tanstack/react-router";
import {
  ArrowLeft,
  Bot,
  ChevronRight,
  FileEdit,
  FileSpreadsheet,
  FileText,
  FileUp,
  Folder,
  FolderOpen,
  FolderPlus,
  FolderTree,
  HardDrive,
  MoreVertical,
  Pencil,
  ScanLine,
  ShieldCheck,
} from "lucide-react";
import { useMemo, useState } from "react";
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
  formatSourceStatus,
  isDocx,
  isPdf,
} from "@/features/knowledge/schemas";
import { SourceActions } from "@/features/knowledge/source-actions";
import { SourceRenameDialog } from "@/features/knowledge/source-rename-dialog";
import { SourceUploadDialog } from "@/features/knowledge/source-upload-dialog";
import { StageOcrPanel } from "@/features/knowledge/stage-ocr-panel";
import type {
  FolderBreadcrumbItem,
  KBFolder,
  KBSource,
} from "@/features/knowledge/types";
import { LifecycleActions } from "@/features/lifecycle/lifecycle-actions";
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
  selectedSourceId,
  onPageChange,
  onPageSizeChange,
  onStageChange,
  onSelectSourceId,
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
  const [editCollectionOpen, setEditCollectionOpen] = useState(false);
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
      {/* 1. Header with Breadcrumb & Quick Actions */}
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

        {/* Top Actions */}
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5 text-xs h-9"
            disabled={!canManage || foldersQuery.isError}
            onClick={() => {
              setFolderToEdit(null);
              setFolderParentForCreate({
                id: currentFolderId,
                name: currentFolder?.name ?? "Gốc kho tri thức",
              });
              setFolderFormOpen(true);
            }}
          >
            <FolderPlus className="size-4 text-muted-foreground" />
            <span>Tạo thư mục</span>
          </Button>

          <Button
            size="sm"
            className="gap-1.5 text-xs h-9 shadow-xs"
            disabled={!canManage || foldersQuery.isError}
            onClick={() => setUploadOpen(true)}
          >
            <FileUp className="size-4" />
            <span>Tải tài liệu</span>
          </Button>

          {canManage && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  aria-label="Sửa thông tin kho"
                  className="size-9 p-0 text-muted-foreground"
                >
                  <MoreVertical className="size-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-44 text-xs">
                <DropdownMenuItem
                  className="gap-2"
                  onClick={() => setEditCollectionOpen(true)}
                >
                  <Pencil className="size-3.5" />
                  <span>Sửa thông tin kho</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
          <LifecycleActions
            workspaceId={workspaceId}
            kind="collection"
            resourceId={collection.id}
            label={collection.name}
            role={role}
          />
        </div>
      </div>

      {/* 2. Pipeline Stepper (Thanh tiến trình 5 Chặng quy trình) */}
      <div className="rounded-xl border bg-muted/20 p-2 sm:p-3">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
          {/* Chặng 1: Tài liệu & Thư mục (ACTIVE) */}
          <Button
            variant="ghost"
            onClick={() => onStageChange?.("files")}
            className={cn(
              "h-auto whitespace-normal justify-start flex items-center gap-2.5 p-2.5 rounded-lg border text-left transition-all cursor-pointer",
              activeStage === "files"
                ? "bg-primary text-primary-foreground border-primary shadow-xs"
                : "bg-card hover:bg-muted/50 border-border/80 text-foreground",
            )}
          >
            <div
              className={cn(
                "flex size-8 shrink-0 items-center justify-center rounded-lg",
                activeStage === "files"
                  ? "bg-primary-foreground/20 text-primary-foreground"
                  : "bg-primary/10 text-primary",
              )}
            >
              <FolderTree className="size-4" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold whitespace-normal">
                  1. Tài liệu & Thư mục
                </span>
                <span
                  className={cn(
                    "text-[10px] px-1.5 py-0.2 rounded-full font-mono",
                    activeStage === "files"
                      ? "bg-primary-foreground/20 text-primary-foreground"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  {collection.source_count}
                </span>
              </div>
              <p
                className={cn(
                  "text-[10px] truncate mt-0.5",
                  activeStage === "files"
                    ? "text-primary-foreground/80"
                    : "text-muted-foreground",
                )}
              >
                Quản lý tệp & cây thư mục
              </p>
            </div>
          </Button>

          {/* Chặng 2: OCR & Hiệu đính */}
          <Button
            variant="ghost"
            onClick={() => onStageChange?.("ocr")}
            className={cn(
              "h-auto whitespace-normal justify-start flex items-center gap-2.5 p-2.5 rounded-lg border text-left transition-all cursor-pointer",
              activeStage === "ocr"
                ? "bg-primary text-primary-foreground border-primary shadow-xs"
                : "bg-card hover:bg-muted/50 border-border/80 text-foreground",
            )}
          >
            <div
              className={cn(
                "flex size-8 shrink-0 items-center justify-center rounded-lg",
                activeStage === "ocr"
                  ? "bg-primary-foreground/20 text-primary-foreground"
                  : "bg-muted text-muted-foreground",
              )}
            >
              <ScanLine className="size-4" />
            </div>
            <div className="min-w-0 flex-1">
              <span className="text-xs font-semibold whitespace-normal block">
                2. OCR & Hiệu đính
              </span>
              <p className="text-[10px] text-muted-foreground truncate mt-0.5">
                Bóc tách & chính tả AI
              </p>
            </div>
          </Button>

          {/* Chặng 3: Biên soạn (Compiler) */}
          <Button
            variant="ghost"
            onClick={() => onStageChange?.("compiler")}
            className={cn(
              "h-auto whitespace-normal justify-start flex items-center gap-2.5 p-2.5 rounded-lg border text-left transition-all cursor-pointer",
              activeStage === "compiler"
                ? "bg-primary text-primary-foreground border-primary shadow-xs"
                : "bg-card hover:bg-muted/50 border-border/80 text-foreground",
            )}
          >
            <div
              className={cn(
                "flex size-8 shrink-0 items-center justify-center rounded-lg",
                activeStage === "compiler"
                  ? "bg-primary-foreground/20 text-primary-foreground"
                  : "bg-muted text-muted-foreground",
              )}
            >
              <FileEdit className="size-4" />
            </div>
            <div className="min-w-0 flex-1">
              <span className="text-xs font-semibold whitespace-normal block">
                3. Biên soạn
              </span>
              <p className="text-[10px] text-muted-foreground truncate mt-0.5">
                Compiler ghim dẫn chứng
              </p>
            </div>
          </Button>

          {/* Chặng 4: Rà soát & Xuất bản */}
          <Button
            variant="ghost"
            onClick={() => onStageChange?.("publication")}
            className={cn(
              "h-auto whitespace-normal justify-start flex items-center gap-2.5 p-2.5 rounded-lg border text-left transition-all cursor-pointer",
              activeStage === "publication"
                ? "bg-primary text-primary-foreground border-primary shadow-xs"
                : "bg-card hover:bg-muted/50 border-border/80 text-foreground",
            )}
          >
            <div
              className={cn(
                "flex size-8 shrink-0 items-center justify-center rounded-lg",
                activeStage === "publication"
                  ? "bg-primary-foreground/20 text-primary-foreground"
                  : "bg-muted text-muted-foreground",
              )}
            >
              <ShieldCheck className="size-4" />
            </div>
            <div className="min-w-0 flex-1">
              <span className="text-xs font-semibold whitespace-normal block">
                4. Xuất bản
              </span>
              <p className="text-[10px] text-muted-foreground truncate mt-0.5">
                Cổng rà soát Review Gate
              </p>
            </div>
          </Button>

          {/* Chặng 5: Đánh chỉ mục & Phục vụ AI */}
          <Button
            variant="ghost"
            onClick={() => onStageChange?.("serving")}
            className={cn(
              "flex items-center gap-2.5 p-2.5 rounded-lg border text-left transition-all cursor-pointer col-span-2 md:col-span-1",
              activeStage === "serving"
                ? "bg-primary text-primary-foreground border-primary shadow-xs"
                : "bg-card hover:bg-muted/50 border-border/80 text-foreground",
            )}
          >
            <div
              className={cn(
                "flex size-8 shrink-0 items-center justify-center rounded-lg",
                activeStage === "serving"
                  ? "bg-primary-foreground/20 text-primary-foreground"
                  : "bg-muted text-muted-foreground",
              )}
            >
              <Bot className="size-4" />
            </div>
            <div className="min-w-0 flex-1">
              <span className="text-xs font-semibold whitespace-normal block">
                5. Phục vụ AI
              </span>
              <p className="text-[10px] text-muted-foreground truncate mt-0.5">
                Chỉ mục Qdrant & Chat
              </p>
            </div>
          </Button>
        </div>
      </div>

      {/* 3. CHẶNG 1: FILE EXPLORER HIỆN ĐẠI (Cột trái: Cây thư mục | Vùng phải: Tệp & Thư mục con) */}
      {activeStage === "files" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 min-h-[540px]">
          {/* CỘT TRÁI (3 cols): Cây thư mục (Windows 11 Explorer Sidebar) */}
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

          {/* VÙNG PHẢI (9 cols): Quản lý tệp và thư mục con */}
          <div className="lg:col-span-9 space-y-4">
            {/* Breadcrumb đường dẫn thư mục hiện tại & Công cụ */}
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between rounded-xl border bg-card p-3 shadow-2xs">
              {/* Breadcrumb */}
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
                <div className="w-full sm:w-56">
                  <DebouncedSearchInput
                    value={searchQuery}
                    onChange={setSearchQuery}
                    placeholder="Tìm trong trang này..."
                    className="text-xs h-8"
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
            {/* Danh sách Thư mục con (nếu có trong thư mục hiện tại) */}
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
                      ? "Không tìm thấy tệp phù hợp"
                      : "Chưa có tài liệu nào trong thư mục này"}
                  </p>
                  <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                    {searchQuery
                      ? "Hãy thử tìm kiếm với từ khóa khác."
                      : "Tải tài liệu PDF hoặc DOCX lên để bắt đầu quy trình bóc tách và huấn luyện trợ lý AI."}
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
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {sources.map((s) => {
                  const pdf = isPdf(s.content_type, s.file_name);
                  const docx = isDocx(s.content_type, s.file_name);

                  return (
                    <Card
                      key={s.id}
                      className="p-3.5 rounded-xl border-border/80 hover:border-primary/60 hover:bg-muted/10 transition-all cursor-pointer group shadow-2xs relative flex flex-col justify-between"
                    >
                      <div className="space-y-2">
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
                            {pdf ? (
                              <FileText className="size-4" />
                            ) : docx ? (
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
                              >
                                {s.title}
                              </Link>
                            </h4>
                            <p className="text-[11px] text-muted-foreground truncate font-mono">
                              {s.file_name}
                            </p>
                          </div>

                          <SourceActions
                            workspaceId={workspaceId}
                            collectionId={knowledgeId}
                            source={s}
                            role={role}
                            canManage={canManage}
                            onOcr={() => {
                              onSelectSourceId?.(s.id);
                              onStageChange?.("ocr");
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

                        {/* Thông tin phụ: Size, Revision, Trạng thái */}
                        <div className="flex items-center gap-1.5 flex-wrap pt-1 text-[11px] text-muted-foreground">
                          <Badge
                            variant="outline"
                            className="text-[10px] py-0 px-1 font-mono font-normal"
                          >
                            v{s.current_revision_no}
                          </Badge>
                          <span>·</span>
                          <span>{formatBytes(s.size_bytes)}</span>
                          <span>·</span>
                          <span className="truncate">
                            {formatDateTimeValue(s.updated_at || s.created_at)}
                          </span>
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </div>
            ) : (
              /* Chế độ Bảng Table */
              <Card className="rounded-xl border overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Tên tài liệu</TableHead>
                      <TableHead>Định dạng</TableHead>
                      <TableHead>Kích thước</TableHead>
                      <TableHead>Phiên bản</TableHead>
                      <TableHead>Trạng thái</TableHead>
                      <TableHead>Cập nhật</TableHead>
                      <TableHead className="text-right">Thao tác</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sources.map((s) => {
                      const pdf = isPdf(s.content_type, s.file_name);
                      const docx = isDocx(s.content_type, s.file_name);

                      return (
                        <TableRow
                          key={s.id}
                          className="cursor-pointer hover:bg-muted/40"
                        >
                          <TableCell className="font-semibold text-xs text-foreground max-w-xs truncate">
                            <div className="flex items-center gap-2">
                              {pdf ? (
                                <FileText className="size-3.5 text-rose-500 shrink-0" />
                              ) : docx ? (
                                <FileText className="size-3.5 text-blue-500 shrink-0" />
                              ) : (
                                <FileSpreadsheet className="size-3.5 text-emerald-500 shrink-0" />
                              )}
                              <span className="truncate">
                                <Link
                                  to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId"
                                  params={{
                                    workspaceId,
                                    collectionId: knowledgeId,
                                    sourceId: s.id,
                                  }}
                                >
                                  {s.title}
                                </Link>
                              </span>
                            </div>
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
                            <Badge variant="outline" className="text-[10px]">
                              {formatSourceStatus(s.status)}
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
                              role={role}
                              canManage={canManage}
                              onOcr={() => {
                                onSelectSourceId?.(s.id);
                                onStageChange?.("ocr");
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

      {/* CHẶNG 2: BÓC TÁCH OCR & HIỆU ĐÍNH VĂN BẢN */}
      {activeStage === "ocr" && (
        <StageOcrPanel
          workspaceId={workspaceId}
          collectionId={knowledgeId}
          canManage={canManage}
          selectedSourceId={selectedSourceId}
          onSelectSourceId={onSelectSourceId}
          onProceedToCompiler={() => onStageChange?.("compiler")}
        />
      )}

      {/* CHẶNG 3: BIÊN SOẠN TRI THỨC (COMPILER) */}
      {activeStage === "compiler" && (
        <div className="rounded-xl border border-dashed p-12 text-center space-y-3 bg-muted/10">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-primary/10 text-primary mx-auto">
            <FileEdit className="size-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-foreground">
              Chặng 3: Biên soạn tri thức (Compiler)
            </h3>
            <p className="text-xs text-muted-foreground max-w-md mx-auto">
              Chọn kết quả OCR đã hiệu đính để tạo và theo dõi lượt biên soạn.
            </p>
          </div>
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

      {/* CHẶNG 4: RÀ SOÁT & XUẤT BẢN */}
      {activeStage === "publication" && (
        <div className="rounded-xl border border-dashed p-12 text-center space-y-3 bg-muted/10">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-primary/10 text-primary mx-auto">
            <ShieldCheck className="size-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-foreground">
              Chặng 4: Cổng rà soát & Xuất bản (Review Gate)
            </h3>
            <p className="text-xs text-muted-foreground max-w-md mx-auto">
              Kiểm duyệt phiên bản tài liệu, đối chiếu tính toàn vẹn và cấp phép
              xuất bản tri thức cho đơn vị.
            </p>
          </div>
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

      {/* CHẶNG 5: ĐÁNH CHỈ MỤC & PHỤC VỤ AI */}
      {activeStage === "serving" && (
        <div className="rounded-xl border border-dashed p-12 text-center space-y-3 bg-muted/10">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-primary/10 text-primary mx-auto">
            <Bot className="size-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-foreground">
              Chặng 5: Đánh chỉ mục Qdrant & Phục vụ Trợ lý AI
            </h3>
            <p className="text-xs text-muted-foreground max-w-md mx-auto">
              Vector hóa dữ liệu tri thức, theo dõi trạng thái đồng bộ vector
              database và kiểm thử truy vấn RAG.
            </p>
          </div>
          <Button asChild size="sm">
            <Link
              to="/workspaces/$workspaceId/collections/$collectionId/search"
              params={{ workspaceId, collectionId: knowledgeId }}
              search={{ page: 1, pageSize: 20 }}
            >
              Mở chỉ mục & tìm kiếm
            </Link>
          </Button>
        </div>
      )}

      {/* 4. MODALS & DIALOGS */}
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
          void sourcesQuery.refetch();
        }}
      />

      {/* Di chuyển Thư mục / Tệp */}
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
            setItemToMove(null);
          }}
        />
      )}

      {/* Xóa Thư mục (có kiểm tra tác động an toàn) */}
      <FolderDeleteDialog
        open={folderDeleteOpen}
        onOpenChange={(open) => {
          setFolderDeleteOpen(open);
          if (!open) setFolderToDelete(null);
        }}
        workspaceId={workspaceId}
        collectionId={knowledgeId}
        folder={folderToDelete}
        onSuccess={() => {
          void foldersQuery.refetch();
          void sourcesQuery.refetch();
          if (folderToDelete && currentFolderId === folderToDelete.id) {
            setCurrentFolderId(null);
          }
          setFolderToDelete(null);
        }}
      />

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
          setSourceToRename(null);
        }}
      />

      {/* Sửa thông tin Kho */}
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
