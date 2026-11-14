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

type PurgeKind = "source" | "collection";

const PURGE_COPY: Record<
  PurgeKind,
  {
    title: string;
    target: string;
    errorTitle: string;
    confirmLabel: string;
    reason: (title: string) => string;
    success: (title: string) => string;
    note: string;
  }
> = {
  source: {
    title: "Xóa tài liệu?",
    target: "tài liệu",
    errorTitle: "Không thể xóa tài liệu",
    confirmLabel: "Xóa tài liệu",
    reason: (title) => `Xóa tài liệu ${title} từ giao diện người dùng.`,
    success: (title) =>
      `Đã đưa tài liệu "${title}" vào tiến trình xóa vĩnh viễn.`,
    note: "Tệp gốc trong kho, các đoạn văn bản trích xuất và chỉ mục tìm kiếm liên quan sẽ được dọn dẹp an toàn khỏi hệ thống.",
  },
  collection: {
    title: "Xóa kho tri thức?",
    target: "kho tri thức",
    errorTitle: "Không thể xóa kho tri thức",
    confirmLabel: "Xóa kho",
    reason: (title) =>
      `Xóa kho ${title} cùng toàn bộ tài liệu bên trong từ giao diện người dùng.`,
    success: (title) =>
      `Đã đưa kho "${title}" cùng toàn bộ tài liệu bên trong vào tiến trình xóa vĩnh viễn.`,
    note: "Toàn bộ tài liệu, thư mục, bằng chứng OCR/biên soạn, phiên bản đã xử lý và chỉ mục tìm kiếm trong kho sẽ bị xóa vĩnh viễn khỏi hệ thống.",
  },
};

function readImpactCount(
  impact: Record<string, unknown> | undefined,
  key: string,
): number {
  const value = impact?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function describeCollectionImpact(
  impact: Record<string, unknown> | undefined,
): string {
  const parts: string[] = [];
  const sourceCount = readImpactCount(impact, "sources_to_delete");
  const folderCount = readImpactCount(impact, "folders_to_delete");
  const compiledCount = readImpactCount(impact, "compiled_versions_to_delete");
  if (sourceCount > 0) parts.push(`${sourceCount} tài liệu`);
  if (folderCount > 0) parts.push(`${folderCount} thư mục`);
  if (compiledCount > 0) parts.push(`${compiledCount} bản biên soạn`);
  if (parts.length === 0) return "Kho hiện không còn nội dung nào.";
  return `Sẽ xóa vĩnh viễn ${parts.join(", ")} cùng toàn bộ chỉ mục tìm kiếm.`;
}

export function LifecycleDeleteDialog({
  open,
  onOpenChange,
  workspaceId,
  kind,
  resourceId,
  resourceTitle,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  kind: PurgeKind;
  resourceId: string | null;
  resourceTitle: string;
  onSuccess?: () => void;
}) {
  const copy = PURGE_COPY[kind];
  const createPreviewMutation = useCreateLifecyclePreviewMutation(workspaceId);
  const commitActionMutation = useCommitLifecycleActionMutation(workspaceId);
  const mutatePreview = createPreviewMutation.mutateAsync;

  const [preview, setPreview] = useState<LifecycleActionReceipt | null>(null);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;
    if (open && resourceId) {
      setIsLoadingPreview(true);
      setError(null);
      setPreview(null);

      mutatePreview({
        kind,
        resource_id: resourceId,
        action: "delete",
        reason: copy.reason(resourceTitle),
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
  }, [open, kind, resourceId, resourceTitle, copy, mutatePreview]);

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

      toast.success(copy.success(resourceTitle));
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
    preview?.resource_id === resourceId &&
    preview?.kind === kind &&
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
            {copy.title}
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground leading-relaxed">
            Bạn có chắc chắn muốn xóa vĩnh viễn {copy.target}{" "}
            <span className="font-semibold text-foreground break-words">
              "{resourceTitle}"
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
              <span>{copy.errorTitle}</span>
            </div>
            <p>{error}</p>
          </div>
        ) : (
          <div className="p-3 rounded-lg bg-muted/40 border border-border/50 text-xs text-muted-foreground leading-relaxed space-y-1.5">
            {kind === "collection" && preview ? (
              <p className="font-medium text-foreground">
                {describeCollectionImpact(preview.impact)}
              </p>
            ) : null}
            <p>{copy.note}</p>
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
            <span>{isDeleting ? "Đang xóa..." : copy.confirmLabel}</span>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
