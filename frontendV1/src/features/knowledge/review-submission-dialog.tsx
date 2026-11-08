import {
  AlertCircle,
  Check,
  Clock,
  Eye,
  Loader2,
  RotateCcw,
  Send,
  ShieldAlert,
} from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { formatDateTimeValue } from "@/lib/date-utils";
import { createIdempotencyKey } from "@/lib/idempotency-key";
import {
  useCommitSubmissionMutation,
  useSubmissionPreviewMutation,
} from "./review-queries";
import {
  formatReviewSubmissionError,
  submissionActionLabel,
} from "./review-schemas";
import type {
  SubmissionPreviewAction,
  SubmissionPreviewResponse,
  SubmissionResponse,
} from "./review-types";

const MIN_REASON_LENGTH: Partial<Record<SubmissionPreviewAction, number>> = {
  request_changes: 10,
  cancel: 3,
};

export function ReviewSubmissionDialog({
  workspaceId,
  collectionId,
  documentId,
  versionId,
  versionNo,
  action,
  submission,
  isOpen,
  onClose,
  onSuccess,
}: {
  workspaceId: string;
  collectionId: string;
  documentId: string;
  versionId: string;
  versionNo: number;
  action: SubmissionPreviewAction | null;
  submission?: SubmissionResponse | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}) {
  const [reason, setReason] = useState("");
  const [preview, setPreview] = useState<SubmissionPreviewResponse | null>(
    null,
  );
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState(createIdempotencyKey);

  const previewMutation = useSubmissionPreviewMutation(
    workspaceId,
    collectionId,
  );
  const commitMutation = useCommitSubmissionMutation(workspaceId, collectionId);

  useEffect(() => {
    if (!isOpen) return;
    setReason("");
    setPreview(null);
    setErrorBanner(null);
    setIdempotencyKey(createIdempotencyKey());
  }, [isOpen]);

  if (!action) return null;

  const labels = submissionActionLabel(action);
  const minLength = MIN_REASON_LENGTH[action] ?? 0;
  const trimmedReason = reason.trim();
  const isReasonValid = trimmedReason.length >= minLength;
  const needsSubmission = action !== "submit";
  const missingSubmission = needsSubmission && !submission;

  const handlePreview = async () => {
    if (!isReasonValid || missingSubmission) return;
    setErrorBanner(null);
    try {
      const result = await previewMutation.mutateAsync({
        input: {
          document_id: documentId,
          version_id: versionId,
          action,
          reason: trimmedReason,
          ...(needsSubmission && submission
            ? { submission_id: submission.id }
            : {}),
        },
      });
      setPreview(result);
    } catch (err: unknown) {
      setErrorBanner(
        err instanceof ApiProblemError
          ? formatReviewSubmissionError(err.code, err.message)
          : "Không thể tạo bản xem trước. Vui lòng thử lại.",
      );
    }
  };

  const handleCommit = async () => {
    if (!preview) return;
    setErrorBanner(null);
    try {
      await commitMutation.mutateAsync({
        input: {
          preview_id: preview.id,
          preview_sha256: preview.preview_sha256,
        },
        idempotencyKey,
      });
      toast.success(`Đã ${labels.confirm.toLowerCase()} thành công.`);
      onSuccess?.();
      onClose();
    } catch (err: unknown) {
      setErrorBanner(
        err instanceof ApiProblemError
          ? formatReviewSubmissionError(err.code, err.message)
          : "Không thể xác nhận thao tác. Vui lòng thử lại.",
      );
    }
  };

  const isBusy = previewMutation.isPending || commitMutation.isPending;

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => !isBusy && !open && onClose()}
    >
      <DialogContent className="sm:max-w-lg max-h-[min(820px,calc(100vh-2rem))] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="size-8 rounded-lg flex items-center justify-center shrink-0 bg-primary/10 text-primary">
              {action === "submit" ? (
                <Send className="size-4" />
              ) : action === "request_changes" ? (
                <RotateCcw className="size-4" />
              ) : (
                <ShieldAlert className="size-4" />
              )}
            </div>
            <div>
              <DialogTitle className="text-base font-semibold">
                {labels.title} v{versionNo}
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground">
                {action === "submit"
                  ? "Gửi phiên bản bất biến này cho người duyệt. Nội dung phiên bản không bị thay đổi."
                  : action === "request_changes"
                    ? "Nêu rõ nội dung cần sửa. Phiên bản hiện tại được giữ nguyên; người biên tập cần chuẩn bị phiên bản mới."
                    : "Rút yêu cầu duyệt chưa được xử lý. Lịch sử vẫn được giữ lại."}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 pt-2">
          {errorBanner ? (
            <Alert variant="destructive" className="py-2.5">
              <AlertCircle className="size-4" />
              <AlertDescription className="text-xs">
                {errorBanner}
              </AlertDescription>
            </Alert>
          ) : null}

          {missingSubmission ? (
            <Alert variant="destructive" className="py-2.5">
              <AlertCircle className="size-4" />
              <AlertDescription className="text-xs">
                Không tìm thấy yêu cầu duyệt đang mở cho phiên bản này.
              </AlertDescription>
            </Alert>
          ) : null}

          {preview ? (
            <div className="rounded-lg border bg-card p-3.5 space-y-3 text-xs">
              <div className="flex items-center justify-between pb-2 border-b">
                <span className="text-muted-foreground">Thao tác:</span>
                <Badge variant="info" className="font-semibold text-xs">
                  {labels.confirm}
                </Badge>
              </div>
              <div className="space-y-1">
                <span className="text-muted-foreground font-medium">
                  {action === "submit" ? "Ghi chú gửi duyệt:" : "Lý do:"}
                </span>
                <p className="p-2.5 rounded-md bg-muted/40 text-foreground whitespace-pre-wrap text-xs">
                  {preview.reason.trim() || "Không có ghi chú."}
                </p>
              </div>
              <div className="flex items-center gap-1.5 pt-2 border-t text-[11px] text-muted-foreground">
                <Clock className="size-3 text-warning shrink-0" />
                <span>
                  Hết hạn bản xem trước:{" "}
                  <span className="font-medium text-foreground">
                    {formatDateTimeValue(preview.expires_at)}
                  </span>
                </span>
              </div>
            </div>
          ) : (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <Label
                  htmlFor="review-reason"
                  className="font-semibold text-foreground"
                >
                  {action === "submit" ? "Ghi chú cho người duyệt" : "Lý do"}
                  {minLength > 0 ? (
                    <span className="text-destructive"> *</span>
                  ) : null}
                </Label>
                <span className="text-[11px] text-muted-foreground">
                  {trimmedReason.length}/1000
                </span>
              </div>
              <Textarea
                id="review-reason"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder={
                  action === "submit"
                    ? "Ví dụ: Bản đã chuẩn bị từ nguồn mới nhất, nhờ duyệt giúp."
                    : action === "request_changes"
                      ? "Nêu rõ điểm cần sửa để biên tập chuẩn bị phiên bản mới."
                      : "Nêu lý do rút yêu cầu duyệt."
                }
                rows={3}
                maxLength={1000}
                className="text-xs resize-none"
                disabled={isBusy}
              />
              {minLength > 0 ? (
                <p className="text-[11px] text-muted-foreground">
                  Tối thiểu {minLength} ký tự.
                </p>
              ) : null}
            </div>
          )}

          <DialogFooter className="gap-2 sm:gap-0 pt-2 border-t">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="text-xs"
              disabled={isBusy}
              onClick={() => {
                if (preview) {
                  setPreview(null);
                  return;
                }
                onClose();
              }}
            >
              {preview ? "Quay lại" : "Hủy"}
            </Button>
            {preview ? (
              <Button
                type="button"
                variant={action === "cancel" ? "destructive" : "default"}
                size="sm"
                className="text-xs gap-1.5"
                disabled={isBusy}
                onClick={handleCommit}
              >
                {commitMutation.isPending ? (
                  <>
                    <Loader2 className="size-3.5 animate-spin" />
                    <span>Đang xử lý...</span>
                  </>
                ) : (
                  <>
                    <Check className="size-3.5" />
                    <span>Xác nhận {labels.confirm.toLowerCase()}</span>
                  </>
                )}
              </Button>
            ) : (
              <Button
                type="button"
                size="sm"
                className="text-xs gap-1.5"
                disabled={!isReasonValid || missingSubmission || isBusy}
                onClick={handlePreview}
              >
                {previewMutation.isPending ? (
                  <>
                    <Loader2 className="size-3.5 animate-spin" />
                    <span>Đang tạo bản xem trước...</span>
                  </>
                ) : (
                  <>
                    <Eye className="size-3.5" />
                    <span>Xem trước</span>
                  </>
                )}
              </Button>
            )}
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
}
