import { useForm } from "@tanstack/react-form";
import { FolderPlus, Loader2, Save } from "lucide-react";
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
import { Textarea } from "@/components/ui/textarea";
import {
  useCreateCollection,
  useUpdateCollection,
} from "@/features/knowledge/queries";
import {
  collectionCreateSchema,
  collectionUpdateSchema,
} from "@/features/knowledge/schemas";
import type { KBCollection } from "@/features/knowledge/types";
import { getFormErrorMessage } from "@/lib/form-errors";

function fieldError(errors: unknown[]) {
  return getFormErrorMessage(errors[0]);
}

export function CollectionFormDialog({
  open,
  onOpenChange,
  workspaceId,
  collection,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  collection?: KBCollection | null;
}) {
  const isEdit = Boolean(collection);
  const createMutation = useCreateCollection(workspaceId);
  const updateMutation = useUpdateCollection(workspaceId, collection?.id ?? "");
  const [serverError, setServerError] = useState<string | null>(null);

  const form = useForm({
    defaultValues: {
      name: collection?.name ?? "",
      description: collection?.description ?? "",
    },
    validators: {
      onSubmit: isEdit ? collectionUpdateSchema : collectionCreateSchema,
    },
    onSubmit: async ({ value }) => {
      setServerError(null);
      try {
        if (isEdit && collection) {
          const patch: { name?: string; description?: string | null } = {};
          const nextName = value.name.trim();
          if (nextName !== collection.name) {
            patch.name = nextName;
          }

          const currentDesc = collection.description ?? "";
          const nextDesc = (value.description ?? "").trim();
          if (nextDesc !== currentDesc) {
            patch.description = nextDesc === "" ? null : nextDesc;
          }

          if (Object.keys(patch).length === 0) {
            toast.info("Không có thay đổi nào để lưu.");
            onOpenChange(false);
            return;
          }

          await updateMutation.mutateAsync(patch);
          toast.success("Đã cập nhật bộ sưu tập.");
        } else {
          await createMutation.mutateAsync({
            name: value.name.trim(),
            description: value.description?.trim() || null,
          });
          toast.success("Đã tạo bộ sưu tập mới.");
        }
        onOpenChange(false);
      } catch (error) {
        if (error instanceof ApiProblemError) {
          setServerError(error.message);
        } else {
          setServerError("Đã xảy ra lỗi khi lưu bộ sưu tập. Vui lòng thử lại.");
        }
      }
    },
  });

  useEffect(() => {
    if (open) {
      setServerError(null);
      form.reset({
        name: collection?.name ?? "",
        description: collection?.description ?? "",
      });
    }
  }, [open, collection, form.reset]);

  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="max-h-[min(820px,calc(100vh-2rem))] max-w-lg p-0 gap-0 flex flex-col">
        <ResponsiveDialogHeader className="border-b bg-muted/20 px-4 py-4 sm:px-6">
          <ResponsiveDialogTitle className="flex items-center gap-2.5 text-base font-semibold">
            <span className="flex size-8 items-center justify-center rounded-lg bg-muted">
              {isEdit ? (
                <Save className="size-4" />
              ) : (
                <FolderPlus className="size-4" />
              )}
            </span>
            {isEdit ? "Sửa bộ sưu tập" : "Tạo bộ sưu tập mới"}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs">
            {isEdit
              ? "Cập nhật tên hoặc mô tả của bộ sưu tập tri thức."
              : "Bộ sưu tập dùng để phân loại và quản lý các tài liệu tri thức trong workspace."}
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        <form
          id="collection-form"
          className="min-h-0 flex-1 overflow-y-auto"
          onSubmit={(event) => {
            event.preventDefault();
            event.stopPropagation();
            void form.handleSubmit();
          }}
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

            <form.Field name="name">
              {(field) => {
                const error = fieldError(field.state.meta.errors);
                return (
                  <Field>
                    <FieldLabel htmlFor="collection-name">
                      Tên bộ sưu tập <span className="text-destructive">*</span>
                    </FieldLabel>
                    <Input
                      id="collection-name"
                      className="text-xs"
                      placeholder="Ví dụ: Quy chế tuyển sinh 2026"
                      value={field.state.value}
                      disabled={isSubmitting}
                      onBlur={field.handleBlur}
                      onChange={(event) =>
                        field.handleChange(event.target.value)
                      }
                      autoFocus
                    />
                    {error ? (
                      <FieldError>{error}</FieldError>
                    ) : (
                      <FieldDescription>
                        Tên định danh hiển thị trong danh mục tri thức (tối đa
                        255 ký tự).
                      </FieldDescription>
                    )}
                  </Field>
                );
              }}
            </form.Field>

            <form.Field name="description">
              {(field) => {
                const error = fieldError(field.state.meta.errors);
                return (
                  <Field>
                    <FieldLabel htmlFor="collection-description">
                      Mô tả
                    </FieldLabel>
                    <Textarea
                      id="collection-description"
                      rows={4}
                      className="text-xs"
                      placeholder="Mô tả tóm tắt phạm vi, đối tượng hoặc mục đích của bộ sưu tập này..."
                      value={field.state.value}
                      disabled={isSubmitting}
                      onBlur={field.handleBlur}
                      onChange={(event) =>
                        field.handleChange(event.target.value)
                      }
                    />
                    {error ? (
                      <FieldError>{error}</FieldError>
                    ) : (
                      <FieldDescription>
                        Tùy chọn. Tối đa 2000 ký tự. Để trống để xóa mô tả hiện
                        tại khi sửa.
                      </FieldDescription>
                    )}
                  </Field>
                );
              }}
            </form.Field>
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
              disabled={isSubmitting}
              className="gap-1.5"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Đang lưu...</span>
                </>
              ) : isEdit ? (
                <>
                  <Save className="size-3.5" />
                  <span>Lưu thay đổi</span>
                </>
              ) : (
                <>
                  <FolderPlus className="size-3.5" />
                  <span>Tạo bộ sưu tập</span>
                </>
              )}
            </Button>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
