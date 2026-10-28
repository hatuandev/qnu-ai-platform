import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  ChevronRight,
  Cpu,
  Database,
  Download,
  Eye,
  FileText,
  FileUp,
  Folder as FolderIcon,
  FolderOpen,
  FolderPlus,
  HardDrive,
  MoreVertical,
  Pencil,
  Search,
  SlidersHorizontal,
  Trash2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
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
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { FolderDeleteDialog } from "@/features/knowledge/folder-delete-dialog";
import { FolderFormDialog } from "@/features/knowledge/folder-form-dialog";
import { FolderMoveDialog } from "@/features/knowledge/folder-move-dialog";
import { FolderTreePanel } from "@/features/knowledge/folder-tree-panel";
import { canManageKnowledge } from "@/features/knowledge/permissions";
import {
  downloadSourceRevision,
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
import { SourceRenameDialog } from "@/features/knowledge/source-rename-dialog";
import { SourceUploadDialog } from "@/features/knowledge/source-upload-dialog";
import type { KBFolder, KBSource } from "@/features/knowledge/types";
import { LifecycleActions } from "@/features/lifecycle/lifecycle-actions";
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";
import { formatDateTimeValue } from "@/lib/date-utils";
import { cn } from "@/lib/utils";

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
  const foldersQuery = useFoldersQuery(workspaceId, collectionId);

  // Deep link migration: if old tab route was compilations, documents, or index, redirect cleanly
  useEffect(() => {
    if (tab === "compilations") {
      void navigate({
        to: "/workspaces/$workspaceId/collections/$collectionId/compilations",
        params: { workspaceId, collectionId },
        search: { page: 1, pageSize: 20 },
        replace: true,
      });
    } else if (tab === "documents") {
      void navigate({
        to: "/workspaces/$workspaceId/collections/$collectionId/documents",
        params: { workspaceId, collectionId },
        search: { page: 1, pageSize: 20 },
        replace: true,
      });
    } else if (tab === "index") {
      void navigate({
        to: "/workspaces/$workspaceId/collections/$collectionId/search",
        params: { workspaceId, collectionId },
        search: { page: 1, pageSize: 20 },
        replace: true,
      });
    }
  }, [tab, navigate, workspaceId, collectionId]);

  // Explorer State
  const [currentFolderId, setCurrentFolderId] = useState<string | null>(null);
  const [allFoldersActive, setAllFoldersActive] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<"all" | "pdf" | "docx">("all");
  const [viewMode, setViewMode] = useState<"grid" | "table">("table");

  // Dialog States
  const [editCollectionOpen, setEditCollectionOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [folderFormOpen, setFolderFormOpen] = useState(false);
  const [folderToEdit, setFolderToEdit] = useState<KBFolder | null>(null);
  const [folderParentForCreate, setFolderParentForCreate] = useState<{
    id: string | null;
    name: string;
  }>({ id: null, name: "" });

  const [moveDialogState, setMoveDialogState] = useState<{
    open: boolean;
    itemType: "folder" | "source";
    itemId: string;
    itemTitle: string;
    currentFolderId?: string | null;
  }>({
    open: false,
    itemType: "source",
    itemId: "",
    itemTitle: "",
  });

  const [deleteFolderState, setDeleteFolderState] = useState<{
    open: boolean;
    folder: KBFolder | null;
  }>({ open: false, folder: null });

  const [renameSourceState, setRenameSourceState] = useState<{
    open: boolean;
    source: KBSource | null;
  }>({ open: false, source: null });

  const [downloadingSourceId, setDownloadingSourceId] = useState<string | null>(
    null,
  );

  const canManage = !rolePending && canManageKnowledge(role);
  const collection = collectionQuery.data;
  const folders = foldersQuery.data ?? [];

  // Active folder object if not at root
  const currentFolder = useMemo(
    () => folders.find((f) => f.id === currentFolderId) ?? null,
    [folders, currentFolderId],
  );

  // Subfolders in current view
  const directSubfolders = useMemo(() => {
    if (allFoldersActive) return [];
    return folders.filter((f) => f.parent_id === (currentFolderId ?? null));
  }, [folders, currentFolderId, allFoldersActive]);

  // Calculate breadcrumbs path for current folder
  const folderBreadcrumbs = useMemo(() => {
    if (allFoldersActive || !currentFolder) return [];
    const chain: KBFolder[] = [];
    let curr: KBFolder | undefined = currentFolder;
    while (curr) {
      chain.unshift(curr);
      curr = folders.find((f) => f.id === curr?.parent_id);
    }
    return chain;
  }, [currentFolder, folders, allFoldersActive]);

  // Fetch sources filtered by folder
  const sourcesQuery = useSourcesQuery(workspaceId, collectionId, {
    page,
    pageSize,
    folderId: allFoldersActive ? undefined : currentFolderId ?? "root",
    allFolders: allFoldersActive,
  });

  const rawSources = sourcesQuery.data?.items ?? [];
  const total = sourcesQuery.data?.meta.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  // Client-side quick filter on current page
  const sources = useMemo(() => {
    let result = rawSources;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(
        (s) =>
          s.title.toLowerCase().includes(q) ||
          s.file_name.toLowerCase().includes(q),
      );
    }
    if (typeFilter === "pdf") {
      result = result.filter((s) => isPdf(s.content_type));
    } else if (typeFilter === "docx") {
      result = result.filter((s) => isDocx(s.content_type));
    }
    return result;
  }, [rawSources, searchQuery, typeFilter]);

  const rootSourceCount = useMemo(() => {
    const rootSources = folders.length === 0 ? (collection?.source_count ?? 0) : 0;
    return rootSources;
  }, [folders, collection]);

  // Handle Download Source Revision
  const handleDownload = async (source: KBSource) => {
    const revId = source.id; // download latest revision
    setDownloadingSourceId(source.id);
    try {
      const blobResp = await downloadSourceRevision(
        workspaceId,
        collectionId,
        source.id,
        String(source.current_revision_no),
      );
      const url = URL.createObjectURL(blobResp.blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = source.file_name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Không thể tải xuống tệp gốc.");
    } finally {
      setDownloadingSourceId(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Breadcrumb & Actions Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between pb-3 border-b border-border/60">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground flex-wrap mb-1">
            <Link
              to="/workspaces/$workspaceId/collections"
              params={{ workspaceId }}
              search={{ page: 1, pageSize: 20 }}
              className="hover:text-foreground transition-colors flex items-center gap-1"
            >
              <ArrowLeft className="size-3" />
              <span>Kho tri thức</span>
            </Link>
            <ChevronRight className="size-3 text-muted-foreground/60" />
            <span className="font-medium text-foreground truncate max-w-[200px]">
              {collection?.name ?? "Đang tải..."}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-foreground truncate">
              {collection?.name ?? <Skeleton className="h-7 w-48" />}
            </h1>
            {collection ? (
              <Badge variant="secondary" className="text-xs font-normal shrink-0">
                {collection.source_count} tài liệu
              </Badge>
            ) : null}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2 shrink-0">
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5 text-xs h-9"
            disabled={!canManage}
            onClick={() => {
              setFolderToEdit(null);
              setFolderParentForCreate({
                id: currentFolderId,
                name: currentFolder?.name ?? "Gốc kho tri thức",
              });
              setFolderFormOpen(true);
            }}
            title={
              canManage
                ? undefined
                : "Cần vai trò admin hoặc editor để tạo thư mục"
            }
          >
            <FolderPlus className="size-4 text-muted-foreground" />
            <span>Tạo thư mục</span>
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

          {canManage && collection ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="size-9 p-0 text-muted-foreground hover:text-foreground"
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
                <DropdownMenuSeparator />
                <LifecycleActions
                  workspaceId={workspaceId}
                  kind="collection"
                  resourceId={collection.id}
                  label={collection.name}
                  role={role?.kind}
                />
              </DropdownMenuContent>
            </DropdownMenu>
          ) : null}
        </div>
      </div>

      {/* Main File Explorer Workspace (Two Columns: Left Folder Tree, Right Content) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 min-h-[520px]">
        {/* Left Column: Folder Tree (Windows 11 Explorer Sidebar) */}
        <div className="lg:col-span-3 xl:col-span-3">
          <FolderTreePanel
            folders={folders}
            currentFolderId={currentFolderId}
            allFoldersActive={allFoldersActive}
            canManage={canManage}
            rootSourceCount={rootSourceCount}
            totalSourceCount={collection?.source_count ?? 0}
            onSelectFolder={(folderId, all) => {
              setCurrentFolderId(folderId);
              setAllFoldersActive(Boolean(all));
              onPageChange(1);
            }}
            onCreateFolder={() => {
              setFolderToEdit(null);
              setFolderParentForCreate({ id: null, name: "Gốc kho tri thức" });
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
              setMoveDialogState({
                open: true,
                itemType: "folder",
                itemId: f.id,
                itemTitle: f.name,
                currentFolderId: f.parent_id,
              });
            }}
            onDeleteFolder={(f) => {
              setDeleteFolderState({ open: true, folder: f });
            }}
          />
        </div>

        {/* Right Column: Files & Subfolders Explorer */}
        <div className="lg:col-span-9 xl:col-span-9 flex flex-col space-y-3">
          {/* Path Breadcrumbs Bar & View Controls */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-2 border-b border-border/40">
            {/* Current Path Bar */}
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground flex-wrap">
              <button
                type="button"
                className={cn(
                  "flex items-center gap-1 hover:text-foreground transition-colors",
                  !currentFolderId && !allFoldersActive && "font-semibold text-foreground",
                )}
                onClick={() => {
                  setCurrentFolderId(null);
                  setAllFoldersActive(false);
                  onPageChange(1);
                }}
              >
                <HardDrive className="size-3.5 text-primary" />
                <span>Gốc</span>
              </button>

              {allFoldersActive ? (
                <>
                  <ChevronRight className="size-3 text-muted-foreground/60" />
                  <span className="font-semibold text-foreground">Tất cả tài liệu</span>
                </>
              ) : (
                folderBreadcrumbs.map((crumb, idx) => {
                  const isLast = idx === folderBreadcrumbs.length - 1;
                  return (
                    <div key={crumb.id} className="flex items-center gap-1.5">
                      <ChevronRight className="size-3 text-muted-foreground/60" />
                      <button
                        type="button"
                        disabled={isLast}
                        className={cn(
                          "truncate max-w-[150px] transition-colors",
                          isLast
                            ? "font-semibold text-foreground cursor-default"
                            : "hover:text-foreground text-muted-foreground",
                        )}
                        onClick={() => {
                          setCurrentFolderId(crumb.id);
                          onPageChange(1);
                        }}
                      >
                        {crumb.name}
                      </button>
                    </div>
                  );
                })
              )}
            </div>

            {/* View Mode Toggle */}
            <div className="flex items-center gap-2 self-end sm:self-auto">
              <ViewModeToggle value={viewMode} onChange={setViewMode} />
            </div>
          </div>

          {/* Left-Right Split Filter Bar Pattern */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
            <div className="relative w-full sm:w-72">
              <Search className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="pl-8 text-xs h-8"
                placeholder="Tìm tài liệu theo tên..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            <div className="flex items-center gap-2">
              <Select
                value={typeFilter}
                onValueChange={(v) => setTypeFilter(v as "all" | "pdf" | "docx")}
              >
                <SelectTrigger className="text-xs h-8 w-28">
                  <SelectValue placeholder="Định dạng" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all" className="text-xs">
                    Tất cả định dạng
                  </SelectItem>
                  <SelectItem value="pdf" className="text-xs">
                    PDF (.pdf)
                  </SelectItem>
                  <SelectItem value="docx" className="text-xs">
                    Word (.docx)
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Subfolders in Current Folder (Folder Cards) */}
          {directSubfolders.length > 0 && !searchQuery.trim() ? (
            <div className="space-y-1.5">
              <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                Thư mục con ({directSubfolders.length})
              </span>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5">
                {directSubfolders.map((sub) => (
                  <div
                    key={sub.id}
                    role="button"
                    tabIndex={0}
                    className="group relative flex items-center justify-between rounded-lg border border-border/70 bg-card p-2.5 hover:border-primary/50 hover:bg-muted/40 transition-colors cursor-pointer select-none"
                    onClick={() => {
                      setCurrentFolderId(sub.id);
                      onPageChange(1);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        setCurrentFolderId(sub.id);
                        onPageChange(1);
                      }
                    }}
                  >
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <FolderIcon className="size-4 text-primary shrink-0 group-hover:scale-105 transition-transform" />
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-medium text-foreground truncate group-hover:text-primary">
                          {sub.name}
                        </p>
                        <p className="text-[10px] text-muted-foreground">
                          {sub.source_count} tài liệu
                        </p>
                      </div>
                    </div>

                    {canManage ? (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                          <button
                            type="button"
                            aria-label="Thao tác thư mục con"
                            className="size-6 p-0 opacity-0 group-hover:opacity-100 flex items-center justify-center rounded hover:bg-muted shrink-0"
                          >
                            <MoreVertical className="size-3 text-muted-foreground" />
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-40 text-xs">
                          <DropdownMenuItem
                            className="gap-2"
                            onClick={(e) => {
                              e.stopPropagation();
                              setFolderToEdit(sub);
                              setFolderFormOpen(true);
                            }}
                          >
                            <Pencil className="size-3.5" />
                            <span>Đổi tên</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="gap-2"
                            onClick={(e) => {
                              e.stopPropagation();
                              setMoveDialogState({
                                open: true,
                                itemType: "folder",
                                itemId: sub.id,
                                itemTitle: sub.name,
                                currentFolderId: sub.parent_id,
                              });
                            }}
                          >
                            <FolderIcon className="size-3.5" />
                            <span>Di chuyển</span>
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="gap-2 text-destructive focus:text-destructive"
                            onClick={(e) => {
                              e.stopPropagation();
                              setDeleteFolderState({ open: true, folder: sub });
                            }}
                          >
                            <Trash2 className="size-3.5" />
                            <span>Xóa thư mục</span>
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {/* Files List / Grid Area */}
          <div className="flex-1">
            {sourcesQuery.isLoading ? (
              <div className="space-y-2 py-4">
                <Skeleton className="h-10 w-full rounded" />
                <Skeleton className="h-10 w-full rounded" />
                <Skeleton className="h-10 w-full rounded" />
              </div>
            ) : sourcesQuery.isError ? (
              <ErrorState
                error={sourcesQuery.error}
                onRetry={() => void sourcesQuery.refetch()}
              />
            ) : sources.length === 0 ? (
              <Card className="rounded-xl border-dashed border-border/80">
                <CardContent className="py-10">
                  <EmptyState
                    icon={FileText}
                    title={
                      searchQuery.trim()
                        ? "Không tìm thấy tài liệu phù hợp"
                        : "Chưa có tài liệu nào"
                    }
                    description={
                      searchQuery.trim()
                        ? `Không có tài liệu nào khớp với từ khóa "${searchQuery}".`
                        : "Thư mục này hiện đang trống. Bạn có thể tải tài liệu hoặc tạo thư mục con mới."
                    }
                    action={
                      canManage && !searchQuery.trim()
                        ? {
                            label: "Tải tài liệu ngay",
                            onClick: () => setUploadOpen(true),
                          }
                        : undefined
                    }
                  />
                </CardContent>
              </Card>
            ) : viewMode === "grid" ? (
              /* Grid View for Files */
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                {sources.map((source) => (
                  <Card
                    key={source.id}
                    className="group rounded-lg border-border/70 hover:border-primary/50 transition-colors flex flex-col justify-between"
                  >
                    <CardContent className="p-3.5 flex flex-col justify-between h-full space-y-2">
                      <div className="space-y-2">
                        <div className="flex items-start justify-between gap-1.5">
                          <Link
                            to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId"
                            params={{
                              workspaceId,
                              collectionId,
                              sourceId: source.id,
                            }}
                            className="flex items-center gap-2 min-w-0 flex-1 hover:text-primary transition-colors"
                          >
                            <span className="flex size-7 items-center justify-center rounded bg-muted text-primary shrink-0">
                              <FileText className="size-4" />
                            </span>
                            <span className="text-xs font-semibold text-foreground truncate group-hover:text-primary">
                              {source.title}
                            </span>
                          </Link>

                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="size-6 p-0 text-muted-foreground hover:text-foreground shrink-0"
                              >
                                <MoreVertical className="size-3.5" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-44 text-xs">
                              <DropdownMenuItem asChild>
                                <Link
                                  to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId"
                                  params={{
                                    workspaceId,
                                    collectionId,
                                    sourceId: source.id,
                                  }}
                                  className="gap-2"
                                >
                                  <Eye className="size-3.5" />
                                  <span>Xem chi tiết</span>
                                </Link>
                              </DropdownMenuItem>
                              <DropdownMenuItem asChild>
                                <Link
                                  to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId/ocr"
                                  params={{
                                    workspaceId,
                                    collectionId,
                                    sourceId: source.id,
                                  }}
                                  className="gap-2"
                                >
                                  <Cpu className="size-3.5 text-primary" />
                                  <span>OCR & Hiệu đính</span>
                                </Link>
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                className="gap-2"
                                onClick={() => handleDownload(source)}
                                disabled={downloadingSourceId === source.id}
                              >
                                <Download className="size-3.5" />
                                <span>Tải xuống bản gốc</span>
                              </DropdownMenuItem>
                              {canManage ? (
                                <>
                                  <DropdownMenuItem
                                    className="gap-2"
                                    onClick={() =>
                                      setRenameSourceState({
                                        open: true,
                                        source,
                                      })
                                    }
                                  >
                                    <Pencil className="size-3.5" />
                                    <span>Đổi tên</span>
                                  </DropdownMenuItem>
                                  <DropdownMenuItem
                                    className="gap-2"
                                    onClick={() =>
                                      setMoveDialogState({
                                        open: true,
                                        itemType: "source",
                                        itemId: source.id,
                                        itemTitle: source.title,
                                        currentFolderId: source.folder_id,
                                      })
                                    }
                                  >
                                    <FolderIcon className="size-3.5" />
                                    <span>Di chuyển</span>
                                  </DropdownMenuItem>
                                  <DropdownMenuSeparator />
                                  <LifecycleActions
                                    workspaceId={workspaceId}
                                    kind="source"
                                    resourceId={source.id}
                                    label={source.title}
                                    role={role?.kind}
                                  />
                                </>
                              ) : null}
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>

                        <p className="text-[11px] text-muted-foreground truncate font-mono">
                          {source.file_name}
                        </p>
                      </div>

                      <div className="flex items-center justify-between pt-2 border-t border-border/40 text-[10px] text-muted-foreground">
                        <div className="flex items-center gap-1.5">
                          <Badge variant="outline" className="text-[10px] h-4 px-1 font-mono">
                            v{source.current_revision_no}
                          </Badge>
                          <span>{formatBytes(source.size_bytes)}</span>
                        </div>
                        <span>{formatDateTimeValue(source.updated_at || source.created_at)}</span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              /* Table View for Files */
              <Card className="rounded-xl shadow-2xs overflow-hidden border-border/70">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[40%]">Tên tài liệu</TableHead>
                        <TableHead className="w-[10%] text-center">Phiên bản</TableHead>
                        <TableHead className="w-[15%]">Kích thước</TableHead>
                        <TableHead className="w-[20%]">Ngày cập nhật</TableHead>
                        <TableHead className="w-[60px] text-right"></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {sources.map((source) => (
                        <TableRow key={source.id} className="group hover:bg-muted/40">
                          <TableCell className="font-medium">
                            <Link
                              to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId"
                              params={{
                                workspaceId,
                                collectionId,
                                sourceId: source.id,
                              }}
                              className="flex items-center gap-2.5 text-foreground hover:text-primary transition-colors"
                            >
                              <span className="flex size-6 items-center justify-center rounded bg-muted text-primary shrink-0">
                                <FileText className="size-3.5" />
                              </span>
                              <div className="min-w-0">
                                <p className="text-xs font-medium truncate text-foreground group-hover:text-primary">
                                  {source.title}
                                </p>
                                <p className="text-[10px] text-muted-foreground truncate font-mono">
                                  {source.file_name}
                                </p>
                              </div>
                            </Link>
                          </TableCell>
                          <TableCell className="text-center">
                            <Badge variant="outline" className="text-[10px] h-4 px-1.5 font-mono">
                              v{source.current_revision_no}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {formatBytes(source.size_bytes)}
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                            {formatDateTimeValue(source.updated_at || source.created_at)}
                          </TableCell>
                          <TableCell className="text-right">
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
                              <DropdownMenuContent align="end" className="w-44 text-xs">
                                <DropdownMenuItem asChild>
                                  <Link
                                    to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId"
                                    params={{
                                      workspaceId,
                                      collectionId,
                                      sourceId: source.id,
                                    }}
                                    className="gap-2"
                                  >
                                    <Eye className="size-3.5" />
                                    <span>Xem chi tiết</span>
                                  </Link>
                                </DropdownMenuItem>
                                <DropdownMenuItem asChild>
                                  <Link
                                    to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId/ocr"
                                    params={{
                                      workspaceId,
                                      collectionId,
                                      sourceId: source.id,
                                    }}
                                    className="gap-2"
                                  >
                                    <Cpu className="size-3.5 text-primary" />
                                    <span>OCR & Hiệu đính</span>
                                  </Link>
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  className="gap-2"
                                  onClick={() => handleDownload(source)}
                                  disabled={downloadingSourceId === source.id}
                                >
                                  <Download className="size-3.5" />
                                  <span>Tải xuống bản gốc</span>
                                </DropdownMenuItem>
                                {canManage ? (
                                  <>
                                    <DropdownMenuItem
                                      className="gap-2"
                                      onClick={() =>
                                        setRenameSourceState({
                                          open: true,
                                          source,
                                        })
                                      }
                                    >
                                      <Pencil className="size-3.5" />
                                      <span>Đổi tên</span>
                                    </DropdownMenuItem>
                                    <DropdownMenuItem
                                      className="gap-2"
                                      onClick={() =>
                                        setMoveDialogState({
                                          open: true,
                                          itemType: "source",
                                          itemId: source.id,
                                          itemTitle: source.title,
                                          currentFolderId: source.folder_id,
                                        })
                                      }
                                    >
                                      <FolderIcon className="size-3.5" />
                                      <span>Di chuyển</span>
                                    </DropdownMenuItem>
                                    <DropdownMenuSeparator />
                                    <LifecycleActions
                                      workspaceId={workspaceId}
                                      kind="source"
                                      resourceId={source.id}
                                      label={source.title}
                                      role={role?.kind}
                                    />
                                  </>
                                ) : null}
                              </DropdownMenuContent>
                            </DropdownMenu>
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
              <div className="pt-3">
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
              </div>
            ) : null}
          </div>
        </div>
      </div>

      {/* Upload Dialog */}
      <SourceUploadDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        workspaceId={workspaceId}
        collectionId={collectionId}
        folderId={allFoldersActive ? null : currentFolderId}
        onSuccess={() => {
          void sourcesQuery.refetch();
          void foldersQuery.refetch();
          void collectionQuery.refetch();
        }}
      />

      {/* Create / Edit Folder Dialog */}
      <FolderFormDialog
        open={folderFormOpen}
        onOpenChange={setFolderFormOpen}
        workspaceId={workspaceId}
        collectionId={collectionId}
        parentFolderId={folderParentForCreate.id}
        parentFolderName={folderParentForCreate.name}
        folderToEdit={folderToEdit}
        onSuccess={() => {
          void foldersQuery.refetch();
        }}
      />

      {/* Move Dialog (Folder or Source) */}
      <FolderMoveDialog
        open={moveDialogState.open}
        onOpenChange={(open) =>
          setMoveDialogState((prev) => ({ ...prev, open }))
        }
        workspaceId={workspaceId}
        collectionId={collectionId}
        itemType={moveDialogState.itemType}
        itemId={moveDialogState.itemId}
        itemTitle={moveDialogState.itemTitle}
        currentFolderId={moveDialogState.currentFolderId}
        onSuccess={() => {
          void sourcesQuery.refetch();
          void foldersQuery.refetch();
        }}
      />

      {/* Delete Folder Dialog */}
      <FolderDeleteDialog
        open={deleteFolderState.open}
        onOpenChange={(open) =>
          setDeleteFolderState((prev) => ({ ...prev, open }))
        }
        workspaceId={workspaceId}
        collectionId={collectionId}
        folder={deleteFolderState.folder}
        onSuccess={() => {
          if (currentFolderId === deleteFolderState.folder?.id) {
            setCurrentFolderId(null);
          }
          void foldersQuery.refetch();
          void sourcesQuery.refetch();
        }}
      />

      {/* Rename Source Dialog */}
      <SourceRenameDialog
        open={renameSourceState.open}
        onOpenChange={(open) =>
          setRenameSourceState((prev) => ({ ...prev, open }))
        }
        workspaceId={workspaceId}
        collectionId={collectionId}
        source={renameSourceState.source}
        onSuccess={() => {
          void sourcesQuery.refetch();
        }}
      />

      {/* Edit Collection Dialog */}
      {collection ? (
        <CollectionFormDialog
          open={editCollectionOpen}
          onOpenChange={setEditCollectionOpen}
          workspaceId={workspaceId}
          collectionToEdit={collection}
          onSuccess={() => {
            void collectionQuery.refetch();
          }}
        />
      ) : null}
    </div>
  );
}
