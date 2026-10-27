import {
  AlertCircle,
  AlertTriangle,
  Check,
  CheckCircle2,
  Clock,
  KeyRound,
  Loader2,
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
import { formatDateTimeValue } from "@/lib/date-utils";
import { useCommitDecisionMutation } from "./publication-queries";
import {
  formatDecisionAction,
  formatPublicationError,
  generatePublicationIdempotencyKey,
} from "./publication-schemas";
import type { DecisionPreviewResponse } from "./publication-types";

export function DecisionConfirmDialog({
  workspaceId,
  collectionId,
  documentId,
  versionId,
  preview,
  isOpen,
  onClose,
  onCommitSuccess,
}: {
  workspaceId: string;
  collectionId: string;
  documentId: string;
  versionId: string;
  preview: DecisionPreviewResponse | null;
  isOpen: boolean;
  onClose: () => void;
  onCommitSuccess?: () => void;
}) {
  const [idempotencyKey, setIdempotencyKey] = useState(() =>
    generatePublicationIdempotencyKey("dec"),
  );
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const commitMutation = useCommitDecisionMutation(
    workspaceId,
    collectionId,
    documentId,
    versionId,
  );

  useEffect(() => {
    if (isOpen) {
      setIdempotencyKey(generatePublicationIdempotencyKey("dec"));
      setErrorBanner(null);
    }
  }, [isOpen]);

  if (!preview) return null;

  const actionInfo = formatDecisionAction(preview.action);

  const handleConfirm = async () => {
    setErrorBanner(null);
    try {
      await commitMutation.mutateAsync({
        input: {
          preview_id: preview.id,
          preview_sha256: preview.preview_sha256,
        },
        idempotencyKey,
      });

      toast.success(
        `Đã thực hiện ${actionInfo.label.toLowerCase()} thành công`,
      );
      onCommitSuccess?.();
      onClose();
    } catch (err: unknown) {
      if (err instanceof ApiProblemError) {
        setErrorBanner(formatPublicationError(err.code, err.message));
      } else {
        setErrorBanner("Không thể thực hiện quyết định. Vui lòng thử lại.");
      }
    }
  };

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => !commitMutation.isPending && !open && onClose()}
    >
      <DialogContent className="sm:max-w-lg max-h-[min(820px,calc(100vh-2rem))] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div
              className={`size-8 rounded-lg flex items-center justify-center shrink-0 ${
                preview.action === "withdraw"
                  ? "bg-destructive/10 text-destructive"
                  : preview.action === "publish"
                    ? "bg-primary/10 text-primary"
                    : "bg-info/10 text-info"
              }`}
            >
              {preview.action === "withdraw" ? (
                <ShieldAlert className="size-4" />
              ) : preview.action === "publish" ? (
                <CheckCircle2 className="size-4" />
              ) : (
                <KeyRound className="size-4" />
              )}
            </div>
            <div>
              <DialogTitle className="text-base font-semibold">
                Xác nhận {actionInfo.label.toLowerCase()}
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground">
                Kiểm tra thông tin xem trước quyết định trước khi ghi nhận bất
                biến vào hệ thống.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 pt-2">
          {errorBanner && (
            <Alert variant="destructive" className="py-2.5">
              <AlertCircle className="size-4" />
              <AlertDescription className="text-xs">
                {errorBanner}
              </AlertDescription>
            </Alert>
          )}

          {/* Action details card */}
          <div className="rounded-lg border bg-card p-3.5 space-y-3 text-xs">
            <div className="flex items-center justify-between pb-2 border-b">
              <span className="text-muted-foreground">Thao tác:</span>
              <Badge
                variant={actionInfo.variant}
                className="font-semibold text-xs"
              >
                {actionInfo.label}
              </Badge>
            </div>

            <div className="space-y-1">
              <span className="text-muted-foreground font-medium">
                Lý do quyết định:
              </span>
              <p className="p-2.5 rounded-md bg-muted/40 text-foreground whitespace-pre-wrap text-xs">
                {preview.reason}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2 border-t text-[11px]">
              <div>
                <span className="text-muted-foreground">Document Seq:</span>{" "}
                <span className="font-mono font-medium">
                  #{preview.expected_document_sequence}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground">Version Seq:</span>{" "}
                <span className="font-mono font-medium">
                  #{preview.expected_version_sequence}
                </span>
              </div>
              <div className="col-span-2">
                <span className="text-muted-foreground">Preview ID:</span>{" "}
                <span className="font-mono text-muted-foreground/80">
                  {preview.id}
                </span>
              </div>
              <div className="col-span-2">
                <span className="text-muted-foreground">Preview Hash:</span>{" "}
                <span className="font-mono text-muted-foreground/80">
                  {preview.preview_sha256.slice(0, 16)}...
                </span>
              </div>
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

          {/* Explanatory notes */}
          {preview.action === "publish" && (
            <Alert className="bg-primary/5 border-primary/20 text-xs py-2.5">
              <Check className="size-3.5 text-primary" />
              <AlertDescription className="text-xs text-muted-foreground">
                Sau khi xuất bản, phiên bản này sẽ trở thành phiên bản hiện hành
                phục vụ tra cứu. Phiên bản đang xuất bản cũ (nếu có) sẽ tự động
                chuyển thành &quot;Đã thay thế&quot; (superseded).
              </AlertDescription>
            </Alert>
          )}

          {preview.action === "withdraw" && (
            <Alert
              variant="destructive"
              className="bg-destructive/5 text-xs py-2.5"
            >
              <AlertTriangle className="size-3.5" />
              <AlertDescription className="text-xs">
                Thu hồi sẽ dừng trạng thái xuất bản hoặc duyệt của phiên bản
                này. Lưu ý: Thu hồi không tự khôi phục phiên bản trước đó; nếu
                muốn xuất bản lại phiên bản khác, quản trị viên cần thực hiện
                duyệt và xuất bản phiên bản đó.
              </AlertDescription>
            </Alert>
          )}

          <div className="text-[11px] font-mono text-muted-foreground/70 flex justify-between border-t pt-2">
            <span>Idempotency-Key:</span>
            <span>{idempotencyKey.slice(0, 20)}...</span>
          </div>

          <DialogFooter className="gap-2 sm:gap-0 pt-2 border-t">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClose}
              disabled={commitMutation.isPending}
              className="text-xs"
            >
              Hủy
            </Button>
            <Button
              type="button"
              variant={
                preview.action === "withdraw" ? "destructive" : "default"
              }
              size="sm"
              onClick={handleConfirm}
              disabled={commitMutation.isPending}
              className="text-xs gap-1.5"
            >
              {commitMutation.isPending ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Đang xử lý...</span>
                </>
              ) : (
                <>
                  <Check className="size-3.5" />
                  <span>Xác nhận {actionInfo.verb}</span>
                </>
              )}
            </Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
}
