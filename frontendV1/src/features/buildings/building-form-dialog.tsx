import { useForm } from "@tanstack/react-form";
import { Loader2, Plus, Save } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { ApiError } from "@/app/api/client";
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
import { useCreateBuilding, useUpdateBuilding } from "@/features/buildings/api";
import type { Building, BuildingFormValues } from "@/features/buildings/types";
import { getFormErrorMessage } from "@/lib/form-errors";

export const buildingFormSchema = z.object({
  code: z
    .string()
    .trim()
    .min(1, "Mã tòa nhà là bắt buộc.")
    .max(50, "Mã tòa nhà tối đa 50 ký tự."),
  name: z
    .string()
    .trim()
    .min(1, "Tên tòa nhà là bắt buộc.")
    .max(200, "Tên tòa nhà tối đa 200 ký tự."),
  address: z.string().trim().max(500, "Địa chỉ tối đa 500 ký tự."),
  description: z.string().trim().max(2000, "Mô tả tối đa 2000 ký tự."),
});

function fieldError(errors: unknown[]) {
  return getFormErrorMessage(errors[0]);
}

function getServerFieldErrors(error: ApiError) {
  const errors = error.fieldErrors ?? {};
  return Object.fromEntries(
    Object.entries(errors).map(([key, messages]) => [
      key.toLowerCase(),
      messages.join(" "),
    ]),
  );
}

export function BuildingFormDialog({
  open,
  onOpenChange,
  building,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  building?: Building | null;
}) {
  const isEdit = Boolean(building);
  const createMutation = useCreateBuilding();
  const updateMutation = useUpdateBuilding();
  const [serverError, setServerError] = useState<string | null>(null);
  const [serverFieldErrors, setServerFieldErrors] = useState<
    Record<string, string>
  >({});

  const form = useForm({
    defaultValues: {
      code: building?.code ?? "",
      name: building?.name ?? "",
      address: building?.address ?? "",
      description: building?.description ?? "",
    } satisfies BuildingFormValues,
    validators: { onSubmit: buildingFormSchema },
    onSubmit: async ({ value }) => {
      setServerError(null);
      setServerFieldErrors({});
      const input = {
        code: value.code.trim(),
        name: value.name.trim(),
        address: value.address.trim() || undefined,
        description: value.description.trim() || undefined,
      };

      try {
        if (building) {
          await updateMutation.mutateAsync({
            id: building.id,
            input: {
              name: input.name,
              address: input.address,
              description: input.description,
            },
          });
        } else {
          await createMutation.mutateAsync(input);
        }
        toast.success(
          building
            ? "Đã cập nhật tòa nhà thành công."
            : "Đã tạo tòa nhà mới thành công.",
        );
        onOpenChange(false);
      } catch (error) {
        if (error instanceof ApiError) {
          setServerError(error.message);
          setServerFieldErrors(getServerFieldErrors(error));
        } else {
          setServerError("Không thể lưu tòa nhà. Vui lòng thử lại.");
        }
      }
    },
  });

  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="flex max-h-[min(780px,calc(100vh-2rem))] w-full max-w-xl flex-col overflow-hidden">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle>
            {isEdit ? "Chỉnh sửa tòa nhà" : "Thêm tòa nhà mới"}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            {isEdit
              ? "Cập nhật thông tin tòa nhà. Mã tòa nhà không thể thay đổi sau khi tạo."
              : "Tạo tòa nhà mới trong danh mục ký túc xá."}
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

            {/* Mã tòa nhà */}
            <form.Field name="code">
              {(field) => {
                const error =
                  fieldError(field.state.meta.errors) ?? serverFieldErrors.code;
                return (
                  <Field>
                    <FieldLabel htmlFor="building-code">
                      Mã tòa nhà{" "}
                      <span className="text-destructive font-bold">*</span>
                    </FieldLabel>
                    <Input
                      id="building-code"
                      className="text-xs font-mono"
                      placeholder="Ví dụ: K1, K2, KTX-A"
                      value={field.state.value}
                      disabled={isEdit || isSubmitting}
                      onBlur={field.handleBlur}
                      onChange={(event) =>
                        field.handleChange(event.target.value)
                      }
                      aria-invalid={Boolean(error)}
                    />
                    <FieldDescription className="text-xs">
                      Mã định danh duy nhất của tòa nhà, tối đa 50 ký tự.
                    </FieldDescription>
                    {error ? <FieldError>{error}</FieldError> : null}
                  </Field>
                );
              }}
            </form.Field>

            {/* Tên tòa nhà */}
            <form.Field name="name">
              {(field) => {
                const error =
                  fieldError(field.state.meta.errors) ?? serverFieldErrors.name;
                return (
                  <Field>
                    <FieldLabel htmlFor="building-name">
                      Tên tòa nhà{" "}
                      <span className="text-destructive font-bold">*</span>
                    </FieldLabel>
                    <Input
                      id="building-name"
                      className="text-xs"
                      placeholder="Ví dụ: Ký túc xá Khu A"
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

            {/* Địa chỉ */}
            <form.Field name="address">
              {(field) => {
                const error =
                  fieldError(field.state.meta.errors) ??
                  serverFieldErrors.address;
                return (
                  <Field>
                    <FieldLabel htmlFor="building-address">Địa chỉ</FieldLabel>
                    <Input
                      id="building-address"
                      className="text-xs"
                      placeholder="Ví dụ: 170 An Dương Vương, TP. Quy Nhơn"
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
                  fieldError(field.state.meta.errors) ??
                  serverFieldErrors.description;
                return (
                  <Field>
                    <FieldLabel htmlFor="building-description">
                      Mô tả
                    </FieldLabel>
                    <Textarea
                      id="building-description"
                      rows={3}
                      className="text-xs"
                      placeholder="Nhập mô tả thêm về tòa nhà (tùy chọn)..."
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
                      <span>Tạo tòa nhà</span>
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
