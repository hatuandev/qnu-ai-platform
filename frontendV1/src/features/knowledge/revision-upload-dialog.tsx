import { FilePlus2, Loader2 } from "lucide-react";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import { getTokenState, subscribeToken } from "@/app/api/v1/session-token";
import { Field, FieldError } from "@/components/admin/field";
import { FileUpload } from "@/components/admin/file-upload";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { ProcessingProgress } from "@/features/knowledge/processing-progress";
import { useAddRevision } from "@/features/knowledge/queries";
import {
  ACCEPT_UPLOAD,
  generateIdempotencyKey,
  MAX_UPLOAD_BYTES,
  validateUploadFile,
} from "@/features/knowledge/schemas";
import { useActionScope } from "@/features/lifecycle/action-scope";

type RevisionUploadProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  collectionId: string;
  sourceId: string;
  sourceTitle?: string;
};
export function RevisionUploadDialog(props: RevisionUploadProps) {
  const { sessionId } = useSyncExternalStore(
    subscribeToken,
    getTokenState,
    getTokenState,
  );
  return (
    <RevisionUploadSession
      key={JSON.stringify([
        sessionId,
        props.workspaceId,
        props.collectionId,
        props.sourceId,
      ])}
      {...props}
    />
  );
}
function RevisionUploadSession({
  open,
  onOpenChange,
  workspaceId,
  collectionId,
  sourceId,
  sourceTitle: _sourceTitle,
}: RevisionUploadProps) {
  const addRevisionMutation = useAddRevision(
    workspaceId,
    collectionId,
    sourceId,
  );
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [staged, setStaged] = useState(true);
  const current = useActionScope();

  // Maintain idempotency key across retries of the SAME operation
  const idempotencyKeyRef = useRef<string>(generateIdempotencyKey());

  useEffect(() => {
    if (open) {
      setFile(null);
      setFileError(null);
      setServerError(null);
      setStaged(true);
      idempotencyKeyRef.current = generateIdempotencyKey();
    }
  }, [open]);

  const handleFileChange = (files: File[]) => {
    const selected = files[0] ?? null;
    setFile(selected);
    setServerError(null);
    if (selected) {
      const err = validateUploadFile(selected);
      setFileError(err);
      idempotencyKeyRef.current = generateIdempotencyKey();
    } else {
      setFileError(null);
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setServerError(null);

    const validationErr = validateUploadFile(file);
    if (validationErr) {
      setFileError(validationErr);
      return;
    }
    if (!file) return;

    try {
      await addRevisionMutation.mutateAsync({
        file,
        idempotencyKey: idempotencyKeyRef.current,
        staged,
      });

      if (!current()) return;
      toast.success(
        staged
          ? "Đã tải bản chuẩn bị và bắt đầu tự động đọc nội dung; bản đang phục vụ được giữ nguyên."
          : "Đã tải phiên bản mới và bắt đầu tự động đọc nội dung.",
      );
      onOpenChange(false);
    } catch (error) {
      if (!current()) return;
      if (error instanceof ApiProblemError) {
        setServerError(error.message);
      } else {
        setServerError(
          "Không tải lên được phiên bản mới. Vui lòng kiểm tra lại kết nối.",
        );
      }
    }
  };

  const isSubmitting = addRevisionMutation.isPending;

  return (
    <ResponsiveDialog
      open={open}
      onOpenChange={(value) => {
        if (!isSubmitting) onOpenChange(value);
      }}
    >
      <ResponsiveDialogContent className="max-h-[min(820px,calc(100vh-2rem))] max-w-lg p-0 gap-0 flex flex-col">
        <ResponsiveDialogHeader className="border-b bg-muted/20 px-4 py-4 sm:px-6">
          <ResponsiveDialogTitle className="flex items-center gap-2.5 text-base font-semibold">
            <span className="flex size-8 items-center justify-center rounded-lg bg-muted">
              <FilePlus2 className="size-4" />
            </span>
            Tải tệp mới
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs">
            Tải lên tệp mới cho tài liệu này. Phiên bản cũ vẫn được lưu trong
            lịch sử để đối chiếu.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        <form
          id="revision-upload-form"
          className="min-h-0 flex-1 overflow-y-auto"
          onSubmit={handleSubmit}
        >
          <div className="grid gap-4 px-4 py-4 sm:px-6">
            {serverError ? (
              <p
                role="alert"
                className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
              >
                {serverError}
              </p>
            ) : null}

            <Field>
              <FileUpload
                accept={ACCEPT_UPLOAD}
                multiple={false}
                maxSize={MAX_UPLOAD_BYTES}
                disabled={isSubmitting}
                value={file ? [file] : []}
                onFilesChange={handleFileChange}
                compact
              />
              {fileError ? <FieldError>{fileError}</FieldError> : null}
            </Field>

            <div className="space-y-1.5 rounded-lg border bg-muted/15 p-3">
              <div className="flex items-start gap-2.5">
                <Checkbox
                  id="revision-staged"
                  checked={staged}
                  disabled={isSubmitting}
                  className="mt-0.5"
                  onCheckedChange={(checked) => {
                    setStaged(checked === true);
                    idempotencyKeyRef.current = generateIdempotencyKey();
                  }}
                />
                <div className="space-y-1">
                  <Label
                    htmlFor="revision-staged"
                    className="text-xs font-medium leading-none cursor-pointer select-none text-foreground"
                  >
                    Chế độ chuẩn bị (giữ bản hiện tại tiếp tục hoạt động)
                  </Label>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    {staged
                      ? "Bản mới sẽ được đưa vào chế độ nháp để đọc nội dung và đối chiếu. Bản cũ vẫn phục vụ bình thường cho đến khi bạn xuất bản."
                      : "Bản mới sẽ thay thế bản hiện tại ngay lập tức sau khi tải lên."}
                  </p>
                </div>
              </div>
            </div>

            {isSubmitting ? (
              <ProcessingProgress progress={{ status: "uploading" }} />
            ) : null}
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
              type="submit"
              size="sm"
              disabled={isSubmitting || !file || Boolean(fileError)}
              className="gap-1.5"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Đang tải lên...</span>
                </>
              ) : (
                <>
                  <FilePlus2 className="size-3.5" />
                  <span>Tải lên</span>
                </>
              )}
            </Button>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
