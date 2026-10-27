import { useForm } from "@tanstack/react-form";
import { useEffect, useState } from "react";
import { z } from "zod";
import { Field, FieldError, FieldLabel } from "@/components/admin/field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import { PermissionEditor } from "@/features/roles/permission-editor";
import { getFormErrorMessage } from "@/lib/form-errors";
import type { PermissionKey } from "@/rbac/catalog";
import type { RoleRecord, RoleStatus } from "@/rbac/demo";
import { canRenameRoleKey } from "@/rbac/policy";

const roleFormSchema = z.object({
  name: z.string().trim().min(2, "Nhập ít nhất 2 ký tự."),
  key: z
    .string()
    .trim()
    .min(2, "Nhập role key.")
    .regex(
      /^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$/,
      "Role key chỉ dùng chữ thường, số và dấu gạch dưới.",
    ),
  description: z.string().trim().max(160, "Mô tả tối đa 160 ký tự."),
  status: z.enum(["active", "inactive"]),
});

type RoleFormValues = z.infer<typeof roleFormSchema>;
type RoleFormMode = "create" | "edit" | "duplicate";

function fieldError(errors: unknown[]) {
  return getFormErrorMessage(errors[0]) ?? null;
}

export function RoleFormSheet({
  open,
  onOpenChange,
  mode,
  role,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: RoleFormMode;
  role?: RoleRecord | null;
  onSubmit: (
    values: RoleFormValues,
    permissions: PermissionKey[],
  ) => Promise<void>;
}) {
  const [permissions, setPermissions] = useState<PermissionKey[]>(
    role?.permissions ?? [],
  );
  useEffect(() => {
    if (open) setPermissions(role?.permissions ?? []);
  }, [open, role?.permissions]);
  const defaultValues: RoleFormValues = {
    name:
      mode === "duplicate"
        ? `Bản sao của ${role?.name ?? "vai trò"}`
        : (role?.name ?? ""),
    key:
      mode === "duplicate" ? `${role?.key ?? "role"}_copy` : (role?.key ?? ""),
    description: role?.description ?? "",
    status: role?.status ?? "active",
  };
  const form = useForm({
    defaultValues,
    validators: { onSubmit: roleFormSchema },
    onSubmit: async ({ value }) => {
      await onSubmit(value, permissions);
      onOpenChange(false);
    },
  });
  const keyDisabled =
    mode === "edit" && Boolean(role && !canRenameRoleKey(role));
  const title =
    mode === "edit"
      ? "Chỉnh sửa vai trò"
      : mode === "duplicate"
        ? "Nhân bản vai trò"
        : "Tạo vai trò";

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex w-full max-w-none flex-col overflow-hidden sm:max-w-2xl"
      >
        <SheetHeader className="border-b px-5 pb-4">
          <SheetTitle>{title}</SheetTitle>
          <SheetDescription>
            {mode === "edit"
              ? "Cập nhật thông tin và quyền được gán cho vai trò."
              : "Tạo một cấp độ truy cập mới cho không gian làm việc."}
          </SheetDescription>
        </SheetHeader>
        <form
          className="flex min-h-0 flex-1 flex-col overflow-hidden"
          onSubmit={(event) => {
            event.preventDefault();
            event.stopPropagation();
            void form.handleSubmit();
          }}
        >
          <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-5">
            <div className="grid gap-5 sm:grid-cols-2">
              <form.Field name="name">
                {(field) => {
                  const error = fieldError(field.state.meta.errors);
                  return (
                    <div className="grid gap-2">
                      <Label htmlFor="role-name">Tên vai trò</Label>
                      <Input
                        id="role-name"
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(event) =>
                          field.handleChange(event.target.value)
                        }
                      />
                      {error ? (
                        <p className="type-caption text-destructive">{error}</p>
                      ) : null}
                    </div>
                  );
                }}
              </form.Field>
              <form.Field name="key">
                {(field) => {
                  const error = fieldError(field.state.meta.errors);
                  return (
                    <div className="grid gap-2">
                      <Label htmlFor="role-key">Role key</Label>
                      <Input
                        id="role-key"
                        value={field.state.value}
                        disabled={keyDisabled}
                        onBlur={field.handleBlur}
                        onChange={(event) =>
                          field.handleChange(
                            event.target.value
                              .toLowerCase()
                              .replace(/[\s-]+/g, "_")
                              .replace(/[^a-z0-9_]/g, ""),
                          )
                        }
                      />
                      <p className="type-caption text-muted-foreground">
                        {keyDisabled
                          ? "Role key hệ thống không thể thay đổi."
                          : "Dùng chữ thường, số và dấu gạch dưới."}
                      </p>
                      {error ? (
                        <p className="type-caption text-destructive">{error}</p>
                      ) : null}
                    </div>
                  );
                }}
              </form.Field>
            </div>
            <form.Field name="description">
              {(field) => {
                const error = fieldError(field.state.meta.errors);
                return (
                  <Field>
                    <FieldLabel htmlFor="role-description">Mô tả</FieldLabel>
                    <Textarea
                      id="role-description"
                      value={field.state.value}
                      aria-invalid={Boolean(error)}
                      aria-describedby={
                        error ? "role-description-error" : undefined
                      }
                      onBlur={field.handleBlur}
                      onChange={(event) =>
                        field.handleChange(event.target.value)
                      }
                      rows={3}
                    />
                    {error ? (
                      <FieldError id="role-description-error">
                        {error}
                      </FieldError>
                    ) : null}
                  </Field>
                );
              }}
            </form.Field>
            <form.Field name="status">
              {(field) => (
                <div className="grid gap-2 sm:max-w-xs">
                  <Label>Trạng thái</Label>
                  <Select
                    value={field.state.value}
                    onValueChange={(value) =>
                      field.handleChange(value as RoleStatus)
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="active">Đang hoạt động</SelectItem>
                      <SelectItem value="inactive">Không hoạt động</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
            </form.Field>
            <div className="space-y-3">
              <div>
                <h2 className="text-sm font-semibold">Gán quyền hạn</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Chọn những thao tác mà vai trò này được phép thực hiện.
                </p>
              </div>
              <PermissionEditor value={permissions} onChange={setPermissions} />
            </div>
          </div>
          <div className="flex shrink-0 flex-col-reverse gap-2 border-t bg-background px-5 py-4 sm:flex-row sm:justify-end">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Hủy
            </Button>
            <form.Subscribe
              selector={(state) => [state.canSubmit, state.isSubmitting]}
            >
              {([canSubmit, isSubmitting]) => (
                <Button type="submit" disabled={!canSubmit || isSubmitting}>
                  {isSubmitting ? "Đang lưu..." : "Lưu vai trò"}
                </Button>
              )}
            </form.Subscribe>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}

export type { RoleFormMode, RoleFormValues };
