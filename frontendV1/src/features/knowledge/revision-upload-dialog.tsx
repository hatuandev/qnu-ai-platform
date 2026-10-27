import { FilePlus2, Loader2 } from "lucide-react";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import { getTokenState, subscribeToken } from "@/app/api/v1/session-token";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/admin/field";
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
  sourceTitle,
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
          ? "Đã tải bản chuẩn bị; bản đang phục vụ được giữ nguyên."
          : "Đã tải phiên bản mới; cần xử lý và xuất bản lại.",
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
            Tải lên phiên bản mới
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs">
            Thêm một phiên bản tài liệu mới cho nguồn &ldquo;
            {sourceTitle || sourceId}&rdquo;. Phiên bản cũ được lưu giữ bất biến
            trong lịch sử.
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
              <FieldLabel htmlFor="revision-file">
                Tệp phiên bản mới <span className="text-destructive">*</span>
              </FieldLabel>
              <FileUpload
                accept={ACCEPT_UPLOAD}
                multiple={false}
                maxSize={MAX_UPLOAD_BYTES}
                disabled={isSubmitting}
                value={file ? [file] : []}
                onFilesChange={handleFileChange}
              />
              {fileError ? (
                <FieldError>{fileError}</FieldError>
              ) : (
                <FieldDescription>
                  Chỉ chọn 1 tệp PDF hoặc DOCX (tối đa 60 MB). Tiêu đề nguồn sẽ
                  được giữ nguyên.
                </FieldDescription>
              )}
            </Field>

            <div className="space-y-2 rounded-lg border p-3">
              <div className="flex items-start gap-2">
                <Checkbox
                  id="revision-staged"
                  checked={staged}
                  disabled={isSubmitting}
                  onCheckedChange={(checked) => {
                    setStaged(checked === true);
                    idempotencyKeyRef.current = generateIdempotencyKey();
                  }}
                />
                <Label
                  htmlFor="revision-staged"
                  className="text-sm leading-relaxed"
                >
                  Chuẩn bị bản thay thế, giữ bản đang phục vụ
                </Label>
              </div>
              <p className="text-xs text-muted-foreground">
                {staged
                  ? "Sau upload: OCR → sửa văn bản → Compiler → duyệt phiên bản → Thay bản phục vụ. Chỉ chuyển khi chỉ mục mới sẵn sàng."
                  : "Bản mới trở thành revision hiện hành ngay; nội dung cũ có thể hết phù hợp cho RAG trước khi bạn xuất bản lại."}
              </p>
            </div>

            {isSubmitting ? (
              <div className="rounded-md border border-info/30 bg-info/5 p-3 text-xs text-info flex items-center gap-2">
                <Loader2 className="size-4 animate-spin shrink-0" />
                <span>
                  Đang tải lên phiên bản mới ({file?.name}). Vui lòng không đóng
                  trình duyệt...
                </span>
              </div>
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
                  <span>Tải lên phiên bản</span>
                </>
              )}
            </Button>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
