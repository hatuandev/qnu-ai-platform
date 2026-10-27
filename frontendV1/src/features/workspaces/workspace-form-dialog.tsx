import { useForm } from "@tanstack/react-form";
import { Loader2, Plus, Save } from "lucide-react";
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
import { buildWorkspacePatch, isEmptyPatch } from "@/features/workspaces/patch";
import {
  useCreateWorkspace,
  useUpdateWorkspace,
} from "@/features/workspaces/queries";
import {
  workspaceCreateSchema,
  workspaceUpdateSchema,
} from "@/features/workspaces/schemas";
import type { Workspace } from "@/features/workspaces/types";
import { getFormErrorMessage } from "@/lib/form-errors";

function fieldError(errors: unknown[]) {
  return getFormErrorMessage(errors[0]);
}

export function WorkspaceFormDialog({
  open,
  onOpenChange,
  workspace,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspace?: Workspace | null;
}) {
  const isEdit = Boolean(workspace);
  const createMutation = useCreateWorkspace();
  const updateMutation = useUpdateWorkspace(workspace?.id ?? "");
  const [serverError, setServerError] = useState<string | null>(null);

  const form = useForm({
    defaultValues: {
      code: workspace?.code ?? "",
      name: workspace?.name ?? "",
      description: workspace?.description ?? "",
    },
    validators: {
      onSubmit: isEdit ? workspaceUpdateSchema : workspaceCreateSchema,
    },
    onSubmit: async ({ value }) => {
      setServerError(null);
      try {
        if (workspace) {
          const patch = buildWorkspacePatch(
            { name: workspace.name, description: workspace.description },
            { name: value.name, description: value.description },
          );
          if (isEmptyPatch(patch)) {
            toast.info("Không có thay đổi nào để lưu.");
            onOpenChange(false);
            return;
          }
          await updateMutation.mutateAsync(patch);
          toast.success("Đã cập nhật workspace.");
        } else {
          await createMutation.mutateAsync({
            code: value.code.trim(),
            name: value.name.trim(),
            description: value.description.trim() || undefined,
          });
          toast.success("Đã tạo workspace.");
        }
        onOpenChange(false);
      } catch (error) {
        setServerError(
          error instanceof ApiProblemError
            ? error.message
            : "Không lưu được workspace. Vui lòng thử lại.",
        );
      }
    },
  });

  useEffect(() => {
    if (open) {
      form.reset({
        code: workspace?.code ?? "",
        name: workspace?.name ?? "",
        description: workspace?.description ?? "",
      });
      setServerError(null);
    }
  }, [open, workspace, form.reset]);

  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  return (
    <ResponsiveDialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setServerError(null);
        onOpenChange(next);
      }}
    >
      <ResponsiveDialogContent className="flex max-h-[min(780px,calc(100vh-2rem))] w-full max-w-xl flex-col overflow-hidden p-0 gap-0">
        <ResponsiveDialogHeader className="border-b bg-muted/20 px-4 py-4">
          <ResponsiveDialogTitle className="flex items-center gap-2">
            <span className="flex size-8 items-center justify-center rounded-lg bg-muted">
              {isEdit ? (
                <Save className="size-4" />
              ) : (
                <Plus className="size-4" />
              )}
            </span>
            {isEdit ? "Sửa workspace" : "Tạo workspace"}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs">
            {isEdit
              ? "Mã workspace không sửa được: PATCH chỉ nhận tên, mô tả và trạng thái."
              : "Mã workspace là duy nhất, chỉ gồm chữ thường, số, '-' hoặc '_'."}
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        <form
          className="min-h-0 flex-1 overflow-y-auto"
          onSubmit={(event) => {
            event.preventDefault();
            event.stopPropagation();
            void form.handleSubmit();
          }}
        >
          <div className="grid gap-4 px-4 py-4">
            {serverError ? (
              <p
                role="alert"
                className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
              >
                {serverError}
              </p>
            ) : null}

            <form.Field name="code">
              {(field) => {
                const error = fieldError(field.state.meta.errors);
                return (
                  <Field>
                    <FieldLabel htmlFor="workspace-code">
                      Mã workspace
                    </FieldLabel>
                    <Input
                      id="workspace-code"
                      className="text-xs font-mono"
                      placeholder="vi-du: khoa-cntt"
                      value={field.state.value}
                      disabled={isEdit || isSubmitting}
                      onBlur={field.handleBlur}
                      onChange={(event) =>
                        field.handleChange(event.target.value)
                      }
                      aria-invalid={Boolean(error)}
                    />
                    <FieldDescription className="text-xs">
                      {isEdit
                        ? "Không thể đổi mã sau khi tạo."
                        : "2–64 ký tự, chữ thường và số."}
                    </FieldDescription>
                    {error ? <FieldError>{error}</FieldError> : null}
                  </Field>
                );
              }}
            </form.Field>

            <form.Field name="name">
              {(field) => {
                const error = fieldError(field.state.meta.errors);
                return (
                  <Field>
                    <FieldLabel htmlFor="workspace-name">
                      Tên hiển thị
                    </FieldLabel>
                    <Input
                      id="workspace-name"
                      className="text-xs"
                      placeholder="Khoa Công nghệ thông tin"
                      value={field.state.value}
                      disabled={isSubmitting}
                      onBlur={field.handleBlur}
                      onChange={(event) =>
                        field.handleChange(event.target.value)
                      }
                      aria-invalid={Boolean(error)}
                    />
                    {error ? <FieldError>{error}</FieldError> : null}
                  </Field>
                );
              }}
            </form.Field>

            <form.Field name="description">
              {(field) => {
                const error = fieldError(field.state.meta.errors);
                return (
                  <Field>
                    <FieldLabel htmlFor="workspace-description">
                      Mô tả
                    </FieldLabel>
                    <Textarea
                      id="workspace-description"
                      rows={3}
                      className="text-xs"
                      placeholder="Mục đích sử dụng workspace (tùy chọn)"
                      value={field.state.value}
                      disabled={isSubmitting}
                      onBlur={field.handleBlur}
                      onChange={(event) =>
                        field.handleChange(event.target.value)
                      }
                      aria-invalid={Boolean(error)}
                    />
                    <FieldDescription className="text-xs">
                      Để trống và lưu sẽ xóa mô tả hiện tại.
                    </FieldDescription>
                    {error ? <FieldError>{error}</FieldError> : null}
                  </Field>
                );
              }}
            </form.Field>
          </div>

          <ResponsiveDialogFooter className="border-t bg-card px-4 py-3">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="text-xs"
              disabled={isSubmitting}
              onClick={() => onOpenChange(false)}
            >
              Hủy
            </Button>
            <form.Subscribe
              selector={(state) => [state.canSubmit, state.isSubmitting]}
            >
              {([canSubmit, formSubmitting]) => (
                <Button
                  type="submit"
                  size="sm"
                  className="gap-1.5 text-xs font-semibold"
                  disabled={!canSubmit || formSubmitting || isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="size-3.5 animate-spin" />
                      <span>Đang lưu...</span>
                    </>
                  ) : (
                    <>
                      <Save className="size-3.5" />
                      <span>{isEdit ? "Lưu thay đổi" : "Tạo workspace"}</span>
                    </>
                  )}
                </Button>
              )}
            </form.Subscribe>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
