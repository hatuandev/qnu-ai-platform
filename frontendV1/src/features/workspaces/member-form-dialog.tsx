import { useForm } from "@tanstack/react-form";
import { Loader2, UserPlus } from "lucide-react";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAddMember } from "@/features/workspaces/queries";
import {
  memberCreateSchema,
  WORKSPACE_ROLE_LABELS,
} from "@/features/workspaces/schemas";
import type { WorkspaceRole } from "@/features/workspaces/types";
import { getFormErrorMessage } from "@/lib/form-errors";

const ROLES: WorkspaceRole[] = ["admin", "editor", "reviewer", "member"];

function fieldError(errors: unknown[]) {
  return getFormErrorMessage(errors[0]);
}

export function MemberFormDialog({
  open,
  onOpenChange,
  workspaceId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
}) {
  const mutation = useAddMember(workspaceId);
  const [serverError, setServerError] = useState<string | null>(null);

  const form = useForm({
    defaultValues: {
      actor_ref: "",
      display_name: "",
      role: "member" as WorkspaceRole,
    },
    validators: { onSubmit: memberCreateSchema },
    onSubmit: async ({ value }) => {
      setServerError(null);
      try {
        await mutation.mutateAsync({
          actor_ref: value.actor_ref.trim(),
          display_name: value.display_name.trim() || undefined,
          role: value.role,
        });
        toast.success("Đã thêm thành viên vào workspace.");
        onOpenChange(false);
      } catch (error) {
        setServerError(
          error instanceof ApiProblemError
            ? error.message
            : "Không thêm được thành viên.",
        );
      }
    },
  });

  useEffect(() => {
    if (open) {
      form.reset({
        actor_ref: "",
        display_name: "",
        role: "member",
      });
      setServerError(null);
    }
  }, [open, form.reset]);

  return (
    <ResponsiveDialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setServerError(null);
        onOpenChange(next);
      }}
    >
      <ResponsiveDialogContent className="flex max-h-[min(780px,calc(100vh-2rem))] w-full max-w-lg flex-col overflow-hidden p-0 gap-0">
        <ResponsiveDialogHeader className="border-b bg-muted/20 px-4 py-4">
          <ResponsiveDialogTitle className="flex items-center gap-2">
            <span className="flex size-8 items-center justify-center rounded-lg bg-muted">
              <UserPlus className="size-4" />
            </span>
            Thêm thành viên
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs">
            API hiện chỉ thêm thành viên trực tiếp bằng <code>actor_ref</code>,
            chưa gửi email mời. Nếu người này đã bị thu hồi, thao tác này khôi
            phục lại membership cũ.
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

            <form.Field name="actor_ref">
              {(field) => {
                const error = fieldError(field.state.meta.errors);
                return (
                  <Field>
                    <FieldLabel htmlFor="member-actor-ref">
                      actor_ref
                    </FieldLabel>
                    <Input
                      id="member-actor-ref"
                      className="font-mono text-xs"
                      placeholder="act_abc123"
                      value={field.state.value}
                      disabled={mutation.isPending}
                      onBlur={field.handleBlur}
                      onChange={(event) =>
                        field.handleChange(event.target.value)
                      }
                      aria-invalid={Boolean(error)}
                    />
                    <FieldDescription className="text-xs">
                      Định danh opaque, phân biệt hoa thường. Không dùng email
                      hay tên hiển thị thay cho định danh này.
                    </FieldDescription>
                    {error ? <FieldError>{error}</FieldError> : null}
                  </Field>
                );
              }}
            </form.Field>

            <form.Field name="display_name">
              {(field) => {
                const error = fieldError(field.state.meta.errors);
                return (
                  <Field>
                    <FieldLabel htmlFor="member-display-name">
                      Tên hiển thị
                    </FieldLabel>
                    <Input
                      id="member-display-name"
                      className="text-xs"
                      placeholder="Nguyễn Văn A (tùy chọn)"
                      value={field.state.value}
                      disabled={mutation.isPending}
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

            <form.Field name="role">
              {(field) => {
                const error = fieldError(field.state.meta.errors);
                return (
                  <Field>
                    <FieldLabel htmlFor="member-role">Vai trò</FieldLabel>
                    <Select
                      value={field.state.value}
                      onValueChange={(value) =>
                        field.handleChange(value as WorkspaceRole)
                      }
                      disabled={mutation.isPending}
                    >
                      <SelectTrigger id="member-role" className="text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {ROLES.map((role) => (
                          <SelectItem
                            key={role}
                            value={role}
                            className="text-xs"
                          >
                            {WORKSPACE_ROLE_LABELS[role]}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FieldDescription className="text-xs">
                      Vai trò này chỉ áp dụng trong workspace hiện tại, không
                      phải quyền nền tảng.
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
              disabled={mutation.isPending}
              onClick={() => onOpenChange(false)}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              size="sm"
              className="gap-1.5 text-xs font-semibold"
              disabled={mutation.isPending}
            >
              {mutation.isPending ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Đang thêm...</span>
                </>
              ) : (
                <>
                  <UserPlus className="size-3.5" />
                  <span>Thêm thành viên</span>
                </>
              )}
            </Button>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
