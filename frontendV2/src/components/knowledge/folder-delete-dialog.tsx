import { AlertTriangle, Loader2, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { useDeleteFolderMutation } from "@/api/knowledge/queries";
import type { FolderResponse } from "@/api/knowledge/types";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export function FolderDeleteDialog({
  open,
  onOpenChange,
  workspaceId,
  collectionId,
  folder,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  collectionId: string;
  folder: FolderResponse | null;
  onSuccess?: () => void;
}) {
  const deleteMutation = useDeleteFolderMutation(workspaceId, collectionId);
  const [error, setError] = useState<string | null>(null);

  if (!folder) return null;

  const isNotEmpty = folder.source_count > 0 || folder.subfolder_count > 0;

  const handleDelete = async () => {
    if (isNotEmpty) {
      setError(
        "Thư mục đang chứa tài liệu hoặc thư mục con. Vui lòng di chuyển hoặc xóa các nội dung bên trong trước.",
      );
      return;
    }

    try {
      await deleteMutation.mutateAsync(folder.id);
      toast.success(`Đã xóa thư mục "${folder.name}"`);
      onOpenChange(false);
      onSuccess?.();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Có lỗi xảy ra khi xóa thư mục";
      setError(msg);
      toast.error(msg);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={deleteMutation.isPending ? undefined : onOpenChange}
    >
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base text-destructive">
            <Trash2 className="size-4" />
            <span>Xác nhận xóa thư mục</span>
          </DialogTitle>
          <DialogDescription className="text-xs">
            Hành động này sẽ xóa thư mục <strong>{folder.name}</strong> khỏi kho
            tri thức.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-xs text-destructive flex items-start gap-2">
            <AlertTriangle className="size-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <div className="p-3 rounded-lg bg-muted/40 border border-border/70 text-xs space-y-2">
          <div>
            Thư mục: <strong>{folder.name}</strong>
          </div>
          <div className="text-[11px] text-muted-foreground">
            {isNotEmpty ? (
              <span className="text-destructive font-medium">
                Cảnh báo: Thư mục có {folder.source_count} tài liệu và{" "}
                {folder.subfolder_count} thư mục con. Máy chủ chỉ cho phép xóa
                thư mục rỗng.
              </span>
            ) : (
              "Thư mục hiện đang rỗng và có thể xóa an toàn."
            )}
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={deleteMutation.isPending}
            className="h-8 text-xs"
          >
            Hủy
          </Button>
          <Button
            type="button"
            variant="destructive"
            size="sm"
            onClick={handleDelete}
            disabled={deleteMutation.isPending || isNotEmpty}
            className="h-8 text-xs gap-1.5"
          >
            {deleteMutation.isPending ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Trash2 className="size-3.5" />
            )}
            <span>Xác nhận xóa</span>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
