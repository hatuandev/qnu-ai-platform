import { useForm } from "@tanstack/react-form";
import { Loader2, Plus, Save } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { ApiError } from "@/app/api/client";
import { Field, FieldError, FieldLabel } from "@/components/admin/field";
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
  useCreateRoomType,
  useUpdateRoomType,
} from "@/features/room-types/api";
import type { RoomType, RoomTypeFormValues } from "@/features/room-types/types";
import { getFormErrorMessage } from "@/lib/form-errors";

const roomTypeFormSchema = z.object({
  code: z
    .string()
    .trim()
    .min(1, "Mã loại phòng là bắt buộc.")
    .max(50, "Mã loại phòng tối đa 50 ký tự."),
  name: z
    .string()
    .trim()
    .min(1, "Tên loại phòng là bắt buộc.")
    .max(100, "Tên loại phòng tối đa 100 ký tự."),
  capacity: z.number().int().min(1, "Sức chứa phải lớn hơn 0."),
  description: z.string().trim(),
});

function firstError(errors: unknown[]) {
  return getFormErrorMessage(errors[0]);
}

function serverErrors(error: ApiError) {
  return Object.fromEntries(
    Object.entries(error.fieldErrors ?? {}).map(([key, messages]) => [
      key.toLowerCase(),
      messages.join(" "),
    ]),
  );
}

export function RoomTypeFormDialog({
  open,
  onOpenChange,
  roomType,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  roomType?: RoomType | null;
}) {
  const isEdit = Boolean(roomType);
  const createMutation = useCreateRoomType();
  const updateMutation = useUpdateRoomType();
  const [serverError, setServerError] = useState<string | null>(null);
  const [serverFieldErrors, setServerFieldErrors] = useState<
    Record<string, string>
  >({});

  const form = useForm({
    defaultValues: {
      code: roomType?.code ?? "",
      name: roomType?.name ?? "",
      capacity: roomType?.capacity ?? 1,
      description: roomType?.description ?? "",
    } satisfies RoomTypeFormValues,
    validators: { onSubmit: roomTypeFormSchema },
    onSubmit: async ({ value }) => {
      setServerError(null);
      setServerFieldErrors({});
      const input = {
        name: value.name.trim(),
        capacity: value.capacity,
        description: value.description.trim() || undefined,
      };
      try {
        if (roomType) {
          await updateMutation.mutateAsync({ id: roomType.id, input });
        } else {
          await createMutation.mutateAsync({
            code: value.code.trim(),
            ...input,
          });
        }
        toast.success(
          roomType
            ? "Đã cập nhật loại phòng thành công."
            : "Đã tạo loại phòng mới thành công.",
        );
        onOpenChange(false);
      } catch (error) {
        if (error instanceof ApiError) {
          setServerError(error.message);
          setServerFieldErrors(serverErrors(error));
        } else {
          setServerError("Không thể lưu loại phòng. Vui lòng thử lại.");
        }
      }
    },
  });

  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="flex max-h-[min(740px,calc(100vh-2rem))] w-full max-w-xl flex-col overflow-hidden">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle>
            {isEdit ? "Chỉnh sửa loại phòng" : "Thêm loại phòng mới"}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            {isEdit
              ? "Cập nhật sức chứa và mô tả loại phòng. Mã loại phòng không thể thay đổi sau khi tạo."
              : "Tạo loại phòng mới cho danh mục ký túc xá."}
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
          <div className="grid gap-5 px-4 py-4 lg:px-1">
            {serverError ? (
              <div
                role="alert"
                className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
              >
                {serverError}
              </div>
            ) : null}

            {/* Mã & Sức chứa */}
            <div className="grid gap-5 sm:grid-cols-2">
              <form.Field name="code">
                {(field) => {
                  const error =
                    firstError(field.state.meta.errors) ??
                    serverFieldErrors.code;
                  return (
                    <Field>
                      <FieldLabel htmlFor="room-type-code">
                        Mã loại phòng{" "}
                        <span className="text-destructive font-bold">*</span>
                      </FieldLabel>
                      <Input
                        id="room-type-code"
                        className="text-xs font-mono"
                        placeholder="Ví dụ: LP.4N, LP.8N"
                        value={field.state.value}
                        disabled={isEdit || isSubmitting}
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

              <form.Field name="capacity">
                {(field) => {
                  const error =
                    firstError(field.state.meta.errors) ??
                    serverFieldErrors.capacity;
                  return (
                    <Field>
                      <FieldLabel htmlFor="room-type-capacity">
                        Sức chứa (người){" "}
                        <span className="text-destructive font-bold">*</span>
                      </FieldLabel>
                      <Input
                        id="room-type-capacity"
                        type="number"
                        min={1}
                        className="text-xs font-mono"
                        placeholder="Ví dụ: 4, 8"
                        value={field.state.value}
                        disabled={isSubmitting}
                        onBlur={field.handleBlur}
                        onChange={(event) =>
                          field.handleChange(Number(event.target.value))
                        }
                        aria-invalid={Boolean(error)}
                      />
                      {error ? <FieldError>{error}</FieldError> : null}
                    </Field>
                  );
                }}
              </form.Field>
            </div>

            {/* Tên loại phòng */}
            <form.Field name="name">
              {(field) => {
                const error =
                  firstError(field.state.meta.errors) ?? serverFieldErrors.name;
                return (
                  <Field>
                    <FieldLabel htmlFor="room-type-name">
                      Tên loại phòng{" "}
                      <span className="text-destructive font-bold">*</span>
                    </FieldLabel>
                    <Input
                      id="room-type-name"
                      className="text-xs"
                      placeholder="Ví dụ: Phòng 4 người, Phòng dịch vụ 2 người"
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

            {/* Mô tả */}
            <form.Field name="description">
              {(field) => {
                const error =
                  firstError(field.state.meta.errors) ??
                  serverFieldErrors.description;
                return (
                  <Field>
                    <FieldLabel htmlFor="room-type-description">
                      Mô tả
                    </FieldLabel>
                    <Textarea
                      id="room-type-description"
                      rows={3}
                      className="text-xs"
                      placeholder="Nhập thông tin mô tả loại phòng (tùy chọn)..."
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
          </div>

          <ResponsiveDialogFooter className="border-t px-4 pt-4 lg:px-1">
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
                  ) : isEdit ? (
                    <>
                      <Save className="size-3.5" />
                      <span>Lưu thay đổi</span>
                    </>
                  ) : (
                    <>
                      <Plus className="size-3.5" />
                      <span>Tạo loại phòng</span>
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
