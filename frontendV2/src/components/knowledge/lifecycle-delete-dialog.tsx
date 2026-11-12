import { AlertTriangle, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  useCommitLifecycleActionMutation,
  useCreateLifecyclePreviewMutation,
} from "@/api/lifecycle/queries";
import type { LifecycleActionReceipt } from "@/api/lifecycle/types";
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

  const [preview, setPreview] = useState<LifecycleActionReceipt | null>(null);
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
    if (!preview || !canConfirmDelete) return;

    try {
      const idempotencyKey = `lifecycle:${preview.id}`;
      await commitActionMutation.mutateAsync({
        data: {
          preview_id: preview.id,
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
    }
  };

  const isDeleting = commitActionMutation.isPending;
  const canConfirmDelete =
    preview?.resource_id === sourceId &&
    preview?.kind === "source" &&
    preview.action === "delete" &&
    preview.status === "preview" &&
    !isLoadingPreview &&
    !isDeleting &&
    !error;

  return (
    <Dialog open={open} onOpenChange={isDeleting ? undefined : onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader className="gap-1.5 text-left">
          <DialogTitle className="text-base font-semibold text-foreground">
            Xóa tài liệu?
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground leading-relaxed">
            Bạn có chắc chắn muốn xóa vĩnh viễn tài liệu{" "}
            <span className="font-semibold text-foreground break-words">
              "{sourceTitle}"
            </span>
            ? Hành động này không thể hoàn tác.
          </DialogDescription>
        </DialogHeader>

        {isLoadingPreview ? (
          <div className="py-4 flex items-center justify-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="size-4 animate-spin text-primary" />
            <span>Đang kiểm tra tác động dữ liệu...</span>
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
          <div className="p-3 rounded-lg bg-muted/40 border border-border/50 text-xs text-muted-foreground leading-relaxed">
            Tệp gốc trong kho, các đoạn văn bản trích xuất và chỉ mục tìm kiếm
            liên quan sẽ được dọn dẹp an toàn khỏi hệ thống.
          </div>
        )}

        <DialogFooter className="gap-2 sm:gap-2 pt-2">
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
            disabled={!canConfirmDelete}
            className="h-8 text-xs gap-1.5 shadow-2xs"
          >
            {isDeleting && <Loader2 className="size-3.5 animate-spin" />}
            <span>{isDeleting ? "Đang xóa..." : "Xóa tài liệu"}</span>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
