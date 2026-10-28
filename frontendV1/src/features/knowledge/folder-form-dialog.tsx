import { Folder, FolderPlus, Loader2 } from "lucide-react";
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
import {
  useCreateFolder,
  useUpdateFolder,
} from "@/features/knowledge/queries";
import type { KBFolder } from "@/features/knowledge/types";

export function FolderFormDialog({
  open,
  onOpenChange,
  workspaceId,
  collectionId,
  parentFolderId,
  parentFolderName,
  folderToEdit,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  collectionId: string;
  parentFolderId?: string | null;
  parentFolderName?: string;
  folderToEdit?: KBFolder | null;
  onSuccess?: (folder: KBFolder) => void;
}) {
  const isEditing = Boolean(folderToEdit);
  const createMutation = useCreateFolder(workspaceId, collectionId);
  const updateMutation = useUpdateFolder(
    workspaceId,
    collectionId,
    folderToEdit?.id ?? "",
  );

  const [name, setName] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setName(folderToEdit ? folderToEdit.name : "");
      setNameError(null);
      setServerError(null);
    }
  }, [open, folderToEdit]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setServerError(null);

    const trimmed = name.trim();
    if (!trimmed) {
      setNameError("Vui lòng nhập tên thư mục.");
      return;
    }
    if (/[/\\:\*\?\"<>\|]/.test(trimmed)) {
      setNameError("Tên thư mục không được chứa ký tự đặc biệt (/, \\, :, *, ?, \", <, >, |).");
      return;
    }

    try {
      if (isEditing && folderToEdit) {
        const updated = await updateMutation.mutateAsync({ name: trimmed });
        toast.success(`Đã đổi tên thư mục thành "${updated.name}".`);
        onOpenChange(false);
        onSuccess?.(updated);
      } else {
        const created = await createMutation.mutateAsync({
          name: trimmed,
          parent_id: parentFolderId ?? null,
        });
        toast.success(`Đã tạo thư mục "${created.name}".`);
        onOpenChange(false);
        onSuccess?.(created);
      }
    } catch (error) {
      if (error instanceof ApiProblemError) {
        setServerError(error.message);
      } else {
        setServerError("Không thể lưu thư mục. Vui lòng thử lại.");
      }
    }
  };

  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="max-w-md p-0 gap-0">
        <ResponsiveDialogHeader className="border-b bg-muted/20 px-4 py-4 sm:px-6">
          <ResponsiveDialogTitle className="flex items-center gap-2.5 text-base font-semibold">
            <span className="flex size-8 items-center justify-center rounded-lg bg-muted text-primary">
              {isEditing ? (
                <Folder className="size-4" />
              ) : (
                <FolderPlus className="size-4" />
              )}
            </span>
            {isEditing ? "Đổi tên thư mục" : "Tạo thư mục mới"}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs">
            {isEditing
              ? "Cập nhật tên hiển thị của thư mục trong kho tri thức."
              : parentFolderName
                ? `Thư mục mới sẽ được đặt bên trong "${parentFolderName}".`
                : "Thư mục mới sẽ được đặt ở gốc kho tri thức."}
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
              <FieldLabel htmlFor="folder-name">
                Tên thư mục <span className="text-destructive">*</span>
              </FieldLabel>
              <Input
                id="folder-name"
                className="text-xs h-9"
                placeholder="Ví dụ: Quy chế đào tạo 2026"
                value={name}
                autoFocus
                disabled={isSubmitting}
                maxLength={255}
                onChange={(e) => {
                  setName(e.target.value);
                  setNameError(null);
                  setServerError(null);
                }}
              />
              {nameError ? (
                <FieldError>{nameError}</FieldError>
              ) : (
                <FieldDescription>
                  Tên thư mục từ 1 đến 255 ký tự, không chứa ký tự đường dẫn.
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
              disabled={isSubmitting || !name.trim()}
              className="gap-1.5"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Đang lưu...</span>
                </>
              ) : (
                <span>{isEditing ? "Lưu thay đổi" : "Tạo thư mục"}</span>
              )}
            </Button>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

