import { AlertTriangle, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/api/client";
import {
  useCommitLifecycleActionMutation,
  useCreateLifecyclePreviewMutation,
} from "@/api/lifecycle/queries";
import type { LifecycleActionReceipt } from "@/api/lifecycle/types";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

type PurgeKind = "source" | "collection";

const HISTORY_CONFLICT_CODES = new Set([
  "collection_in_use_by_conversations",
  "collection_in_use_by_answer_reviews",
]);

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

function describeHistoryImpact(
  impact: Record<string, unknown> | undefined,
): string {
  const parts: string[] = [];
  const conversationCount = readImpactCount(impact, "conversations_to_delete");
  const reviewCount = readImpactCount(impact, "answer_reviews_to_delete");
  if (conversationCount > 0) parts.push(`${conversationCount} hội thoại`);
  if (reviewCount > 0) parts.push(`${reviewCount} bài kiểm thử câu trả lời`);
  if (parts.length === 0) return "Kho không còn hội thoại hay bài kiểm thử cũ.";
  return `Kèm theo ${parts.join(" và ")} cũng sẽ bị xóa vĩnh viễn.`;
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
  const [includeHistory, setIncludeHistory] = useState(false);
  const [historyRequired, setHistoryRequired] = useState(false);

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
        reason: includeHistory
          ? `${copy.reason(resourceTitle)} Bao gồm lịch sử hội thoại và bài kiểm thử cũ.`
          : copy.reason(resourceTitle),
        ...(includeHistory ? { include_history: true } : {}),
      })
        .then((res) => {
          if (!isCancelled) {
            setPreview(res);
            setHistoryRequired(false);
            setIsLoadingPreview(false);
          }
        })
        .catch((err: unknown) => {
          if (isCancelled) return;
          const blockedByHistory =
            kind === "collection" &&
            err instanceof ApiProblemError &&
            HISTORY_CONFLICT_CODES.has(err.code);
          setHistoryRequired(blockedByHistory);
          setError(
            blockedByHistory
              ? null
              : err instanceof Error
                ? err.message
                : "Không thể tạo bản xem trước xóa",
          );
          setIsLoadingPreview(false);
        });
    }
    return () => {
      isCancelled = true;
    };
  }, [
    open,
    kind,
    resourceId,
    resourceTitle,
    includeHistory,
    copy,
    mutatePreview,
  ]);

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      setIncludeHistory(false);
      setHistoryRequired(false);
      setPreview(null);
      setError(null);
    }
    onOpenChange(next);
  };

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
      handleOpenChange(false);
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
    <Dialog
      open={open}
      onOpenChange={isDeleting ? undefined : handleOpenChange}
    >
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
        ) : historyRequired ? (
          <div className="p-3 rounded-lg bg-warning/10 border border-warning/30 text-xs space-y-2">
            <div className="font-semibold text-foreground flex items-center gap-1.5">
              <AlertTriangle className="size-4 shrink-0 text-warning" />
              <span>Kho còn lịch sử hội thoại cũ</span>
            </div>
            <p className="text-muted-foreground leading-relaxed">
              Hội thoại và bài kiểm thử câu trả lời cũ vẫn trỏ vào kho này. Để
              xóa kho, bạn cần xóa kèm các lịch sử đó. Trợ lý được giữ nguyên.
            </p>
            <label
              htmlFor="delete-collection-include-history"
              className="flex cursor-pointer select-none items-start gap-2 pt-0.5"
            >
              <Checkbox
                id="delete-collection-include-history"
                checked={includeHistory}
                disabled={isLoadingPreview}
                onCheckedChange={(value) => setIncludeHistory(value === true)}
                className="mt-0.5"
              />
              <span className="font-medium text-foreground leading-snug">
                Xóa cả lịch sử hội thoại cũ
              </span>
            </label>
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
            {kind === "collection" && preview?.impact?.history_included ? (
              <p className="font-medium text-foreground">
                {describeHistoryImpact(preview.impact)}
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
            onClick={() => handleOpenChange(false)}
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
