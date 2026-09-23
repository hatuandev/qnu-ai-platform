import { useForm } from "@tanstack/react-form";
import { z } from "zod";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type {
  ResidenceContract,
  ResidenceContractDetail,
  ResidenceContractInput,
  ResidenceContractUpdateInput,
} from "@/features/residence-contracts/types";
import type { Residence } from "@/features/residences/types";
import { formatDateOnly, parseDateOnly } from "@/lib/date-utils";
import { getFormErrorMessage } from "@/lib/form-errors";

const formSchema = z
  .object({
    residenceId: z.string().min(1, "Hồ sơ cư trú là bắt buộc."),
    effectiveFrom: z.date({ message: "Ngày bắt đầu là bắt buộc." }),
    effectiveTo: z.date({ message: "Ngày kết thúc là bắt buộc." }),
    totalAmount: z.union([
      z.number().min(0, "Số tiền không được âm."),
      z.undefined(),
    ]),
    paymentPlan: z.enum(["one_time", "monthly"]),
    currency: z.string().trim().length(3, "Mã tiền tệ gồm 3 ký tự."),
    note: z.string().max(2000, "Ghi chú tối đa 2.000 ký tự."),
  })
  .refine((value) => value.effectiveTo >= value.effectiveFrom, {
    message: "Ngày kết thúc phải sau ngày bắt đầu.",
    path: ["effectiveTo"],
  });

type FormValues = {
  residenceId: string;
  effectiveFrom?: Date;
  effectiveTo?: Date;
  totalAmount?: number;
  paymentPlan: "one_time" | "monthly";
  currency: string;
  note: string;
};

function firstError(errors: unknown[]) {
  return errors.length ? getFormErrorMessage(errors[0]) : undefined;
}

export function ResidenceContractDialog({
  open,
  contract,
  residences,
  onOpenChange,
  onCreate,
  onUpdate,
  isSubmitting,
}: {
  open: boolean;
  contract?: ResidenceContract | ResidenceContractDetail | null;
  residences: Residence[];
  onOpenChange: (open: boolean) => void;
  onCreate: (input: ResidenceContractInput) => Promise<void>;
  onUpdate: (id: string, input: ResidenceContractUpdateInput) => Promise<void>;
  isSubmitting: boolean;
}) {
  const isEdit = Boolean(contract);
  const contractNote =
    contract && "note" in contract ? (contract.note ?? "") : "";
  const defaultValues: FormValues = {
    residenceId: contract?.residenceId ?? residences[0]?.id ?? "",
    effectiveFrom: parseDateOnly(contract?.effectiveFrom) ?? new Date(),
    effectiveTo:
      parseDateOnly(contract?.effectiveTo) ??
      new Date(new Date().setFullYear(new Date().getFullYear() + 1)),
    totalAmount: contract?.totalAmount,
    paymentPlan: contract?.paymentPlan === "monthly" ? "monthly" : "one_time",
    currency: contract?.currency ?? "VND",
    note: contractNote,
  };
  const form = useForm({
    defaultValues,
    validators: { onSubmit: formSchema },
    onSubmit: async ({ value }) => {
      const common = {
        effectiveFrom: formatDateOnly(value.effectiveFrom),
        effectiveTo: formatDateOnly(value.effectiveTo),
        totalAmount: value.totalAmount,
        paymentPlan: value.paymentPlan,
        currency: value.currency.trim().toUpperCase(),
        note: value.note.trim() || undefined,
      };
      if (contract) await onUpdate(contract.id, common);
      else await onCreate({ residenceId: value.residenceId, ...common });
    },
  });

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="flex max-h-[min(760px,calc(100dvh-1rem))] w-full max-w-2xl flex-col overflow-hidden">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle>
            {isEdit ? "Chỉnh sửa hợp đồng" : "Tạo hợp đồng nội trú"}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            {isEdit
              ? "Chỉ bản nháp mới có thể chỉnh sửa. Thông tin sinh viên và chỗ ở được giữ nguyên theo hồ sơ cư trú."
              : "Tạo bản nháp từ một lượt cư trú đang hoạt động để chuẩn bị gửi ký."}
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
          <div className="grid gap-5 px-1 py-4 sm:px-2">
            {!isEdit ? (
              <form.Field name="residenceId">
                {(field) => (
                  <Field>
                    <FieldLabel>Hồ sơ cư trú</FieldLabel>
                    <Select
                      value={field.state.value}
                      disabled={isSubmitting}
                      onValueChange={field.handleChange}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Chọn hồ sơ cư trú" />
                      </SelectTrigger>
                      <SelectContent>
                        {residences.map((residence) => (
                          <SelectItem key={residence.id} value={residence.id}>
                            {residence.studentName} · {residence.studentCode} ·{" "}
                            {residence.roomCode}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {firstError(field.state.meta.errors) ? (
                      <FieldError>
                        {firstError(field.state.meta.errors)}
                      </FieldError>
                    ) : null}
                  </Field>
                )}
              </form.Field>
            ) : null}
            <div className="grid items-start gap-5 sm:grid-cols-2">
              <form.Field name="effectiveFrom">
                {(field) => (
                  <Field>
                    <FieldLabel>Hiệu lực từ</FieldLabel>
                    <DatePicker
                      value={field.state.value}
                      disabled={isSubmitting}
                      onBlur={field.handleBlur}
                      onChange={(value) => field.handleChange(value)}
                      onValidationChange={(message) => {
                        field.setMeta((meta) => ({
                          ...meta,
                          errors: message ? [message] : [],
                        }));
                      }}
                      aria-invalid={Boolean(
                        firstError(field.state.meta.errors),
                      )}
                    />
                    {firstError(field.state.meta.errors) ? (
                      <FieldError>
                        {firstError(field.state.meta.errors)}
                      </FieldError>
                    ) : null}
                  </Field>
                )}
              </form.Field>
              <form.Field name="effectiveTo">
                {(field) => (
                  <Field>
                    <FieldLabel>Hiệu lực đến</FieldLabel>
                    <DatePicker
                      value={field.state.value}
                      disabled={isSubmitting}
                      minDate={form.getFieldValue("effectiveFrom")}
                      onBlur={field.handleBlur}
                      onChange={(value) => field.handleChange(value)}
                      onValidationChange={(message) => {
                        field.setMeta((meta) => ({
                          ...meta,
                          errors: message ? [message] : [],
                        }));
                      }}
                      aria-invalid={Boolean(
                        firstError(field.state.meta.errors),
                      )}
                    />
                    {firstError(field.state.meta.errors) ? (
                      <FieldError>
                        {firstError(field.state.meta.errors)}
                      </FieldError>
                    ) : null}
                  </Field>
                )}
              </form.Field>
            </div>
            <div className="grid gap-5 sm:grid-cols-2">
              <form.Field name="totalAmount">
                {(field) => (
                  <Field>
                    <FieldLabel>Số tiền hợp đồng (tùy chọn)</FieldLabel>
                    <Input
                      type="number"
                      min={0}
                      step={1000}
                      value={field.state.value ?? ""}
                      placeholder="Tự lấy theo mức phí nếu để trống"
                      disabled={isSubmitting}
                      onChange={(event) => {
                        const value = event.target.value;
                        field.handleChange(
                          value === "" ? undefined : Number(value),
                        );
                      }}
                    />
                    {firstError(field.state.meta.errors) ? (
                      <FieldError>
                        {firstError(field.state.meta.errors)}
                      </FieldError>
                    ) : null}
                  </Field>
                )}
              </form.Field>
              <form.Field name="currency">
                {(field) => (
                  <Field>
                    <FieldLabel>Loại tiền</FieldLabel>
                    <Input
                      value={field.state.value}
                      maxLength={3}
                      disabled={isSubmitting}
                      onChange={(event) =>
                        field.handleChange(event.target.value)
                      }
                    />
                    {firstError(field.state.meta.errors) ? (
                      <FieldError>
                        {firstError(field.state.meta.errors)}
                      </FieldError>
                    ) : null}
                  </Field>
                )}
              </form.Field>
            </div>
            <form.Field name="paymentPlan">
              {(field) => (
                <Field>
                  <FieldLabel>Phương thức thanh toán</FieldLabel>
                  <Select
                    value={field.state.value}
                    disabled={isSubmitting}
                    onValueChange={(value) =>
                      field.handleChange(value as "one_time" | "monthly")
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="one_time">Một lần</SelectItem>
                      <SelectItem value="monthly">Hàng tháng</SelectItem>
                    </SelectContent>
                  </Select>
                </Field>
              )}
            </form.Field>
            <form.Field name="note">
              {(field) => (
                <Field>
                  <FieldLabel>Ghi chú</FieldLabel>
                  <Textarea
                    value={field.state.value}
                    rows={4}
                    maxLength={2000}
                    disabled={isSubmitting}
                    onChange={(event) => field.handleChange(event.target.value)}
                  />
                  {firstError(field.state.meta.errors) ? (
                    <FieldError>
                      {firstError(field.state.meta.errors)}
                    </FieldError>
                  ) : null}
                </Field>
              )}
            </form.Field>
          </div>
          <ResponsiveDialogFooter className="border-t px-1 pt-4 sm:px-2">
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
                      : "Tạo bản nháp"}
                </Button>
              )}
            </form.Subscribe>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
