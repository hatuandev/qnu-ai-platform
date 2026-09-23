import { useForm } from "@tanstack/react-form";
import { Loader2, Plus, Save } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { ApiError } from "@/app/api/client";
import { Combobox } from "@/components/admin/combobox";
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
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  useCreateDifficultArea,
  useDifficultAreaProvincesQuery,
  useUpdateDifficultArea,
} from "@/features/difficult-areas/api";
import type { DifficultAreaItem } from "@/features/difficult-areas/types";
import { getFormErrorMessage } from "@/lib/form-errors";

export const difficultAreaFormSchema = z
  .object({
    externalCode: z.string().trim().max(100, "Mã tối đa 100 ký tự."),
    name: z
      .string()
      .trim()
      .min(1, "Tên xã / phường / thị trấn là bắt buộc.")
      .max(200, "Tên tối đa 200 ký tự."),
    divisionType: z.string().trim().min(1, "Loại đơn vị là bắt buộc."),
    provinceName: z
      .string()
      .trim()
      .min(1, "Tỉnh / Thành phố là bắt buộc.")
      .max(200, "Tỉnh/TP tối đa 200 ký tự."),
    provinceCode: z.string().trim().max(50, "Mã tỉnh tối đa 50 ký tự."),
    isWholeArea: z.boolean(),
    specificVillages: z
      .string()
      .trim()
      .max(2000, "Danh sách thôn/ấp tối đa 2000 ký tự."),
  })
  .refine(
    (data) => {
      if (!data.isWholeArea) {
        return Boolean(
          data.specificVillages && data.specificVillages.trim().length > 0,
        );
      }
      return true;
    },
    {
      message:
        "Vui lòng nhập danh sách thôn/ấp khi chỉ áp dụng một phần địa bàn",
      path: ["specificVillages"],
    },
  );

type DifficultAreaFormValues = z.infer<typeof difficultAreaFormSchema>;

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

const VIETNAM_PROVINCES = [
  "An Giang",
  "Bà Rịa - Vũng Tàu",
  "Bắc Giang",
  "Bắc Kạn",
  "Bạc Liêu",
  "Bắc Ninh",
  "Bến Tre",
  "Bình Định",
  "Bình Dương",
  "Bình Phước",
  "Bình Thuận",
  "Cà Mau",
  "Cần Thơ",
  "Cao Bằng",
  "Đà Nẵng",
  "Đắk Lắk",
  "Đắk Nông",
  "Điện Biên",
  "Đồng Nai",
  "Đồng Tháp",
  "Gia Lai",
  "Hà Giang",
  "Hà Nam",
  "Hà Nội",
  "Hà Tĩnh",
  "Hải Dương",
  "Hải Phòng",
  "Hậu Giang",
  "Hòa Bình",
  "Hưng Yên",
  "Khánh Hòa",
  "Kiên Giang",
  "Kon Tum",
  "Lai Châu",
  "Lâm Đồng",
  "Lạng Sơn",
  "Lào Cai",
  "Long An",
  "Nam Định",
  "Nghệ An",
  "Ninh Bình",
  "Ninh Thuận",
  "Phú Thọ",
  "Phú Yên",
  "Quảng Bình",
  "Quảng Nam",
  "Quảng Ngãi",
  "Quảng Ninh",
  "Quảng Trị",
  "Sóc Trăng",
  "Sơn La",
  "Tây Ninh",
  "Thái Bình",
  "Thái Nguyên",
  "Thanh Hóa",
  "Thừa Thiên Huế",
  "Tiền Giang",
  "TP Hồ Chí Minh",
  "Trà Vinh",
  "Tuyên Quang",
  "Vĩnh Long",
  "Vĩnh Phúc",
  "Yên Bái",
];

export function DifficultAreaFormDialog({
  open,
  onOpenChange,
  areaToEdit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  areaToEdit?: DifficultAreaItem | null;
}) {
  const isEdit = Boolean(areaToEdit);
  const provincesQuery = useDifficultAreaProvincesQuery();

  const provinceOptions = useMemo(() => {
    const combined = Array.from(
      new Set([...VIETNAM_PROVINCES, ...(provincesQuery.data ?? [])]),
    );
    combined.sort((a, b) => a.localeCompare(b, "vi"));
    return combined.map((p) => ({ value: p, label: p }));
  }, [provincesQuery.data]);

  const createMutation = useCreateDifficultArea();
  const updateMutation = useUpdateDifficultArea();

  const [serverError, setServerError] = useState<string | null>(null);
  const [serverFieldErrors, setServerFieldErrors] = useState<
    Record<string, string>
  >({});

  const form = useForm({
    defaultValues: {
      externalCode: areaToEdit?.externalCode ?? "",
      name: areaToEdit?.name ?? "",
      divisionType: areaToEdit?.divisionType ?? "Xã",
      provinceName: areaToEdit?.provinceName ?? "",
      provinceCode: areaToEdit?.provinceCode ?? "",
      isWholeArea: areaToEdit?.isWholeArea ?? true,
      specificVillages: areaToEdit?.specificVillages ?? "",
    } satisfies DifficultAreaFormValues,
    validators: { onSubmit: difficultAreaFormSchema },
    onSubmit: async ({ value }) => {
      setServerError(null);
      setServerFieldErrors({});
      const input = {
        externalCode: value.externalCode.trim() || undefined,
        name: value.name.trim(),
        divisionType: value.divisionType.trim() || "Xã",
        provinceName: value.provinceName.trim(),
        provinceCode: value.provinceCode.trim() || undefined,
        isWholeArea: value.isWholeArea,
        specificVillages: value.isWholeArea
          ? undefined
          : value.specificVillages.trim() || undefined,
      };

      try {
        if (areaToEdit) {
          await updateMutation.mutateAsync({
            id: areaToEdit.id,
            payload: input,
          });
          toast.success("Đã cập nhật địa bàn ưu tiên thành công.");
        } else {
          await createMutation.mutateAsync(input);
          toast.success("Đã thêm mới địa bàn ưu tiên thành công.");
        }
        onOpenChange(false);
      } catch (error) {
        if (error instanceof ApiError) {
          setServerError(error.message);
          setServerFieldErrors(getServerFieldErrors(error));
        } else {
          setServerError(
            error instanceof Error
              ? error.message
              : "Không thể lưu địa bàn ưu tiên. Vui lòng thử lại.",
          );
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
            {isEdit ? "Chỉnh sửa địa bàn ưu tiên" : "Thêm mới địa bàn ưu tiên"}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            {isEdit
              ? "Cập nhật thông tin xã, phường, thôn/ấp đặc biệt khó khăn."
              : "Khai báo địa bàn xã/phường thuộc diện đặc biệt khó khăn theo Quyết định 60."}
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
          <div className="grid gap-4 px-4 py-4 lg:px-1">
            {serverError ? (
              <div
                role="alert"
                className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
              >
                {serverError}
              </div>
            ) : null}

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {/* Tên Xã/Phường */}
              <form.Field name="name">
                {(field) => {
                  const error =
                    fieldError(field.state.meta.errors) ??
                    serverFieldErrors.name;
                  return (
                    <Field>
                      <FieldLabel htmlFor="area-name">
                        Tên Xã / Phường / Thị trấn{" "}
                        <span className="text-destructive font-bold">*</span>
                      </FieldLabel>
                      <Input
                        id="area-name"
                        className="text-xs"
                        placeholder="Ví dụ: Xã An Vinh"
                        value={field.state.value}
                        disabled={isSubmitting}
                        onBlur={field.handleBlur}
                        onChange={(e) => field.handleChange(e.target.value)}
                        aria-invalid={Boolean(error)}
                      />
                      {error ? <FieldError>{error}</FieldError> : null}
                    </Field>
                  );
                }}
              </form.Field>

              {/* Loại đơn vị */}
              <form.Field name="divisionType">
                {(field) => (
                  <Field>
                    <FieldLabel htmlFor="area-division">
                      Loại đơn vị{" "}
                      <span className="text-destructive font-bold">*</span>
                    </FieldLabel>
                    <Select
                      value={field.state.value}
                      disabled={isSubmitting}
                      onValueChange={(val) => field.handleChange(val)}
                    >
                      <SelectTrigger id="area-division" className="text-xs">
                        <SelectValue placeholder="Chọn loại đơn vị" />
                      </SelectTrigger>
                      <SelectContent className="text-xs">
                        <SelectItem value="Xã">Xã</SelectItem>
                        <SelectItem value="Phường">Phường</SelectItem>
                        <SelectItem value="Thị trấn">Thị trấn</SelectItem>
                      </SelectContent>
                    </Select>
                  </Field>
                )}
              </form.Field>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {/* Tỉnh/Thành phố */}
              <form.Field name="provinceName">
                {(field) => {
                  const error =
                    fieldError(field.state.meta.errors) ??
                    serverFieldErrors.provincename;
                  return (
                    <Field>
                      <FieldLabel htmlFor="area-province">
                        Tỉnh / Thành phố{" "}
                        <span className="text-destructive font-bold">*</span>
                      </FieldLabel>
                      <Combobox
                        options={provinceOptions}
                        value={field.state.value}
                        onValueChange={(val) => field.handleChange(val ?? "")}
                        placeholder="Chọn Tỉnh / Thành phố"
                        searchPlaceholder="Tìm kiếm Tỉnh / Thành phố..."
                        emptyMessage="Không tìm thấy Tỉnh / Thành phố."
                        disabled={isSubmitting}
                        clearable
                        className="text-xs h-9"
                      />
                      {error ? <FieldError>{error}</FieldError> : null}
                    </Field>
                  );
                }}
              </form.Field>

              {/* Mã địa bàn */}
              <form.Field name="externalCode">
                {(field) => (
                  <Field>
                    <FieldLabel htmlFor="area-code">
                      Mã địa bàn (Tùy chọn)
                    </FieldLabel>
                    <Input
                      id="area-code"
                      className="text-xs font-mono"
                      placeholder="Tự sinh (QD60_xxxx)"
                      value={field.state.value}
                      disabled={isSubmitting}
                      onBlur={field.handleBlur}
                      onChange={(e) => field.handleChange(e.target.value)}
                    />
                    <FieldDescription className="text-[11px]">
                      Mã định danh trong hệ thống QĐ 60.
                    </FieldDescription>
                  </Field>
                )}
              </form.Field>
            </div>

            {/* Phạm vi: Toàn xã hay một phần */}
            <form.Field name="isWholeArea">
              {(field) => (
                <Field className="rounded-lg border p-3 bg-muted/20">
                  <div className="flex items-start gap-3">
                    <Checkbox
                      id="area-whole"
                      checked={field.state.value}
                      disabled={isSubmitting}
                      onCheckedChange={(checked) =>
                        field.handleChange(Boolean(checked))
                      }
                    />
                    <div className="space-y-1 leading-none">
                      <label
                        htmlFor="area-whole"
                        className="text-xs font-medium cursor-pointer"
                      >
                        Áp dụng toàn bộ địa bàn xã / phường
                      </label>
                      <p className="text-[11px] text-muted-foreground">
                        Bỏ chọn nếu chỉ có một số thôn, xóm, ấp cụ thể thuộc
                        diện đặc biệt khó khăn.
                      </p>
                    </div>
                  </div>
                </Field>
              )}
            </form.Field>

            {/* Danh sách thôn/ấp nếu !isWholeArea */}
            <form.Subscribe
              selector={(state) => state.values.isWholeArea}
              children={(isWhole) =>
                !isWhole ? (
                  <form.Field name="specificVillages">
                    {(field) => {
                      const error =
                        fieldError(field.state.meta.errors) ??
                        serverFieldErrors.specificvillages;
                      return (
                        <Field>
                          <FieldLabel htmlFor="area-villages">
                            Danh sách thôn / xóm / ấp áp dụng{" "}
                            <span className="text-destructive font-bold">
                              *
                            </span>
                          </FieldLabel>
                          <Textarea
                            id="area-villages"
                            className="text-xs min-h-[70px]"
                            placeholder="Ví dụ: Thôn 1, Thôn 2, Làng O2, Làng K2..."
                            value={field.state.value}
                            disabled={isSubmitting}
                            onBlur={field.handleBlur}
                            onChange={(e) => field.handleChange(e.target.value)}
                            aria-invalid={Boolean(error)}
                          />
                          <FieldDescription className="text-[11px]">
                            Nhập tên các thôn/bản theo danh sách được công nhận
                            trong Quyết định.
                          </FieldDescription>
                          {error ? <FieldError>{error}</FieldError> : null}
                        </Field>
                      );
                    }}
                  </form.Field>
                ) : null
              }
            />
          </div>

          <ResponsiveDialogFooter className="border-t px-4 py-3 sm:px-1">
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
            <Button
              type="submit"
              size="sm"
              className="text-xs"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-1.5 size-3.5 animate-spin" />
                  Đang lưu...
                </>
              ) : isEdit ? (
                <>
                  <Save className="mr-1.5 size-3.5" />
                  Lưu thay đổi
                </>
              ) : (
                <>
                  <Plus className="mr-1.5 size-3.5" />
                  Thêm địa bàn
                </>
              )}
            </Button>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
