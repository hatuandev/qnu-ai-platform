import { useForm } from "@tanstack/react-form";
import { useState } from "react";
import { z } from "zod";
import { ApiError } from "@/app/api/client";
import { DatePicker } from "@/components/admin/date-pickers";
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
import { Switch } from "@/components/ui/switch";
import {
  useCreateAcademicYear,
  useUpdateAcademicYear,
} from "@/features/academic-years/api";
import type {
  AcademicYear,
  AcademicYearFormValues,
} from "@/features/academic-years/types";
import { formatDateOnly, parseDateOnly } from "@/lib/date-utils";
import { getFormErrorMessage } from "@/lib/form-errors";

const schema = z
  .object({
    code: z
      .string()
      .trim()
      .min(1, "Mã năm học là bắt buộc.")
      .max(20, "Mã năm học tối đa 20 ký tự."),
    name: z
      .string()
      .trim()
      .min(1, "Tên năm học là bắt buộc.")
      .max(100, "Tên năm học tối đa 100 ký tự."),
    startDate: z.date({ message: "Ngày bắt đầu là bắt buộc." }),
    endDate: z.date({ message: "Ngày kết thúc là bắt buộc." }),
    isCurrent: z.boolean(),
  })
  .refine((value) => value.endDate > value.startDate, {
    path: ["endDate"],
    message: "Ngày kết thúc phải sau ngày bắt đầu.",
  });
function firstError(errors: unknown[]) {
  return getFormErrorMessage(errors[0]);
}
function mapErrors(error: ApiError) {
  return Object.fromEntries(
    Object.entries(error.fieldErrors ?? {}).map(([key, messages]) => [
      key.toLowerCase(),
      messages.join(" "),
    ]),
  );
}

export function AcademicYearFormDialog({
  open,
  onOpenChange,
  academicYear,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  academicYear?: AcademicYear | null;
}) {
  const isEdit = Boolean(academicYear);
  const createMutation = useCreateAcademicYear();
  const updateMutation = useUpdateAcademicYear();
  const [serverError, setServerError] = useState<string | null>(null);
  const [serverFieldErrors, setServerFieldErrors] = useState<
    Record<string, string>
  >({});
  const form = useForm({
    defaultValues: {
      code: academicYear?.code ?? "",
      name: academicYear?.name ?? "",
      startDate: parseDateOnly(academicYear?.startDate),
      endDate: parseDateOnly(academicYear?.endDate),
      isCurrent: academicYear?.isCurrent ?? false,
    } satisfies AcademicYearFormValues,
    validators: { onSubmit: schema },
    onSubmit: async ({ value }) => {
      setServerError(null);
      setServerFieldErrors({});
      const input = {
        name: value.name.trim(),
        startDate: formatDateOnly(value.startDate),
        endDate: formatDateOnly(value.endDate),
        isCurrent: value.isCurrent,
      };
      try {
        if (academicYear)
          await updateMutation.mutateAsync({ id: academicYear.id, input });
        else
          await createMutation.mutateAsync({
            code: value.code.trim(),
            ...input,
          });
        onOpenChange(false);
      } catch (error) {
        if (error instanceof ApiError) {
          setServerError(error.message);
          setServerFieldErrors(mapErrors(error));
        } else setServerError("Không thể lưu năm học. Vui lòng thử lại.");
      }
    },
  });
  const isSubmitting = createMutation.isPending || updateMutation.isPending;
  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="flex max-h-[min(760px,calc(100vh-2rem))] w-full max-w-xl flex-col overflow-hidden">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle>
            {isEdit ? "Chỉnh sửa năm học" : "Thêm năm học"}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            {isEdit
              ? "Cập nhật thời gian và trạng thái năm học."
              : "Tạo năm học mới cho cấu hình học vụ."}
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
                className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive"
              >
                {serverError}
              </div>
            ) : null}
            <form.Field name="code">
              {(field) => {
                const error =
                  firstError(field.state.meta.errors) ?? serverFieldErrors.code;
                return (
                  <Field>
                    <FieldLabel htmlFor="academic-year-code">
                      Mã năm học
                    </FieldLabel>
                    <Input
                      id="academic-year-code"
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
            <form.Field name="name">
              {(field) => {
                const error =
                  firstError(field.state.meta.errors) ?? serverFieldErrors.name;
                return (
                  <Field>
                    <FieldLabel htmlFor="academic-year-name">
                      Tên năm học
                    </FieldLabel>
                    <Input
                      id="academic-year-name"
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
            <div className="grid gap-5 sm:grid-cols-2">
              <form.Field name="startDate">
                {(field) => {
                  const error =
                    firstError(field.state.meta.errors) ??
                    serverFieldErrors.startdate;
                  return (
                    <Field>
                      <FieldLabel htmlFor="academic-year-start">
                        Ngày bắt đầu
                      </FieldLabel>
                      <DatePicker
                        id="academic-year-start"
                        value={field.state.value}
                        disabled={isSubmitting}
                        onBlur={field.handleBlur}
                        onChange={(value) => field.handleChange(value)}
                        onValidationChange={(message) => {
                          if (message)
                            field.setMeta((meta) => ({
                              ...meta,
                              errors: [message],
                            }));
                        }}
                        aria-invalid={Boolean(error)}
                      />
                      {error ? <FieldError>{error}</FieldError> : null}
                    </Field>
                  );
                }}
              </form.Field>
              <form.Field name="endDate">
                {(field) => {
                  const error =
                    firstError(field.state.meta.errors) ??
                    serverFieldErrors.enddate;
                  return (
                    <Field>
                      <FieldLabel htmlFor="academic-year-end">
                        Ngày kết thúc
                      </FieldLabel>
                      <DatePicker
                        id="academic-year-end"
                        value={field.state.value}
                        disabled={isSubmitting}
                        minDate={form.getFieldValue("startDate")}
                        onBlur={field.handleBlur}
                        onChange={(value) => field.handleChange(value)}
                        onValidationChange={(message) => {
                          if (message)
                            field.setMeta((meta) => ({
                              ...meta,
                              errors: [message],
                            }));
                        }}
                        aria-invalid={Boolean(error)}
                      />
                      {error ? <FieldError>{error}</FieldError> : null}
                    </Field>
                  );
                }}
              </form.Field>
            </div>
            <form.Field name="isCurrent">
              {(field) => (
                <div className="flex items-center justify-between rounded-md border px-3 py-3">
                  <div>
                    <p className="text-sm font-medium">
                      Đặt là năm học hiện tại
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Hệ thống sẽ tự bỏ trạng thái hiện tại của năm học khác.
                    </p>
                  </div>
                  <Switch
                    checked={field.state.value}
                    disabled={isSubmitting}
                    onCheckedChange={field.handleChange}
                  />
                </div>
              )}
            </form.Field>
          </div>
          <ResponsiveDialogFooter className="border-t px-4 pt-4 lg:px-1">
            <Button
              type="button"
              variant="outline"
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
                  disabled={!canSubmit || formSubmitting || isSubmitting}
                >
                  {isSubmitting
                    ? "Đang lưu..."
                    : isEdit
                      ? "Lưu thay đổi"
                      : "Tạo năm học"}
                </Button>
              )}
            </form.Subscribe>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
