import { useForm } from "@tanstack/react-form";
import { Mail, UserRound } from "lucide-react";
import { z } from "zod";
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
import type { User, UserStatus } from "@/features/users/types";
import { getFormErrorMessage } from "@/lib/form-errors";
import { useRbac } from "@/rbac/context";

const userFormSchema = z.object({
  name: z.string().trim().min(2, "Nhập ít nhất 2 ký tự."),
  email: z.string().trim().email("Nhập địa chỉ email hợp lệ."),
  role: z.string().min(1, "Chọn một vai trò."),
  status: z.enum(["active", "inactive", "pending", "suspended"]),
});

type UserFormValues = z.infer<typeof userFormSchema>;

function fieldError(errors: unknown[]) {
  return getFormErrorMessage(errors[0]) ?? null;
}

export function UserFormSheet({
  open,
  onOpenChange,
  mode,
  user,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: "create" | "edit";
  user?: User | null;
  onSubmit: (values: UserFormValues) => Promise<void>;
}) {
  const { roles } = useRbac();
  const defaultValues: UserFormValues = {
    name: user?.name ?? "",
    email: user?.email ?? "",
    role: user?.role ?? roles.at(-1)?.name ?? "Viewer",
    status: user?.status ?? "pending",
  };
  const form = useForm({
    defaultValues,
    validators: { onSubmit: userFormSchema },
    onSubmit: async ({ value }) => {
      await onSubmit(value);
      onOpenChange(false);
    },
  });

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex w-full max-w-none flex-col overflow-hidden sm:max-w-lg"
      >
        <SheetHeader className="border-b px-5 pb-4">
          <SheetTitle>
            {mode === "create" ? "Mời người dùng" : "Chỉnh sửa người dùng"}
          </SheetTitle>
          <SheetDescription>
            {mode === "create"
              ? "Gửi lời mời tham gia không gian làm việc với cấp độ truy cập phù hợp."
              : "Cập nhật hồ sơ và cấp độ truy cập của người dùng."}
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
            <form.Field name="name">
              {(field) => {
                const error = fieldError(field.state.meta.errors);
                return (
                  <div className="grid gap-2">
                    <Label htmlFor="user-name">Họ và tên</Label>
                    <div className="relative">
                      <UserRound className="pointer-events-none absolute top-2.5 left-3 size-4 text-muted-foreground" />
                      <Input
                        id="user-name"
                        className="pl-9"
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(event) =>
                          field.handleChange(event.target.value)
                        }
                      />
                    </div>
                    {error ? (
                      <p className="type-caption text-destructive">{error}</p>
                    ) : null}
                  </div>
                );
              }}
            </form.Field>
            <form.Field name="email">
              {(field) => {
                const error = fieldError(field.state.meta.errors);
                return (
                  <div className="grid gap-2">
                    <Label htmlFor="user-email">Địa chỉ email</Label>
                    <div className="relative">
                      <Mail className="pointer-events-none absolute top-2.5 left-3 size-4 text-muted-foreground" />
                      <Input
                        id="user-email"
                        type="email"
                        className="pl-9"
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(event) =>
                          field.handleChange(event.target.value)
                        }
                      />
                    </div>
                    {error ? (
                      <p className="type-caption text-destructive">{error}</p>
                    ) : null}
                  </div>
                );
              }}
            </form.Field>
            <form.Field name="role">
              {(field) => {
                const error = fieldError(field.state.meta.errors);
                return (
                  <div className="grid gap-2">
                    <Label>Vai trò</Label>
                    <Select
                      value={field.state.value}
                      onValueChange={field.handleChange}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Chọn vai trò" />
                      </SelectTrigger>
                      <SelectContent>
                        {roles.map((role) => (
                          <SelectItem key={role.key} value={role.name}>
                            {role.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {error ? (
                      <p className="type-caption text-destructive">{error}</p>
                    ) : null}
                  </div>
                );
              }}
            </form.Field>
            <form.Field name="status">
              {(field) => (
                <div className="grid gap-2">
                  <Label>Trạng thái</Label>
                  <Select
                    value={field.state.value}
                    onValueChange={(value) =>
                      field.handleChange(value as UserStatus)
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pending">Đang chờ</SelectItem>
                      <SelectItem value="active">Đang hoạt động</SelectItem>
                      <SelectItem value="inactive">Không hoạt động</SelectItem>
                      <SelectItem value="suspended">Tạm khóa</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
            </form.Field>
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
                  {isSubmitting
                    ? "Đang lưu..."
                    : mode === "create"
                      ? "Gửi lời mời"
                      : "Lưu thay đổi"}
                </Button>
              )}
            </form.Subscribe>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}

export type { UserFormValues };
