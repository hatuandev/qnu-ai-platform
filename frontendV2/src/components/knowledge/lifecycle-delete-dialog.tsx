import { AlertTriangle, Loader2, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  useCommitLifecycleActionMutation,
  useCreateLifecyclePreviewMutation,
} from "@/api/lifecycle/queries";
import type { LifecyclePreviewResponse } from "@/api/lifecycle/types";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export function LifecycleDeleteDialog({
  open,
  onOpenChange,
  workspaceId,
  sourceId,
  sourceTitle,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  sourceId: string | null;
  sourceTitle: string;
  onSuccess?: () => void;
}) {
  const createPreviewMutation = useCreateLifecyclePreviewMutation(workspaceId);
  const commitActionMutation = useCommitLifecycleActionMutation(workspaceId);
  const mutatePreview = createPreviewMutation.mutateAsync;

  const [preview, setPreview] = useState<LifecyclePreviewResponse | null>(null);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;
    if (open && sourceId) {
      setIsLoadingPreview(true);
      setError(null);
      setPreview(null);

      mutatePreview({
        kind: "source",
        resource_id: sourceId,
        action: "delete",
        reason: `Xóa tài liệu ${sourceTitle} từ giao diện người dùng.`,
      })
        .then((res) => {
          if (!isCancelled) {
            setPreview(res);
            setIsLoadingPreview(false);
          }
        })
        .catch((err: unknown) => {
          if (!isCancelled) {
            const msg =
              err instanceof Error
                ? err.message
                : "Không thể tạo bản xem trước xóa";
            setError(msg);
            setIsLoadingPreview(false);
          }
        });
    }
    return () => {
      isCancelled = true;
    };
  }, [open, sourceId, sourceTitle, mutatePreview]);

  const handleConfirmDelete = async () => {
    if (!preview) return;

    try {
      const idempotencyKey = `del_${preview.preview_id}`;
      await commitActionMutation.mutateAsync({
        data: {
          preview_id: preview.preview_id,
          preview_sha256: preview.preview_sha256,
        },
        idempotencyKey,
      });

      toast.success(
        `Đã đưa tài liệu "${sourceTitle}" vào tiến trình xóa vĩnh viễn.`,
      );
      onOpenChange(false);
      onSuccess?.();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Có lỗi xảy ra khi xác nhận xóa";
      setError(msg);
      toast.error(msg);
    }
  };

  const isDeleting = commitActionMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={isDeleting ? undefined : onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base text-destructive">
            <Trash2 className="size-4" />
            <span>Xác nhận xóa tài liệu</span>
          </DialogTitle>
          <DialogDescription className="text-xs">
            Hành động này sẽ xóa vĩnh viễn tài liệu và toàn bộ bản bóc tách liên
            quan.
          </DialogDescription>
        </DialogHeader>

        {isLoadingPreview ? (
          <div className="py-6 flex flex-col items-center justify-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="size-5 animate-spin text-primary" />
            <span>Đang kiểm tra phụ thuộc và tác động xóa...</span>
          </div>
        ) : error ? (
          <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-xs text-destructive space-y-1">
            <div className="font-semibold flex items-center gap-1.5">
              <AlertTriangle className="size-4 shrink-0" />
              <span>Không thể xóa tài liệu</span>
            </div>
            <p>{error}</p>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="p-3 rounded-lg bg-muted/40 border border-border/70 text-xs space-y-2">
              <div className="text-foreground">
                Bạn có chắc chắn muốn xóa tài liệu:
              </div>
              <div className="font-semibold text-foreground px-2 py-1 bg-background rounded border border-border/60 truncate">
                {sourceTitle}
              </div>
              <div className="text-[11px] text-muted-foreground leading-relaxed">
                Tệp gốc trong kho lưu trữ, các đoạn văn bản trích xuất và chỉ
                mục liên quan sẽ được dọn dẹp an toàn trên hệ thống.
              </div>
            </div>
          </div>
        )}

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={isDeleting}
            className="h-8 text-xs"
          >
            Hủy
          </Button>
          <Button
            type="button"
            variant="destructive"
            size="sm"
            onClick={handleConfirmDelete}
            disabled={
              !preview || isLoadingPreview || isDeleting || Boolean(error)
            }
            className="h-8 text-xs gap-1.5 shadow-2xs"
          >
            {isDeleting ? (
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
