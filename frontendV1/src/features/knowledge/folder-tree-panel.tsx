import {
  ChevronDown,
  ChevronRight,
  Folder,
  FolderOpen,
  FolderPlus,
  HardDrive,
  Layers,
  MoreVertical,
  Pencil,
  Trash2,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { KBFolder } from "@/features/knowledge/types";
import { cn } from "@/lib/utils";

interface TreeNode {
  folder: KBFolder;
  children: TreeNode[];
}

export function FolderTreePanel({
  folders,
  currentFolderId,
  allFoldersActive,
  canManage,
  rootSourceCount,
  totalSourceCount,
  onSelectFolder,
  onCreateFolder,
  onCreateSubfolder,
  onRenameFolder,
  onMoveFolder,
  onDeleteFolder,
}: {
  folders: KBFolder[];
  currentFolderId?: string | null;
  allFoldersActive?: boolean;
  canManage: boolean;
  rootSourceCount: number;
  totalSourceCount: number;
  onSelectFolder: (folderId: string | null, allFolders?: boolean) => void;
  onCreateFolder: () => void;
  onCreateSubfolder: (parent: KBFolder) => void;
  onRenameFolder: (folder: KBFolder) => void;
  onMoveFolder: (folder: KBFolder) => void;
  onDeleteFolder: (folder: KBFolder) => void;
}) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  // Build tree from flat folder list
  const tree = useMemo(() => {
    const map = new Map<string, TreeNode>();
    for (const f of folders) {
      map.set(f.id, { folder: f, children: [] });
    }
    const roots: TreeNode[] = [];
    for (const f of folders) {
      const node = map.get(f.id)!;
      if (f.parent_id && map.has(f.parent_id)) {
        map.get(f.parent_id)!.children.push(node);
      } else {
        roots.push(node);
      }
    }
    return roots;
  }, [folders]);

  const toggleExpand = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const renderNode = (node: TreeNode, depth = 0) => {
    const { folder, children } = node;
    const hasChildren = children.length > 0;
    const isExpanded = expandedIds.has(folder.id);
    const isSelected = !allFoldersActive && currentFolderId === folder.id;

    return (
      <div key={folder.id} className="space-y-0.5 select-none">
        <div
          role="button"
          tabIndex={0}
          className={cn(
            "group relative flex items-center justify-between rounded-md px-2 py-1.5 text-xs transition-colors cursor-pointer",
            isSelected
              ? "bg-accent font-semibold text-accent-foreground"
              : "hover:bg-muted/60 text-muted-foreground hover:text-foreground",
          )}
          style={{ paddingLeft: `${Math.max(8, depth * 16 + 8)}px` }}
          onClick={() => onSelectFolder(folder.id, false)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              onSelectFolder(folder.id, false);
            }
          }}
        >
          <div className="flex items-center gap-1.5 min-w-0 flex-1">
            {hasChildren ? (
              <button
                type="button"
                className="size-4 shrink-0 flex items-center justify-center rounded hover:bg-muted"
                onClick={(e) => toggleExpand(folder.id, e)}
              >
                {isExpanded ? (
                  <ChevronDown className="size-3 text-muted-foreground" />
                ) : (
                  <ChevronRight className="size-3 text-muted-foreground" />
                )}
              </button>
            ) : (
              <span className="size-4 shrink-0" />
            )}
            {isExpanded || isSelected ? (
              <FolderOpen className="size-3.5 shrink-0 text-primary" />
            ) : (
              <Folder className="size-3.5 shrink-0 text-muted-foreground group-hover:text-primary transition-colors" />
            )}
            <span className="truncate">{folder.name}</span>
          </div>

          <div className="flex items-center gap-1 shrink-0 ml-1">
            {folder.source_count > 0 ? (
              <span className="text-[10px] text-muted-foreground px-1">
                {folder.source_count}
              </span>
            ) : null}

            {canManage ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                  <button
                    type="button"
                    aria-label="Thao tác thư mục"
                    className="size-5 shrink-0 opacity-0 group-hover:opacity-100 flex items-center justify-center rounded hover:bg-muted transition-opacity"
                  >
                    <MoreVertical className="size-3 text-muted-foreground" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-44 text-xs">
                  <DropdownMenuItem
                    onClick={(e) => {
                      e.stopPropagation();
                      onCreateSubfolder(folder);
                    }}
                    className="gap-2"
                  >
                    <FolderPlus className="size-3.5" />
                    <span>Tạo thư mục con</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={(e) => {
                      e.stopPropagation();
                      onRenameFolder(folder);
                    }}
                    className="gap-2"
                  >
                    <Pencil className="size-3.5" />
                    <span>Đổi tên</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={(e) => {
                      e.stopPropagation();
                      onMoveFolder(folder);
                    }}
                    className="gap-2"
                  >
                    <Folder className="size-3.5" />
                    <span>Di chuyển</span>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteFolder(folder);
                    }}
                    className="gap-2 text-destructive focus:text-destructive"
                  >
                    <Trash2 className="size-3.5" />
                    <span>Xóa thư mục</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : null}
          </div>
        </div>

        {hasChildren && isExpanded ? (
          <div>{children.map((child) => renderNode(child, depth + 1))}</div>
        ) : null}
      </div>
    );
  };

  const isRootSelected = !allFoldersActive && (currentFolderId === null || currentFolderId === "root");

  return (
    <div className="flex flex-col h-full bg-card/50 rounded-lg border border-border/70 p-2.5">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 mb-1.5 border-b border-border/50 px-1">
        <span className="text-xs font-semibold text-foreground tracking-tight uppercase">
          Thư mục
        </span>
        {canManage ? (
          <Button
            size="sm"
            variant="ghost"
            className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
            onClick={onCreateFolder}
            title="Tạo thư mục ở gốc"
          >
            <FolderPlus className="size-3.5" />
          </Button>
        ) : null}
      </div>

      {/* Tree Content */}
      <div className="flex-1 overflow-y-auto space-y-0.5 pr-0.5">
        {/* Root node */}
        <div
          role="button"
          tabIndex={0}
          className={cn(
            "flex items-center justify-between rounded-md px-2 py-1.5 text-xs transition-colors cursor-pointer",
            isRootSelected
              ? "bg-accent font-semibold text-accent-foreground"
              : "hover:bg-muted/60 text-muted-foreground hover:text-foreground",
          )}
          onClick={() => onSelectFolder(null, false)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              onSelectFolder(null, false);
            }
          }}
        >
          <div className="flex items-center gap-2 min-w-0">
            <HardDrive className={cn("size-3.5 shrink-0", isRootSelected ? "text-primary" : "text-muted-foreground")} />
            <span className="truncate">Gốc kho tri thức</span>
          </div>
          <Badge variant="secondary" className="text-[10px] h-4 font-normal">
            {rootSourceCount}
          </Badge>
        </div>

        {/* Tree folders */}
        {tree.map((node) => renderNode(node, 0))}
      </div>

      {/* Footer shortcut: Tất cả tài liệu */}
      <div className="pt-2 mt-1 border-t border-border/50">
        <div
          role="button"
          tabIndex={0}
          className={cn(
            "flex items-center justify-between rounded-md px-2 py-1.5 text-xs transition-colors cursor-pointer",
            allFoldersActive
              ? "bg-accent font-semibold text-accent-foreground"
              : "hover:bg-muted/60 text-muted-foreground hover:text-foreground",
          )}
          onClick={() => onSelectFolder(null, true)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              onSelectFolder(null, true);
            }
          }}
        >
          <div className="flex items-center gap-2 min-w-0">
            <Layers className="size-3.5 shrink-0 text-muted-foreground" />
            <span className="truncate">Tất cả tài liệu</span>
          </div>
          <Badge variant="secondary" className="text-[10px] h-4 font-normal">
            {totalSourceCount}
          </Badge>
        </div>
      </div>
    </div>
  );
}

