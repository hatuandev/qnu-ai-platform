import { Folder, FolderTree, HardDrive, Loader2 } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  useFoldersQuery,
  useMoveFolder,
  useMoveSource,
} from "@/features/knowledge/queries";
import type { KBFolder } from "@/features/knowledge/types";
import { cn } from "@/lib/utils";

export function FolderMoveDialog({
  open,
  onOpenChange,
  workspaceId,
  collectionId,
  itemType,
  itemId,
  itemTitle,
  currentFolderId,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  collectionId: string;
  itemType: "folder" | "source";
  itemId: string;
  itemTitle: string;
  currentFolderId?: string | null;
  onSuccess?: () => void;
}) {
  const foldersQuery = useFoldersQuery(workspaceId, collectionId);
  const moveFolderMutation = useMoveFolder(workspaceId, collectionId, itemId);
  const moveSourceMutation = useMoveSource(workspaceId, collectionId);

  const [selectedTargetId, setSelectedTargetId] = useState<string | null>(
    currentFolderId ?? null,
  );
  const [serverError, setServerError] = useState<string | null>(null);

  const allFolders = foldersQuery.data ?? [];

  // If moving a folder, calculate illegal targets (self + all descendants)
  const illegalFolderIds = useMemo(() => {
    if (itemType !== "folder") return new Set<string>();
    const illegal = new Set<string>([itemId]);
    let added = true;
    while (added) {
      added = false;
      for (const f of allFolders) {
        if (f.parent_id && illegal.has(f.parent_id) && !illegal.has(f.id)) {
          illegal.add(f.id);
          added = true;
        }
      }
    }
    return illegal;
  }, [itemType, itemId, allFolders]);

  const handleMove = async () => {
    setServerError(null);
    try {
      if (itemType === "folder") {
        await moveFolderMutation.mutateAsync({
          target_parent_id: selectedTargetId,
        });
        toast.success(`Đã di chuyển thư mục "${itemTitle}".`);
      } else {
        await moveSourceMutation.mutateAsync({
          sourceId: itemId,
          targetFolderId: selectedTargetId,
        });
        toast.success(`Đã di chuyển tài liệu "${itemTitle}".`);
      }
      onOpenChange(false);
      onSuccess?.();
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setServerError(error.message);
      } else {
        setServerError("Không thể di chuyển. Vui lòng thử lại.");
      }
    }
  };

  const isSubmitting =
    moveFolderMutation.isPending || moveSourceMutation.isPending;

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="max-w-md p-0 gap-0">
        <ResponsiveDialogHeader className="border-b bg-muted/20 px-4 py-4 sm:px-6">
          <ResponsiveDialogTitle className="flex items-center gap-2.5 text-base font-semibold">
            <span className="flex size-8 items-center justify-center rounded-lg bg-muted text-primary">
              <FolderTree className="size-4" />
            </span>
            Di chuyển {itemType === "folder" ? "thư mục" : "tài liệu"}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs truncate" title={itemTitle}>
            Chọn thư mục đích cho: <span className="font-semibold text-foreground">{itemTitle}</span>
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        <div className="grid gap-3 px-4 py-4 sm:px-6">
          {serverError ? (
            <p
              role="alert"
              className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
            >
              {serverError}
            </p>
          ) : null}

          <div className="space-y-1.5 max-h-60 overflow-y-auto rounded-md border border-border p-2 bg-muted/10">
            {/* Root option */}
            <button
              type="button"
              className={cn(
                "flex w-full items-center justify-between rounded px-2.5 py-2 text-left text-xs transition-colors",
                selectedTargetId === null
                  ? "bg-primary text-primary-foreground font-medium"
                  : "hover:bg-muted/50 text-foreground",
              )}
              onClick={() => setSelectedTargetId(null)}
            >
              <div className="flex items-center gap-2">
                <HardDrive className="size-4 shrink-0" />
                <span>Gốc kho tri thức (Thư mục gốc)</span>
              </div>
              {selectedTargetId === null ? (
                <Badge variant="secondary" className="text-[10px] h-4">
                  Đang chọn
                </Badge>
              ) : null}
            </button>

            {/* Folder list */}
            {allFolders.map((f: KBFolder) => {
              const isIllegal = illegalFolderIds.has(f.id);
              const isSelected = selectedTargetId === f.id;
              return (
                <button
                  key={f.id}
                  type="button"
                  disabled={isIllegal}
                  className={cn(
                    "flex w-full items-center justify-between rounded px-2.5 py-2 text-left text-xs transition-colors",
                    isIllegal && "opacity-40 cursor-not-allowed",
                    isSelected
                      ? "bg-primary text-primary-foreground font-medium"
                      : "hover:bg-muted/50 text-foreground",
                  )}
                  onClick={() => {
                    if (!isIllegal) setSelectedTargetId(f.id);
                  }}
                >
                  <div className="flex items-center gap-2 truncate">
                    <Folder className="size-3.5 shrink-0 text-primary" />
                    <span className="truncate">{f.name}</span>
                  </div>
                  {isIllegal ? (
                    <span className="text-[10px] text-muted-foreground">
                      (Không hợp lệ)
                    </span>
                  ) : isSelected ? (
                    <Badge variant="secondary" className="text-[10px] h-4">
                      Đang chọn
                    </Badge>
                  ) : (
                    <span className="text-[10px] text-muted-foreground">
                      {f.source_count} tệp
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <ResponsiveDialogFooter className="border-t bg-card px-4 py-3 sm:px-6">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={isSubmitting}
            onClick={() => onOpenChange(false)}
          >
            Hủy
          </Button>
          <Button
            type="button"
            size="sm"
            disabled={isSubmitting || selectedTargetId === currentFolderId}
            className="gap-1.5"
            onClick={handleMove}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="size-3.5 animate-spin" />
                <span>Đang di chuyển...</span>
              </>
            ) : (
              <span>Di chuyển đến đây</span>
            )}
          </Button>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

