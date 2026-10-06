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
import { useCreateFloor, useUpdateFloor } from "@/features/floors/api";
import type { Floor, FloorFormValues } from "@/features/floors/types";
import { getFormErrorMessage } from "@/lib/form-errors";

const floorFormSchema = z.object({
  floorNumber: z.number().int().min(0, "Số tầng phải lớn hơn hoặc bằng 0."),
  name: z
    .string()
    .trim()
    .min(1, "Tên tầng là bắt buộc.")
    .max(100, "Tên tầng tối đa 100 ký tự."),
});

function firstError(errors: unknown[]) {
  return getFormErrorMessage(errors[0]);
}

function getServerFieldErrors(error: ApiError) {
  return Object.fromEntries(
    Object.entries(error.fieldErrors ?? {}).map(([key, messages]) => [
      key.toLowerCase(),
      messages.join(" "),
    ]),
  );
}

export function FloorFormDialog({
  open,
  onOpenChange,
  buildingId,
  floor,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  buildingId: string;
  floor?: Floor | null;
}) {
  const isEdit = Boolean(floor);
  const createMutation = useCreateFloor();
  const updateMutation = useUpdateFloor();
  const [serverError, setServerError] = useState<string | null>(null);
  const [serverFieldErrors, setServerFieldErrors] = useState<
    Record<string, string>
  >({});

  const form = useForm({
    defaultValues: {
      floorNumber: floor?.floorNumber ?? 0,
      name: floor?.name ?? "",
    } satisfies FloorFormValues,
    validators: { onSubmit: floorFormSchema },
    onSubmit: async ({ value }) => {
      setServerError(null);
      setServerFieldErrors({});
      try {
        if (floor) {
          await updateMutation.mutateAsync({
            buildingId,
            id: floor.id,
            input: { name: value.name.trim() },
          });
        } else {
          await createMutation.mutateAsync({
            buildingId,
            input: { floorNumber: value.floorNumber, name: value.name.trim() },
          });
        }
        toast.success(
          floor
            ? "Đã cập nhật tầng thành công."
            : "Đã tạo tầng mới thành công.",
        );
        onOpenChange(false);
      } catch (error) {
        if (error instanceof ApiError) {
          setServerError(error.message);
          setServerFieldErrors(getServerFieldErrors(error));
        } else {
          setServerError("Không thể lưu tầng. Vui lòng thử lại.");
        }
      }
    },
  });

  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="flex max-h-[min(580px,calc(100vh-2rem))] w-full max-w-lg flex-col overflow-hidden">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle>
            {isEdit ? "Chỉnh sửa tầng" : "Thêm tầng mới"}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            {isEdit
              ? "Cập nhật tên tầng. Số tầng không thể thay đổi sau khi tạo."
              : "Tạo tầng mới thuộc tòa nhà đang chọn trong hệ thống."}
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

            {/* Số tầng */}
            <form.Field name="floorNumber">
              {(field) => {
                const error =
                  firstError(field.state.meta.errors) ??
                  serverFieldErrors.floornumber;
                return (
                  <Field>
                    <FieldLabel htmlFor="floor-number">
                      Số tầng{" "}
                      <span className="text-destructive font-bold">*</span>
                    </FieldLabel>
                    <Input
                      id="floor-number"
                      type="number"
                      min={0}
                      className="text-xs font-mono"
                      placeholder="Ví dụ: 1, 2, 3..."
                      value={field.state.value}
                      disabled={isEdit || isSubmitting}
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

            {/* Tên tầng */}
            <form.Field name="name">
              {(field) => {
                const error =
                  firstError(field.state.meta.errors) ?? serverFieldErrors.name;
                return (
                  <Field>
                    <FieldLabel htmlFor="floor-name">
                      Tên tầng{" "}
                      <span className="text-destructive font-bold">*</span>
                    </FieldLabel>
                    <Input
                      id="floor-name"
                      className="text-xs"
                      placeholder="Ví dụ: Tầng 1, Tầng 2, Tầng Trệt"
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
                      <span>Tạo tầng</span>
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
