import { Loader2, RotateCcw } from "lucide-react";
import { useRef } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import { ErrorState } from "@/components/admin/error-state";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Button } from "@/components/ui/button";
import { useActionScope } from "@/features/lifecycle/action-scope";
import { useRequestProcessingRunMutation } from "./ocr-queries";
import { useRevisionsQuery } from "./queries";
import type { KBSource } from "./types";

export function SourceReextractDialog({
  workspaceId,
  collectionId,
  source,
  onClose,
  onStarted,
}: {
  workspaceId: string;
  collectionId: string;
  source: KBSource;
  onClose: () => void;
  onStarted: (revisionId: string, runId: string) => void;
}) {
  const current = useActionScope();
  const submitted = useRef(false);
  const revisions = useRevisionsQuery(workspaceId, collectionId, source.id);
  const revision = revisions.data?.find(
    (item) => item.revision_no === source.current_revision_no,
  );
  const request = useRequestProcessingRunMutation(
    workspaceId,
    collectionId,
    source.id,
    revision?.id ?? "",
  );
  const handleStart = async () => {
    if (!current() || !revision || submitted.current) return;
    submitted.current = true;
    try {
      const result = await request.mutateAsync({
        strategy: "auto",
        force: true,
      });
      if (!current()) return;
      toast.success("Đã gửi yêu cầu bóc tách lại.");
      onStarted(revision.id, result.run.id);
    } catch (error) {
      if (!current()) return;
      toast.error(
        error instanceof ApiProblemError
          ? error.message
          : "Không thể yêu cầu bóc tách lại. Hãy kiểm tra trạng thái tài liệu.",
      );
    } finally {
      submitted.current = false;
    }
  };
  return (
    <ResponsiveDialog
      open
      onOpenChange={(open) => !open && !request.isPending && onClose()}
    >
      <ResponsiveDialogContent className="max-w-md p-0 gap-0">
        <ResponsiveDialogHeader className="border-b bg-muted/20 px-6 py-4">
          <ResponsiveDialogTitle className="flex items-center gap-2">
            <RotateCcw className="size-4 text-primary" />
            Bóc tách lại
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            Tạo lượt bóc tách mới cho “{source.title}”. Kết quả cũ được giữ lại.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>
        <div className="px-6 py-4 text-sm">
          {revisions.isError ? (
            <ErrorState error={revisions.error} />
          ) : revisions.isPending ? (
            <p role="status">Đang tải phiên bản tài liệu…</p>
          ) : revision ? (
            <p>Phiên bản tệp v{revision.revision_no}</p>
          ) : (
            <p role="alert">
              Không tìm thấy phiên bản hiện tại. Hãy tải lại danh sách.
            </p>
          )}
        </div>
        <ResponsiveDialogFooter className="border-t bg-card px-6 py-4">
          <Button
            variant="outline"
            disabled={request.isPending}
            onClick={onClose}
          >
            Hủy
          </Button>
          <Button
            disabled={!revision || revisions.isError || request.isPending}
            onClick={() => void handleStart()}
          >
            {request.isPending && <Loader2 className="size-4 animate-spin" />}
            {request.isPending ? "Đang gửi…" : "Bắt đầu bóc tách lại"}
          </Button>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
