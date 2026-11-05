import {
  ChevronRight,
  Folder,
  HardDrive,
  Layers,
} from "lucide-react";
import type React from "react";
import type { FolderBreadcrumbItem, KBFolder } from "@/features/knowledge/types";
import { cn } from "@/lib/utils";

export interface KnowledgeBreadcrumbsProps {
  currentFolderId: string | null;
  allFoldersActive: boolean;
  parentFolder: KBFolder | null;
  folderBreadcrumbs: FolderBreadcrumbItem[];
  rootSourceCount: number;
  totalSourceCount: number;
  dragOverTargetId: string | null;
  draggingSourceId: string | null;
  onSelectFolder: (folderId: string | null) => void;
  onToggleAllFolders: () => void;
  onDragOverTarget: (
    e: React.DragEvent<HTMLElement>,
    targetId: string,
  ) => void;
  onDragLeaveTarget: (
    e: React.DragEvent<HTMLElement>,
    targetId: string,
  ) => void;
  onDropTarget: (
    e: React.DragEvent<HTMLElement>,
    targetFolderId: string | null,
    targetName: string,
  ) => void;
}

/**
 * Component thanh điều hướng Breadcrumb phong cách Google Drive cho Kho tri thức.
 * Hỗ trợ kéo - thả tệp trực tiếp lên "Gốc kho" hoặc thư mục cha để chuyển tệp ra ngoài.
 */
export function KnowledgeBreadcrumbs({
  currentFolderId,
  allFoldersActive,
  parentFolder: _parentFolder,
  folderBreadcrumbs,
  rootSourceCount,
  totalSourceCount,
  dragOverTargetId,
  draggingSourceId,
  onSelectFolder,
  onToggleAllFolders,
  onDragOverTarget,
  onDragLeaveTarget,
  onDropTarget,
}: KnowledgeBreadcrumbsProps) {
  const isInsideFolder = Boolean(currentFolderId && !allFoldersActive);

  return (
    <nav
      aria-label="Đường dẫn thư mục kho tri thức"
      className="flex items-center gap-1.5 text-sm text-muted-foreground flex-wrap min-w-0"
    >
      {/* Nút Gốc kho (Hỗ trợ Drop target để kéo tệp ra ngoài thư mục) */}
      <button
        type="button"
        onDragOver={(e) => {
          if (isInsideFolder) {
            onDragOverTarget(e, "root");
          }
        }}
        onDragLeave={(e) => {
          if (isInsideFolder) {
            onDragLeaveTarget(e, "root");
          }
        }}
        onDrop={(e) => {
          if (isInsideFolder) {
            onDropTarget(e, null, "Gốc kho tri thức");
          }
        }}
        onClick={() => onSelectFolder(null)}
        className={cn(
          "flex items-center gap-2 h-8.5 px-3 rounded-lg text-sm transition-all select-none border font-medium",
          !currentFolderId && !allFoldersActive
            ? "bg-accent/80 font-semibold text-accent-foreground border-border/60 shadow-2xs"
            : "text-muted-foreground hover:text-foreground hover:bg-muted/60 border-transparent",
          isInsideFolder &&
            draggingSourceId &&
            "border-dashed border-primary/50 bg-primary/5 text-primary",
          dragOverTargetId === "root" &&
            "ring-2 ring-primary border-primary bg-primary/20 text-primary font-semibold shadow-sm",
        )}
      >
        <HardDrive
          className={cn(
            "size-4 shrink-0",
            (!currentFolderId && !allFoldersActive) ||
              dragOverTargetId === "root"
              ? "text-primary"
              : "text-muted-foreground",
          )}
        />
        <span>Gốc kho</span>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-muted/80 text-muted-foreground">
          {rootSourceCount}
        </span>
      </button>

      {/* Danh sách đường dẫn thư mục cha & hiện tại */}
      {allFoldersActive ? (
        <>
          <ChevronRight className="size-4 text-muted-foreground/40 shrink-0" />
          <span className="font-semibold text-foreground flex items-center gap-1.5 h-8.5 px-3 rounded-lg bg-accent/80 border border-border/60 shadow-2xs text-sm">
            <Layers className="size-3.5 text-muted-foreground" />
            <span>Tất cả tài liệu</span>
          </span>
        </>
      ) : (
        folderBreadcrumbs.map((bc, idx) => {
          const isLast = idx === folderBreadcrumbs.length - 1;
          const isHovered = dragOverTargetId === bc.id;

          return (
            <div key={bc.id} className="flex items-center gap-1.5">
              <ChevronRight className="size-4 text-muted-foreground/40 shrink-0" />
              <button
                type="button"
                onDragOver={(e) => {
                  if (!isLast) {
                    onDragOverTarget(e, bc.id);
                  }
                }}
                onDragLeave={(e) => {
                  if (!isLast) {
                    onDragLeaveTarget(e, bc.id);
                  }
                }}
                onDrop={(e) => {
                  if (!isLast) {
                    onDropTarget(e, bc.id, bc.name);
                  }
                }}
                onClick={() => onSelectFolder(bc.id)}
                className={cn(
                  "flex items-center gap-2 h-8.5 px-3 rounded-lg text-sm transition-all select-none border",
                  isLast
                    ? "bg-accent/80 font-semibold text-accent-foreground border-border/60 shadow-2xs cursor-default"
                    : "font-medium text-muted-foreground hover:text-foreground hover:bg-muted/60 border-transparent cursor-pointer",
                  !isLast &&
                    draggingSourceId &&
                    "border-dashed border-primary/50 bg-primary/5 text-primary",
                  isHovered &&
                    "ring-2 ring-primary border-primary bg-primary/20 text-primary font-semibold shadow-sm",
                )}
              >
                <Folder className="size-4 text-amber-500 fill-amber-500/20 shrink-0" />
                <span className="truncate max-w-[220px]">{bc.name}</span>
              </button>
            </div>
          );
        })
      )}

      {/* Lối tắt Xem toàn bộ kho */}
      <button
        type="button"
        onClick={onToggleAllFolders}
        className={cn(
          "ml-2 h-8.5 px-3 rounded-full border text-xs font-medium transition-all flex items-center gap-1.5 select-none",
          allFoldersActive
            ? "border-primary bg-primary/10 text-primary font-semibold shadow-2xs"
            : "border-border/70 text-muted-foreground hover:text-foreground hover:bg-muted/40",
        )}
      >
        <Layers className="size-3.5" />
        <span>Xem toàn bộ ({totalSourceCount})</span>
      </button>
    </nav>
  );
}

