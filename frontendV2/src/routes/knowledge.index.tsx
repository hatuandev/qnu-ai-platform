import { createFileRoute, Link } from "@tanstack/react-router";
import {
  ArrowLeft,
  ChevronRight,
  FileText,
  Folder,
  FolderOpen,
  FolderPlus,
  Loader2,
  MoreHorizontal,
  Pencil,
  RefreshCw,
  Trash2,
  Upload,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import {
  useCollectionQuery,
  useCollectionsQuery,
  useFoldersQuery,
  useMoveFolderMutation,
  useMoveSourceMutation,
  useSourcesQuery,
} from "@/api/knowledge/queries";
import type {
  CollectionResponse,
  FolderResponse,
  SourceResponse,
} from "@/api/knowledge/types";
import { DebouncedSearchInput } from "@/components/admin/debounced-search-input";
import { DocumentTypeIcon } from "@/components/admin/document-file-icon";
import { EmptyState } from "@/components/admin/empty-state";
import { PageHeader } from "@/components/admin/page-header";
import { CollectionFormDialog } from "@/components/knowledge/collection-form-dialog";
import { FolderDeleteDialog } from "@/components/knowledge/folder-delete-dialog";
import { FolderFormDialog } from "@/components/knowledge/folder-form-dialog";
import { FolderMoveDialog } from "@/components/knowledge/folder-move-dialog";
import { LifecycleDeleteDialog } from "@/components/knowledge/lifecycle-delete-dialog";
import { SourceMoveDialog } from "@/components/knowledge/source-move-dialog";
import { SourceRenameDialog } from "@/components/knowledge/source-rename-dialog";
import { SourceUploadDialog } from "@/components/knowledge/source-upload-dialog";
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
import {
  type ViewMode,
  ViewModeToggle,
} from "@/components/ui/view-mode-toggle";
import { resolveSourceDisplayStatus } from "@/lib/knowledge-status";
import { useUiStore } from "@/lib/ui-store";
import { cn } from "@/lib/utils";

const knowledgeSearchSchema = z.object({
  collectionId: z.string().optional(),
  folderId: z.string().optional(),
  view: z.enum(["table", "grid"]).optional().catch("table"),
  page: z.number().int().positive().optional().catch(1),
  pageSize: z.number().int().positive().optional().catch(20),
});

export type DragPayload =
  | { type: "document"; doc: SourceResponse }
  | { type: "folder"; folder: FolderResponse };

export const Route = createFileRoute("/knowledge/")({
  validateSearch: (search) => knowledgeSearchSchema.parse(search),
  component: KnowledgePage,
});

function KnowledgePage() {
  const searchParams = Route.useSearch();
  const navigate = Route.useNavigate();

  const activeWorkspaceId = useUiStore((s) => s.activeWorkspaceId);

  const selectedCollectionId = searchParams.collectionId;
  const selectedFolderId = searchParams.folderId;
  const viewMode: ViewMode = (searchParams.view as ViewMode) || "table";
  const currentPage = searchParams.page || 1;
  const pageSize = searchParams.pageSize || 20;

  // Local filter for loaded items on page
  const [searchTerm, setSearchTerm] = useState("");

  // Dialog States
  const [createCollectionOpen, setCreateCollectionOpen] = useState(false);
  const [editingCollection, setEditingCollection] =
    useState<CollectionResponse | null>(null);

  const [createFolderOpen, setCreateFolderOpen] = useState(false);
  const [editingFolder, setEditingFolder] = useState<FolderResponse | null>(
    null,
  );
  const [movingFolder, setMovingFolder] = useState<FolderResponse | null>(null);
  const [deletingFolder, setDeletingFolder] = useState<FolderResponse | null>(
    null,
  );

  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [droppedFile, setDroppedFile] = useState<File | null>(null);
  const [isFullPageDragging, setIsFullPageDragging] = useState(false);

  const [renamingSource, setRenamingSource] = useState<SourceResponse | null>(
    null,
  );
  const [movingSource, setMovingSource] = useState<SourceResponse | null>(null);
  const [deletingSource, setDeletingSource] = useState<SourceResponse | null>(
    null,
  );

  // In-page Drag & Drop State
  const [dragPayload, setDragPayload] = useState<DragPayload | null>(null);
  const [dragOverFolderId, setDragOverFolderId] = useState<string | null>(null);
  const [isRootDropHovered, setIsRootDropHovered] = useState(false);

  const moveSourceMutation = useMoveSourceMutation(
    activeWorkspaceId,
    selectedCollectionId,
  );
  const moveFolderMutation = useMoveFolderMutation(
    activeWorkspaceId,
    selectedCollectionId,
  );

  // Queries
  const {
    data: collectionsPage,
    isLoading: isCollectionsLoading,
    isError: isCollectionsError,
    error: collectionsError,
    refetch: refetchCollections,
  } = useCollectionsQuery(activeWorkspaceId);

  const collections = useMemo(
    () => collectionsPage?.items || [],
    [collectionsPage],
  );

  // Auto-redirect if only 1 collection and none chosen
  const activeCollection = useMemo(() => {
    if (selectedCollectionId) {
      return collections.find((c) => c.id === selectedCollectionId) || null;
    }
    return null;
  }, [collections, selectedCollectionId]);

  // Query specific collection detail if not in list yet
  const { data: directCollection } = useCollectionQuery(
    activeWorkspaceId,
    selectedCollectionId,
  );

  const currentCollection = activeCollection || directCollection || null;

  // Query folders inside current collection
  const { data: folders = [], refetch: refetchFolders } = useFoldersQuery(
    activeWorkspaceId,
    selectedCollectionId,
  );

  // Active folder object if navigating inside a subfolder
  const currentFolder = useMemo(() => {
    if (!selectedFolderId || selectedFolderId === "root") return null;
    return folders.find((f) => f.id === selectedFolderId) || null;
  }, [folders, selectedFolderId]);

  // Query sources inside current collection/folder
  const {
    data: sourcesPage,
    isLoading: isSourcesLoading,
    isError: isSourcesError,
    error: sourcesError,
    refetch: refetchSources,
    isFetching: isSourcesFetching,
  } = useSourcesQuery(activeWorkspaceId, selectedCollectionId, {
    folderId: selectedFolderId || "root",
    allFolders: selectedFolderId === "all",
    page: currentPage,
    pageSize,
  });

  const sources = useMemo(() => sourcesPage?.items || [], [sourcesPage]);

  // Local search filter applied on the current page's sources
  const filteredSources = useMemo(() => {
    if (!searchTerm.trim()) return sources;
    const term = searchTerm.toLowerCase();
    return sources.filter(
      (s) =>
        s.title.toLowerCase().includes(term) ||
        s.file_name.toLowerCase().includes(term),
    );
  }, [sources, searchTerm]);

  // Filtered folders
  const currentLevelFolders = useMemo(() => {
    if (!selectedFolderId || selectedFolderId === "root") {
      return folders.filter((f) => !f.parent_id);
    }
    return folders.filter((f) => f.parent_id === selectedFolderId);
  }, [folders, selectedFolderId]);

  // Handlers
  const handleSelectCollection = (collectionId: string) => {
    void navigate({
      search: (prev) => ({
        ...prev,
        collectionId,
        folderId: undefined,
        page: 1,
      }),
    });
  };

  const handleSelectFolder = (folderId?: string) => {
    void navigate({
      search: (prev) => ({
        ...prev,
        folderId: folderId || undefined,
        page: 1,
      }),
    });
  };

  const handlePageChange = (newPage: number) => {
    void navigate({
      search: (prev) => ({
        ...prev,
        page: newPage,
      }),
    });
  };

  const handleViewModeChange = (newView: ViewMode) => {
    void navigate({
      search: (prev) => ({
        ...prev,
        view: newView,
      }),
    });
  };

  // In-page Drag and Drop handlers
  const handleDocDragStart = (e: React.DragEvent, doc: SourceResponse) => {
    setDragPayload({ type: "document", doc });
    e.dataTransfer.setData("application/qnu-doc-id", doc.id);
    e.dataTransfer.setData("application/qnu-type", "document");
    e.dataTransfer.effectAllowed = "move";
  };

  const handleFolderDragStart = (
    e: React.DragEvent,
    folder: FolderResponse,
  ) => {
    setDragPayload({ type: "folder", folder });
    e.dataTransfer.setData("application/qnu-folder-id", folder.id);
    e.dataTransfer.setData("application/qnu-type", "folder");
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragEnd = () => {
    setDragPayload(null);
    setDragOverFolderId(null);
    setIsRootDropHovered(false);
  };

  const handleFolderDragOver = (e: React.DragEvent, targetFolderId: string) => {
    if (!dragPayload) return;
    if (dragPayload.type === "document") {
      if (dragPayload.doc.folder_id === targetFolderId) return;
      e.preventDefault();
      e.stopPropagation();
      e.dataTransfer.dropEffect = "move";
      if (dragOverFolderId !== targetFolderId) {
        setDragOverFolderId(targetFolderId);
      }
    } else if (dragPayload.type === "folder") {
      if (dragPayload.folder.id === targetFolderId) return;
      e.preventDefault();
      e.stopPropagation();
      e.dataTransfer.dropEffect = "move";
      if (dragOverFolderId !== targetFolderId) {
        setDragOverFolderId(targetFolderId);
      }
    }
  };

  const handleFolderDragLeave = (
    e: React.DragEvent,
    targetFolderId: string,
  ) => {
    e.preventDefault();
    e.stopPropagation();
    if (dragOverFolderId === targetFolderId) {
      setDragOverFolderId(null);
    }
  };

  const handleFolderDrop = async (
    e: React.DragEvent,
    targetFolder: FolderResponse,
  ) => {
    e.preventDefault();
    e.stopPropagation();
    if (!dragPayload) return;

    if (dragPayload.type === "document") {
      const doc = dragPayload.doc;
      if (doc.folder_id !== targetFolder.id) {
        try {
          await moveSourceMutation.mutateAsync({
            sourceId: doc.id,
            data: { target_folder_id: targetFolder.id },
          });
          toast.success(
            `Đã chuyển "${doc.title}" vào thư mục "${targetFolder.name}"`,
          );
          void refetchSources();
          void refetchFolders();
        } catch (err: unknown) {
          const msg =
            err instanceof Error ? err.message : "Không thể di chuyển tài liệu";
          toast.error(msg);
        }
      }
    } else if (dragPayload.type === "folder") {
      const folder = dragPayload.folder;
      if (
        folder.id !== targetFolder.id &&
        folder.parent_id !== targetFolder.id
      ) {
        try {
          await moveFolderMutation.mutateAsync({
            folderId: folder.id,
            data: { target_parent_id: targetFolder.id },
          });
          toast.success(
            `Đã chuyển thư mục "${folder.name}" vào "${targetFolder.name}"`,
          );
          void refetchFolders();
        } catch (err: unknown) {
          const msg =
            err instanceof Error ? err.message : "Không thể di chuyển thư mục";
          toast.error(msg);
        }
      }
    }
    handleDragEnd();
  };

  const handleDropOnRoot = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsRootDropHovered(false);

    if (dragPayload?.type === "document") {
      const doc = dragPayload.doc;
      if (doc.folder_id !== null) {
        try {
          await moveSourceMutation.mutateAsync({
            sourceId: doc.id,
            data: { target_folder_id: null },
          });
          toast.success(`Đã chuyển "${doc.title}" về Gốc kho tri thức`);
          void refetchSources();
          void refetchFolders();
        } catch (err: unknown) {
          const msg =
            err instanceof Error
              ? err.message
              : "Không thể di chuyển tài liệu về gốc";
          toast.error(msg);
        }
      }
    }
    handleDragEnd();
  };

  // Full-page drag-and-drop
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (dragPayload) return;
    if (e.dataTransfer.types.includes("Files")) {
      setIsFullPageDragging(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    if (e.currentTarget.contains(e.relatedTarget as Node)) return;
    setIsFullPageDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsFullPageDragging(false);
    if (dragPayload) return;
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      setDroppedFile(files[0]);
      setUploadDialogOpen(true);
    }
  };

  // ==========================================
  // VIEW 1: Trang Danh sách Kho Tri Thức (Chưa chọn kho)
  // ==========================================
  if (!selectedCollectionId) {
    return (
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        <PageHeader
          eyebrow="Tài liệu & Dữ liệu"
          title="Kho tri thức"
          description="Quản lý các kho tài liệu văn bản phục vụ Trợ lý AI và tra cứu tri thức."
          actions={
            <Button
              size="sm"
              onClick={() => setCreateCollectionOpen(true)}
              className="h-8 gap-1.5 text-xs shadow-2xs"
            >
              <FolderPlus className="size-3.5" />
              <span>Tạo kho mới</span>
            </Button>
          }
        />

        {isCollectionsLoading ? (
          <div className="py-16 flex flex-col items-center justify-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="size-6 animate-spin text-primary" />
            <span>Đang tải danh sách kho tri thức của đơn vị...</span>
          </div>
        ) : isCollectionsError ? (
          <EmptyState
            title="Không thể tải kho tri thức"
            description={collectionsError?.message || "Lỗi kết nối máy chủ"}
            action={{
              label: "Thử lại",
              onClick: () => {
                void refetchCollections();
              },
            }}
          />
        ) : collections.length === 0 ? (
          <EmptyState
            title="Đơn vị chưa có kho tri thức nào"
            description="Tạo kho tri thức đầu tiên để bắt đầu lưu trữ và bóc tách tài liệu phục vụ hỏi đáp."
            action={{
              label: "Tạo kho đầu tiên",
              onClick: () => setCreateCollectionOpen(true),
            }}
          />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {collections.map((col) => (
              <Card
                key={col.id}
                className="group border border-border/70 hover:border-primary/50 transition-all shadow-2xs hover:shadow-xs flex flex-col justify-between"
              >
                <CardContent className="p-4 space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="size-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                        <Folder className="size-4" />
                      </div>
                      <Link
                        to="/knowledge"
                        search={{ collectionId: col.id }}
                        className="text-sm font-semibold text-foreground hover:text-primary transition-colors truncate"
                        title={col.name}
                      >
                        {col.name}
                      </Link>
                    </div>

                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="size-7 p-0 text-muted-foreground hover:text-foreground"
                          aria-label="Thao tác"
                        >
                          <MoreHorizontal className="size-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-44 text-xs">
                        <DropdownMenuItem
                          onClick={() => handleSelectCollection(col.id)}
                          className="gap-2"
                        >
                          <FolderOpen className="size-3.5" />
                          <span>Mở kho tri thức</span>
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => setEditingCollection(col)}
                          className="gap-2"
                        >
                          <Pencil className="size-3.5" />
                          <span>Chỉnh sửa thông tin</span>
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>

                  <p className="text-xs text-muted-foreground line-clamp-2 min-h-8">
                    {col.description ||
                      "Kho lưu trữ văn bản và dữ liệu trích xuất."}
                  </p>

                  <div className="flex items-center justify-between pt-2 border-t border-border/60 text-[11px] text-muted-foreground">
                    <Badge
                      variant="secondary"
                      className="text-[10px] h-4 px-1.5 font-mono"
                    >
                      {col.source_count} tài liệu
                    </Badge>
                    <Link
                      to="/knowledge"
                      search={{ collectionId: col.id }}
                      className="font-medium text-primary hover:underline flex items-center gap-0.5"
                    >
                      <span>Mở kho</span>
                      <ChevronRight className="size-3" />
                    </Link>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        <CollectionFormDialog
          open={createCollectionOpen || Boolean(editingCollection)}
          onOpenChange={(open) => {
            if (!open) {
              setCreateCollectionOpen(false);
              setEditingCollection(null);
            }
          }}
          workspaceId={activeWorkspaceId || ""}
          collection={editingCollection}
          onSuccess={(item) => {
            void refetchCollections();
            if (!editingCollection) {
              handleSelectCollection(item.id);
            }
          }}
        />
      </div>
    );
  }

  // ==========================================
  // VIEW 2: Trang Bên Trong Kho Tri Thức (Thư mục & Tài liệu thật)
  // ==========================================
  const totalSources = sourcesPage?.meta?.total ?? sources.length;
  const totalPages = Math.ceil(totalSources / pageSize) || 1;

  return (
    <section
      aria-label="Khu vực quản lý kho tri thức"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className="p-6 max-w-7xl mx-auto space-y-6 min-h-screen relative"
    >
      {/* Full-page Drag & Drop Overlay */}
      {isFullPageDragging && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex flex-col items-center justify-center p-8 animate-in fade-in-0 duration-150">
          <div className="flex flex-col items-center max-w-md text-center p-10 rounded-2xl border-2 border-dashed border-primary bg-primary/5 shadow-xl">
            <div className="size-16 rounded-full bg-primary/10 text-primary flex items-center justify-center mb-4 ring-8 ring-primary/5 animate-pulse">
              <Upload className="size-8" />
            </div>
            <h3 className="text-base font-semibold text-foreground">
              Thả tệp vào đây để tải vào kho
            </h3>
            <p className="text-xs text-muted-foreground mt-2">
              Hệ thống sẽ tải tệp lên và tự động khởi chạy tiến trình bóc tách
              AI.
            </p>
            <div className="mt-4 text-[11px] text-primary font-medium bg-primary/10 px-3 py-1 rounded-full">
              Hỗ trợ .DOCX, .PDF, .XLSX (Tối đa 60 MB)
            </div>
          </div>
        </div>
      )}

      {/* 1. Page Header with Back button and 1 Primary CTA */}
      <div className="flex items-start gap-3">
        <Button
          asChild
          variant="outline"
          size="sm"
          onDragOver={(e) => {
            if (dragPayload?.type === "document") {
              e.preventDefault();
              e.stopPropagation();
              e.dataTransfer.dropEffect = "move";
              setIsRootDropHovered(true);
            }
          }}
          onDragLeave={() => setIsRootDropHovered(false)}
          onDrop={(e) => void handleDropOnRoot(e)}
          className={cn(
            "size-8 p-0 text-muted-foreground hover:text-foreground shrink-0 mt-1 shadow-2xs transition-all",
            isRootDropHovered &&
              "border-primary bg-primary/20 text-primary ring-2 ring-primary",
          )}
        >
          <Link
            to="/knowledge"
            search={{ collectionId: undefined, folderId: undefined }}
            title="Quay lại danh sách kho tri thức"
          >
            <ArrowLeft className="size-4" />
          </Link>
        </Button>

        <div className="flex-1 min-w-0">
          <PageHeader
            eyebrow={
              currentFolder
                ? `Kho: ${currentCollection?.name || ""}`
                : "Kho tri thức"
            }
            title={
              currentFolder
                ? currentFolder.name
                : currentCollection?.name || "Kho tri thức"
            }
            description={
              currentCollection?.description ||
              "Quản lý tệp tài liệu và chuẩn bị dữ liệu tri thức phục vụ Trợ lý AI."
            }
            actions={
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCreateFolderOpen(true)}
                  className="h-8 gap-1.5 text-xs"
                >
                  <FolderPlus className="size-3.5" />
                  <span>Thư mục mới</span>
                </Button>
                <Button
                  size="sm"
                  onClick={() => {
                    setDroppedFile(null);
                    setUploadDialogOpen(true);
                  }}
                  className="h-8 gap-1.5 text-xs shadow-2xs"
                >
                  <Upload className="size-3.5" />
                  <span>Tải tài liệu</span>
                </Button>
              </div>
            }
          />
        </div>
      </div>

      {/* 2. Flat Filter Bar (Không bọc Card, Không hộp trong hộp) */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pb-2 border-b border-border/60">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
          <DebouncedSearchInput
            value={searchTerm}
            onChange={setSearchTerm}
            placeholder="Tìm theo tên tài liệu trong trang..."
            className="w-full sm:w-72"
          />
          {searchTerm && (
            <span className="text-[11px] text-muted-foreground">
              (Lọc trên {sources.length} tài liệu của trang)
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              void refetchFolders();
              void refetchSources();
            }}
            disabled={isSourcesFetching}
            className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground gap-1"
            title="Làm mới dữ liệu từ máy chủ"
          >
            <RefreshCw
              className={cn("size-3.5", isSourcesFetching && "animate-spin")}
            />
            <span className="hidden sm:inline">Làm mới</span>
          </Button>
          <ViewModeToggle value={viewMode} onChange={handleViewModeChange} />
        </div>
      </div>

      {/* 3. Folders Section (Lưới thư mục thật) */}
      {currentLevelFolders.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs font-semibold text-foreground px-0.5">
            <div className="flex items-center gap-1.5">
              <Folder className="size-3.5 text-primary" />
              <span>Thư mục ({currentLevelFolders.length})</span>
            </div>
            {selectedFolderId && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleSelectFolder(undefined)}
                className="h-6 px-2 text-[11px] text-primary gap-1"
              >
                <ArrowLeft className="size-3" />
                <span>Về thư mục gốc</span>
              </Button>
            )}
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2.5">
            {currentLevelFolders.map((f) => {
              const isFolderHovered = dragOverFolderId === f.id;
              const isBeingDragged =
                dragPayload?.type === "folder" &&
                dragPayload.folder.id === f.id;

              return (
                <button
                  type="button"
                  key={f.id}
                  draggable={true}
                  onDragStart={(e) => handleFolderDragStart(e, f)}
                  onDragEnd={handleDragEnd}
                  onDragOver={(e) => handleFolderDragOver(e, f.id)}
                  onDragLeave={(e) => handleFolderDragLeave(e, f.id)}
                  onDrop={(e) => void handleFolderDrop(e, f)}
                  onClick={() => handleSelectFolder(f.id)}
                  className={cn(
                    "group relative flex items-center justify-between p-2.5 rounded-lg border bg-card transition-all cursor-pointer shadow-2xs text-left w-full select-none",
                    isFolderHovered
                      ? "border-primary bg-primary/10 ring-2 ring-primary/20 scale-[1.02]"
                      : dragPayload
                        ? "border-dashed border-primary/40 hover:border-primary/80"
                        : "border-border/70 hover:bg-muted/40 hover:border-primary/40",
                    isBeingDragged
                      ? "opacity-40 border-dashed border-primary"
                      : "",
                  )}
                >
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <div
                      className={cn(
                        "size-6 rounded flex items-center justify-center shrink-0 transition-colors",
                        isFolderHovered
                          ? "bg-primary text-primary-foreground shadow-xs"
                          : "text-primary",
                      )}
                    >
                      {isFolderHovered ? (
                        <FolderOpen className="size-4" />
                      ) : (
                        <Folder className="size-4" />
                      )}
                    </div>
                    <span className="text-xs font-medium text-foreground truncate">
                      {f.name}
                    </span>
                  </div>

                  {isFolderHovered && (
                    <Badge
                      variant="outline"
                      className="absolute -top-2.5 right-2 bg-primary text-primary-foreground text-[9px] h-4 px-1.5 font-medium border-none shadow-xs animate-in zoom-in-90"
                    >
                      {dragPayload?.type === "document"
                        ? "Thả tệp vào đây"
                        : "Chuyển vào đây"}
                    </Badge>
                  )}

                  <DropdownMenu>
                    <DropdownMenuTrigger
                      asChild
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Button
                        variant="ghost"
                        size="sm"
                        className="size-6 p-0 text-muted-foreground hover:text-foreground opacity-60 group-hover:opacity-100"
                      >
                        <MoreHorizontal className="size-3.5" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-40 text-xs">
                      <DropdownMenuItem
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingFolder(f);
                        }}
                        className="gap-2"
                      >
                        <Pencil className="size-3.5" />
                        <span>Đổi tên</span>
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={(e) => {
                          e.stopPropagation();
                          setMovingFolder(f);
                        }}
                        className="gap-2"
                      >
                        <span>Di chuyển</span>
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onClick={(e) => {
                          e.stopPropagation();
                          setDeletingFolder(f);
                        }}
                        className="gap-2 text-destructive focus:text-destructive focus:bg-destructive/10"
                      >
                        <Trash2 className="size-3.5" />
                        <span>Xóa thư mục</span>
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Subfolder Drop-out Zone when user is dragging a file inside a subfolder */}
      {dragPayload?.type === "document" && selectedFolderId && (
        <section
          aria-label="Khu vực thả tệp về thư mục gốc"
          onDragOver={(e) => {
            e.preventDefault();
            e.stopPropagation();
            e.dataTransfer.dropEffect = "move";
            setIsRootDropHovered(true);
          }}
          onDragLeave={() => setIsRootDropHovered(false)}
          onDrop={(e) => void handleDropOnRoot(e)}
          className={cn(
            "w-full p-2.5 rounded-lg border-2 border-dashed flex items-center justify-center gap-2 text-xs font-medium transition-all animate-in fade-in-0 duration-150 select-none cursor-pointer",
            isRootDropHovered
              ? "border-primary bg-primary/20 text-primary ring-2 ring-primary/30 scale-[1.01]"
              : "border-primary/50 bg-primary/5 text-primary hover:bg-primary/10",
          )}
        >
          <FolderOpen className="size-4 animate-bounce" />
          <span>
            Thả vào đây để đưa tệp "{dragPayload.doc.title}" về Gốc kho tri thức
          </span>
        </section>
      )}

      {/* 4. Sources Section (Bảng hoặc Lưới tài liệu thật) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs font-semibold text-foreground px-0.5">
          <span>Tài liệu lưu trữ ({totalSources})</span>
          {selectedFolderId && (
            <Button
              variant="link"
              size="sm"
              onClick={() => handleSelectFolder(undefined)}
              className="h-auto p-0 text-[11px] text-muted-foreground hover:text-primary"
            >
              Hiện tất cả tài liệu
            </Button>
          )}
        </div>

        {isSourcesLoading ? (
          <div className="py-16 flex flex-col items-center justify-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="size-6 animate-spin text-primary" />
            <span>Đang tải danh sách tài liệu...</span>
          </div>
        ) : isSourcesError ? (
          <EmptyState
            title="Không thể tải tài liệu"
            description={sourcesError?.message || "Lỗi kết nối máy chủ"}
            action={{
              label: "Thử lại",
              onClick: () => {
                void refetchSources();
              },
            }}
          />
        ) : filteredSources.length === 0 ? (
          <EmptyState
            title={
              searchTerm
                ? "Không tìm thấy tài liệu phù hợp"
                : "Chưa có tài liệu nào trong thư mục này"
            }
            description={
              searchTerm
                ? "Thử tìm với từ khóa khác hoặc xóa bộ lọc."
                : "Tải tệp Word, PDF hoặc Excel lên để hệ thống bắt đầu bóc tách."
            }
            action={
              !searchTerm
                ? {
                    label: "Tải tài liệu ngay",
                    onClick: () => {
                      setDroppedFile(null);
                      setUploadDialogOpen(true);
                    },
                  }
                : undefined
            }
          />
        ) : viewMode === "table" ? (
          /* TABLE VIEW */
          <div className="rounded-lg border border-border/70 overflow-hidden bg-card shadow-2xs">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40 hover:bg-muted/40 text-xs">
                  <TableHead className="w-12 text-center">Loại</TableHead>
                  <TableHead>Tên tài liệu</TableHead>
                  <TableHead className="w-28">Trạng thái</TableHead>
                  <TableHead className="w-24 text-right">Dung lượng</TableHead>
                  <TableHead className="w-24 text-center">
                    Bản sửa đổi
                  </TableHead>
                  <TableHead className="w-36">Cập nhật</TableHead>
                  <TableHead className="w-12 text-right"> </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredSources.map((doc) => {
                  const statusInfo = resolveSourceDisplayStatus(doc);
                  const isDocBeingDragged =
                    dragPayload?.type === "document" &&
                    dragPayload.doc.id === doc.id;

                  return (
                    <TableRow
                      key={doc.id}
                      draggable={true}
                      onDragStart={(e) => handleDocDragStart(e, doc)}
                      onDragEnd={handleDragEnd}
                      onClick={() =>
                        void navigate({
                          to: "/knowledge/$sourceId",
                          params: { sourceId: doc.id },
                          search: { collectionId: selectedCollectionId },
                        })
                      }
                      className={cn(
                        "group cursor-pointer text-xs hover:bg-muted/40 transition-colors select-none",
                        isDocBeingDragged
                          ? "opacity-40 bg-primary/10 border-dashed border-primary"
                          : "cursor-grab active:cursor-grabbing",
                      )}
                    >
                      {/* Cột 1: Icon loại tệp */}
                      <TableCell
                        className="text-center"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="flex justify-center">
                          <DocumentTypeIcon
                            fileName={doc.file_name}
                            className="size-4"
                          />
                        </div>
                      </TableCell>

                      {/* Cột 2: Tên tài liệu */}
                      <TableCell className="font-medium text-foreground">
                        <Link
                          to="/knowledge/$sourceId"
                          params={{ sourceId: doc.id }}
                          search={{ collectionId: selectedCollectionId }}
                          onClick={(e) => e.stopPropagation()}
                          className="hover:text-primary transition-colors truncate block max-w-md"
                          title={doc.title}
                        >
                          {doc.title}
                        </Link>
                        <span className="text-[10px] text-muted-foreground font-mono truncate block">
                          {doc.file_name}
                        </span>
                      </TableCell>

                      {/* Cột 3: Trạng thái vòng đời */}
                      <TableCell>
                        <Badge
                          variant={statusInfo.variant}
                          className="text-[10px] font-normal h-4 px-1.5"
                          title={statusInfo.hint}
                        >
                          {statusInfo.label}
                        </Badge>
                      </TableCell>

                      {/* Cột 4: Dung lượng */}
                      <TableCell className="text-right text-muted-foreground font-mono">
                        {(doc.size_bytes / 1024).toFixed(1)} KB
                      </TableCell>

                      {/* Cột 5: Phiên bản */}
                      <TableCell className="text-center font-mono text-muted-foreground">
                        v{doc.current_revision_no}
                      </TableCell>

                      {/* Cột 6: Ngày cập nhật */}
                      <TableCell className="text-muted-foreground text-[11px]">
                        {new Date(doc.updated_at).toLocaleDateString("vi-VN", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </TableCell>

                      {/* Cột 7: Menu ⋯ duy nhất */}
                      <TableCell
                        className="text-right"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="size-7 p-0 text-muted-foreground hover:text-foreground"
                              aria-label="Thao tác"
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
                                  to: "/knowledge/$sourceId",
                                  params: { sourceId: doc.id },
                                  search: {
                                    collectionId: selectedCollectionId,
                                  },
                                })
                              }
                              className="gap-2 font-medium"
                            >
                              <FileText className="size-3.5 text-primary" />
                              <span>Chi tiết & Biên soạn</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => setRenamingSource(doc)}
                              className="gap-2"
                            >
                              <Pencil className="size-3.5" />
                              <span>Đổi tên tài liệu</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => setMovingSource(doc)}
                              className="gap-2"
                            >
                              <Folder className="size-3.5" />
                              <span>Di chuyển</span>
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() => setDeletingSource(doc)}
                              className="gap-2 text-destructive focus:text-destructive focus:bg-destructive/10"
                            >
                              <Trash2 className="size-3.5" />
                              <span>Xóa tài liệu</span>
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        ) : (
          /* GRID VIEW */
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {filteredSources.map((doc) => {
              const statusInfo = resolveSourceDisplayStatus(doc);
              const isDocBeingDragged =
                dragPayload?.type === "document" &&
                dragPayload.doc.id === doc.id;

              return (
                <Card
                  key={doc.id}
                  draggable={true}
                  onDragStart={(e) => handleDocDragStart(e, doc)}
                  onDragEnd={handleDragEnd}
                  onClick={() =>
                    void navigate({
                      to: "/knowledge/$sourceId",
                      params: { sourceId: doc.id },
                      search: { collectionId: selectedCollectionId },
                    })
                  }
                  className={cn(
                    "group border border-border/70 hover:border-primary/50 transition-all cursor-pointer shadow-2xs hover:shadow-xs flex flex-col justify-between select-none",
                    isDocBeingDragged
                      ? "opacity-40 scale-95 border-dashed border-primary ring-2 ring-primary/20"
                      : "cursor-grab active:cursor-grabbing",
                  )}
                >
                  <CardContent className="p-3.5 space-y-2.5">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <DocumentTypeIcon
                          fileName={doc.file_name}
                          className="size-5 shrink-0"
                        />
                        <Link
                          to="/knowledge/$sourceId"
                          params={{ sourceId: doc.id }}
                          search={{ collectionId: selectedCollectionId }}
                          onClick={(e) => e.stopPropagation()}
                          className="text-xs font-semibold text-foreground hover:text-primary transition-colors truncate block"
                          title={doc.title}
                        >
                          {doc.title}
                        </Link>
                      </div>

                      <DropdownMenu>
                        <DropdownMenuTrigger
                          asChild
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Button
                            variant="ghost"
                            size="sm"
                            className="size-6 p-0 text-muted-foreground hover:text-foreground shrink-0"
                          >
                            <MoreHorizontal className="size-3.5" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent
                          align="end"
                          className="w-44 text-xs"
                        >
                          <DropdownMenuItem
                            onClick={() =>
                              void navigate({
                                to: "/knowledge/$sourceId",
                                params: { sourceId: doc.id },
                                search: { collectionId: selectedCollectionId },
                              })
                            }
                            className="gap-2"
                          >
                            <FileText className="size-3.5" />
                            <span>Chi tiết & Biên tập</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => setRenamingSource(doc)}
                            className="gap-2"
                          >
                            <Pencil className="size-3.5" />
                            <span>Đổi tên</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => setMovingSource(doc)}
                            className="gap-2"
                          >
                            <Folder className="size-3.5" />
                            <span>Di chuyển</span>
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={() => setDeletingSource(doc)}
                            className="gap-2 text-destructive focus:text-destructive focus:bg-destructive/10"
                          >
                            <Trash2 className="size-3.5" />
                            <span>Xóa</span>
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>

                    <div className="text-[10px] text-muted-foreground font-mono truncate">
                      {doc.file_name}
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-border/60 text-[11px]">
                      <Badge
                        variant={statusInfo.variant}
                        className="text-[9px] font-normal h-3.5 px-1.5"
                      >
                        {statusInfo.label}
                      </Badge>
                      <span className="text-muted-foreground font-mono">
                        {(doc.size_bytes / 1024).toFixed(1)} KB
                      </span>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* Server-based Pagination */}
        {totalSources > pageSize && (
          <div className="flex items-center justify-between pt-2 text-xs text-muted-foreground">
            <span>
              Trang {currentPage} / {totalPages} (Tổng {totalSources} tài liệu)
            </span>
            <div className="flex items-center gap-1.5">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage <= 1}
                className="h-7 px-2.5 text-xs"
              >
                Trước
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage >= totalPages}
                className="h-7 px-2.5 text-xs"
              >
                Sau
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* DIALOGS */}
      <FolderFormDialog
        open={createFolderOpen || Boolean(editingFolder)}
        onOpenChange={(open) => {
          if (!open) {
            setCreateFolderOpen(false);
            setEditingFolder(null);
          }
        }}
        workspaceId={activeWorkspaceId || ""}
        collectionId={selectedCollectionId}
        parentFolderId={selectedFolderId}
        folder={editingFolder}
        onSuccess={() => void refetchFolders()}
      />

      <FolderMoveDialog
        open={Boolean(movingFolder)}
        onOpenChange={(open) => !open && setMovingFolder(null)}
        workspaceId={activeWorkspaceId || ""}
        collectionId={selectedCollectionId}
        folder={movingFolder}
        onSuccess={() => void refetchFolders()}
      />

      <FolderDeleteDialog
        open={Boolean(deletingFolder)}
        onOpenChange={(open) => !open && setDeletingFolder(null)}
        workspaceId={activeWorkspaceId || ""}
        collectionId={selectedCollectionId}
        folder={deletingFolder}
        onSuccess={() => void refetchFolders()}
      />

      <SourceUploadDialog
        open={uploadDialogOpen}
        onOpenChange={setUploadDialogOpen}
        workspaceId={activeWorkspaceId || ""}
        collectionId={selectedCollectionId}
        folders={folders}
        defaultFolderId={selectedFolderId}
        initialFile={droppedFile}
        onSuccess={() => {
          void refetchSources();
          void refetchCollections();
        }}
      />

      <SourceRenameDialog
        open={Boolean(renamingSource)}
        onOpenChange={(open) => !open && setRenamingSource(null)}
        workspaceId={activeWorkspaceId || ""}
        collectionId={selectedCollectionId}
        source={renamingSource}
        onSuccess={() => void refetchSources()}
      />

      <SourceMoveDialog
        open={Boolean(movingSource)}
        onOpenChange={(open) => !open && setMovingSource(null)}
        workspaceId={activeWorkspaceId || ""}
        collectionId={selectedCollectionId}
        source={movingSource}
        onSuccess={() => void refetchSources()}
      />

      <LifecycleDeleteDialog
        open={Boolean(deletingSource)}
        onOpenChange={(open) => !open && setDeletingSource(null)}
        workspaceId={activeWorkspaceId || ""}
        sourceId={deletingSource?.id || null}
        sourceTitle={deletingSource?.title || ""}
        onSuccess={() => {
          void refetchSources();
          void refetchCollections();
        }}
      />
    </section>
  );
}
