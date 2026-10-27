import { FileUp, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
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
import { Input } from "@/components/ui/input";
import { useUploadSource } from "@/features/knowledge/queries";
import {
  ACCEPT_UPLOAD,
  generateIdempotencyKey,
  MAX_UPLOAD_BYTES,
  validateUploadFile,
} from "@/features/knowledge/schemas";

export function SourceUploadDialog({
  open,
  onOpenChange,
  workspaceId,
  collectionId,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  collectionId: string;
  onSuccess?: (sourceId: string) => void;
}) {
  const uploadMutation = useUploadSource(workspaceId, collectionId);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [fileError, setFileError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

  // Maintain idempotency key across retries of the SAME operation
  const idempotencyKeyRef = useRef<string>(generateIdempotencyKey());

  useEffect(() => {
    if (open) {
      setFile(null);
      setTitle("");
      setFileError(null);
      setServerError(null);
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
      // Auto fill title if currently empty
      if (!title) {
        setTitle(selected.name.replace(/\.[^/.]+$/, ""));
      }
      // Operation changed -> new idempotency key
      idempotencyKeyRef.current = generateIdempotencyKey();
    } else {
      setFileError(null);
    }
  };

  const handleTitleChange = (nextTitle: string) => {
    setTitle(nextTitle);
    setServerError(null);
    // Operation changed -> new idempotency key
    idempotencyKeyRef.current = generateIdempotencyKey();
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
      const result = await uploadMutation.mutateAsync({
        file,
        title: title.trim() || undefined,
        idempotencyKey: idempotencyKeyRef.current,
      });

      toast.success("Đã tải lên và lưu tệp thành công.");
      onOpenChange(false);
      onSuccess?.(result.source.id);
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setServerError(error.message);
      } else {
        setServerError(
          "Không tải lên được tệp. Vui lòng kiểm tra lại kết nối.",
        );
      }
    }
  };

  const isSubmitting = uploadMutation.isPending;

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="max-h-[min(820px,calc(100vh-2rem))] max-w-lg p-0 gap-0 flex flex-col">
        <ResponsiveDialogHeader className="border-b bg-muted/20 px-4 py-4 sm:px-6">
          <ResponsiveDialogTitle className="flex items-center gap-2.5 text-base font-semibold">
            <span className="flex size-8 items-center justify-center rounded-lg bg-muted">
              <FileUp className="size-4" />
            </span>
            Tải lên tài liệu mới
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs">
            Thêm tài liệu vào bộ sưu tập. Hỗ trợ tệp định dạng PDF (.pdf) hoặc
            Word (.docx), dung lượng tối đa 60 MB.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        <form
          id="source-upload-form"
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
              <FieldLabel htmlFor="source-file">
                Tệp tài liệu <span className="text-destructive">*</span>
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
                  Chỉ chọn 1 tệp mỗi lần. Tệp được lưu nguyên vẹn bytes vào kho
                  lưu trữ an toàn.
                </FieldDescription>
              )}
            </Field>

            <Field>
              <FieldLabel htmlFor="source-title">Tiêu đề hiển thị</FieldLabel>
              <Input
                id="source-title"
                className="text-xs"
                placeholder="Ví dụ: Hướng dẫn tuyển sinh và học phí năm 2026"
                value={title}
                disabled={isSubmitting}
                maxLength={255}
                onChange={(event) => handleTitleChange(event.target.value)}
              />
              <FieldDescription>
                Tùy chọn. Nếu để trống, hệ thống sẽ sử dụng tên tệp làm tiêu đề.
              </FieldDescription>
            </Field>

            {isSubmitting ? (
              <div className="rounded-md border border-info/30 bg-info/5 p-3 text-xs text-info flex items-center gap-2">
                <Loader2 className="size-4 animate-spin shrink-0" />
                <span>
                  Đang tải lên tệp ({file?.name}). Vui lòng không đóng trình
                  duyệt...
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
                  <FileUp className="size-3.5" />
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
