import { AlertTriangle, Loader2 } from "lucide-react";
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
        <DialogHeader className="gap-1.5 text-left">
          <DialogTitle className="text-base font-semibold text-foreground">
            Xóa thư mục?
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground leading-relaxed">
            Bạn có chắc chắn muốn xóa thư mục{" "}
            <span className="font-semibold text-foreground break-words">
              "{folder.name}"
            </span>
            ? Hành động này không thể hoàn tác.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-xs text-destructive flex items-start gap-2">
            <AlertTriangle className="size-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <div className="p-3 rounded-lg bg-muted/40 border border-border/50 text-xs text-muted-foreground leading-relaxed">
          {isNotEmpty ? (
            <span className="text-destructive font-medium">
              Cảnh báo: Thư mục có {folder.source_count} tài liệu và{" "}
              {folder.subfolder_count} thư mục con. Hệ thống chỉ cho phép xóa
              thư mục rỗng.
            </span>
          ) : (
            "Thư mục hiện đang rỗng và có thể xóa an toàn khỏi kho tri thức."
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-2 pt-2">
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
            className="h-8 text-xs gap-1.5 shadow-2xs"
          >
            {deleteMutation.isPending && (
              <Loader2 className="size-3.5 animate-spin" />
            )}
            <span>
              {deleteMutation.isPending ? "Đang xóa..." : "Xóa thư mục"}
            </span>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
