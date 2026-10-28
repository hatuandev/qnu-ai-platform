import { FileText, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/admin/field";
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
import { useRenameSource } from "@/features/knowledge/queries";
import type { KBSource } from "@/features/knowledge/types";

export function SourceRenameDialog({
  open,
  onOpenChange,
  workspaceId,
  collectionId,
  source,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  collectionId: string;
  source: KBSource | null;
  onSuccess?: (source: KBSource) => void;
}) {
  const renameMutation = useRenameSource(workspaceId, collectionId);
  const [title, setTitle] = useState("");
  const [titleError, setTitleError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

  useEffect(() => {
    if (open && source) {
      setTitle(source.title);
      setTitleError(null);
      setServerError(null);
    }
  }, [open, source]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    event.stopPropagation();
    if (!source) return;

    const trimmed = title.trim();
    if (!trimmed) {
      setTitleError("Tiêu đề không được để trống.");
      return;
    }

    try {
      const updated = await renameMutation.mutateAsync({
        sourceId: source.id,
        title: trimmed,
      });
      toast.success("Đã đổi tiêu đề tài liệu.");
      onOpenChange(false);
      onSuccess?.(updated);
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setServerError(error.message);
      } else {
        setServerError("Không thể đổi tiêu đề. Vui lòng thử lại.");
      }
    }
  };

  const isSubmitting = renameMutation.isPending;

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="max-w-md p-0 gap-0">
        <ResponsiveDialogHeader className="border-b bg-muted/20 px-4 py-4 sm:px-6">
          <ResponsiveDialogTitle className="flex items-center gap-2.5 text-base font-semibold">
            <span className="flex size-8 items-center justify-center rounded-lg bg-muted text-primary">
              <FileText className="size-4" />
            </span>
            Đổi tiêu đề tài liệu
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs">
            Cập nhật tên hiển thị của tài liệu. ID tài liệu, các phiên bản và dữ liệu xử lý không thay đổi.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        <form onSubmit={handleSubmit}>
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
              <FieldLabel htmlFor="source-rename-title">
                Tiêu đề hiển thị <span className="text-destructive">*</span>
              </FieldLabel>
              <Input
                id="source-rename-title"
                className="text-xs h-9"
                value={title}
                autoFocus
                disabled={isSubmitting}
                maxLength={255}
                onChange={(e) => {
                  setTitle(e.target.value);
                  setTitleError(null);
                  setServerError(null);
                }}
              />
              {titleError ? (
                <FieldError>{titleError}</FieldError>
              ) : (
                <FieldDescription>
                  Tên tệp gốc: <span className="font-mono text-foreground">{source?.file_name}</span>
                </FieldDescription>
              )}
            </Field>
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
              disabled={isSubmitting || !title.trim()}
              className="gap-1.5"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Đang lưu...</span>
                </>
              ) : (
                <span>Lưu thay đổi</span>
              )}
            </Button>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

