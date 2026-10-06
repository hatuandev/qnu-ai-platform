import { useForm } from "@tanstack/react-form";
import {
  BookOpen,
  Building2,
  Calendar,
  Lock,
  Mail,
  MapPin,
  Pencil,
  Phone,
  Sparkles,
  User,
  UserCheck,
  UserPlus,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  useCreateStudent,
  useStudentQuery,
  useUpdateStudent,
} from "@/features/students/api";
import type {
  Student,
  StudentDetail,
  StudentFormValues,
} from "@/features/students/types";
import { getFormErrorMessage } from "@/lib/form-errors";

const schema = z.object({
  studentCode: z.string().trim().min(1, "Mã sinh viên là bắt buộc.").max(50),
  fullName: z.string().trim().min(1, "Họ tên là bắt buộc.").max(255),
  dateOfBirth: z.union([z.date(), z.undefined()]),
  gender: z.enum(["male", "female", "other"]),
  email: z.string().trim().email("Email không hợp lệ.").or(z.literal("")),
  phoneNumber: z.string().max(50),
  faculty: z.string().max(255),
  className: z.string().max(100),
  major: z.string().max(255),
  permanentAddress: z.string(),
  contactAddress: z.string(),
});

function firstError(errors: unknown[]) {
  return getFormErrorMessage(errors[0]);
}

function parseDate(value?: string | null) {
  if (!value) return undefined;
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? undefined : date;
}

function mapErrors(error: ApiError) {
  return Object.fromEntries(
    Object.entries(error.fieldErrors ?? {}).map(([key, messages]) => [
      key.charAt(0).toLowerCase() + key.slice(1),
      messages.join(" "),
    ]),
  );
}

export function StudentFormDialog({
  open,
  onOpenChange,
  student,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  student?: (Student | StudentDetail) | null;
}) {
  const isEdit = Boolean(student);

  // If student is provided (and might be a summary object from list), fetch full student detail
  const detailQuery = useStudentQuery(student?.id ?? "");
  const fullStudent: (Student | StudentDetail) | null =
    (detailQuery.data as StudentDetail | undefined) ?? student ?? null;

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="flex max-h-[min(820px,calc(100vh-2rem))] w-full max-w-2xl flex-col overflow-hidden p-0 gap-0 shadow-lg">
        <ResponsiveDialogHeader className="border-b bg-muted/20 px-6 py-4 pr-12">
          <ResponsiveDialogTitle className="flex items-center gap-2 text-base sm:text-lg font-bold">
            {isEdit ? (
              <>
                <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
                  <Pencil className="size-4" />
                </div>
                <span>Chỉnh sửa sinh viên</span>
              </>
            ) : (
              <>
                <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
                  <UserPlus className="size-4" />
                </div>
                <span>Thêm sinh viên</span>
              </>
            )}
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs text-muted-foreground mt-1">
            {isEdit
              ? "Cập nhật thông tin hồ sơ sinh viên."
              : "Tạo hồ sơ sinh viên mới trong hệ thống ký túc xá."}
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        {isEdit &&
        !("permanentAddress" in (student ?? {})) &&
        detailQuery.isLoading ? (
          <div className="p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Skeleton className="h-10 w-full rounded" />
              <Skeleton className="h-10 w-full rounded" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Skeleton className="h-10 w-full rounded" />
              <Skeleton className="h-10 w-full rounded" />
            </div>
            <Skeleton className="h-20 w-full rounded" />
          </div>
        ) : (
          <StudentFormInner
            key={`${fullStudent?.id ?? "new"}-${detailQuery.dataUpdatedAt}`}
            student={fullStudent}
            onOpenChange={onOpenChange}
          />
        )}
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

function StudentFormInner({
  student,
  onOpenChange,
}: {
  student?: (Student | StudentDetail) | null;
  onOpenChange: (open: boolean) => void;
}) {
  const isEdit = Boolean(student);
  const create = useCreateStudent();
  const update = useUpdateStudent();
  const [serverError, setServerError] = useState<string | null>(null);
  const [serverFields, setServerFields] = useState<Record<string, string>>({});

  const form = useForm({
    defaultValues: {
      studentCode: student?.studentCode ?? "",
      fullName: student?.fullName ?? "",
      dateOfBirth: parseDate(student?.dateOfBirth),
      gender: student?.gender ?? "other",
      email: student?.email ?? "",
      phoneNumber: student?.phoneNumber ?? "",
      faculty: student?.faculty ?? "",
      className: student?.className ?? "",
      major: student && "major" in student ? (student.major ?? "") : "",
      permanentAddress:
        student && "permanentAddress" in student
          ? (student.permanentAddress ?? "")
          : "",
      contactAddress:
        student && "contactAddress" in student
          ? (student.contactAddress ?? "")
          : "",
    } satisfies StudentFormValues,
    validators: { onSubmit: schema },
    onSubmit: async ({ value }) => {
      setServerError(null);
      setServerFields({});
      const input = {
        fullName: value.fullName.trim(),
        dateOfBirth: value.dateOfBirth?.toISOString().slice(0, 10),
        gender: value.gender,
        email: value.email.trim() || undefined,
        phoneNumber: value.phoneNumber.trim() || undefined,
        faculty: value.faculty.trim() || undefined,
        className: value.className.trim() || undefined,
        major: value.major.trim() || undefined,
        permanentAddress: value.permanentAddress.trim() || undefined,
        contactAddress: value.contactAddress.trim() || undefined,
      };

      try {
        if (student) {
          await update.mutateAsync({ id: student.id, input });
          toast.success("Cập nhật thông tin sinh viên thành công.");
        } else {
          await create.mutateAsync({
            studentCode: value.studentCode.trim(),
            ...input,
          });
          toast.success("Tạo mới sinh viên thành công.");
        }
        onOpenChange(false);
      } catch (error) {
        if (error instanceof ApiError) {
          setServerError(error.message);
          setServerFields(mapErrors(error));
        } else {
          setServerError(
            "Không thể lưu sinh viên. Vui lòng kiểm tra lại dữ liệu.",
          );
        }
      }
    },
  });

  const pending = create.isPending || update.isPending;

  return (
    <form
      className="min-h-0 flex-1 overflow-y-auto"
      onSubmit={(event) => {
        event.preventDefault();
        event.stopPropagation();
        void form.handleSubmit();
      }}
    >
      <div className="space-y-4 px-6 py-5">
        {serverError ? (
          <div
            role="alert"
            className="rounded-lg border border-destructive/30 bg-destructive/5 px-3.5 py-2.5 text-xs text-destructive flex items-center gap-2"
          >
            <span className="font-semibold">Lỗi:</span>
            <span>{serverError}</span>
          </div>
        ) : null}

        {/* Clean 2-Column Form Grid */}
        <div className="grid gap-4 sm:grid-cols-2 text-xs">
          <form.Field name="studentCode">
            {(field) => {
              const error =
                firstError(field.state.meta.errors) ?? serverFields.studentCode;
              return (
                <Field>
                  <FieldLabel
                    htmlFor="student-code"
                    className="flex items-center gap-1.5 text-xs font-medium"
                  >
                    <User className="size-3.5 text-muted-foreground" />
                    <span>Mã sinh viên</span>
                    {isEdit ? (
                      <Lock className="size-3 text-muted-foreground ml-auto" />
                    ) : (
                      <span className="text-destructive">*</span>
                    )}
                  </FieldLabel>
                  <Input
                    id="student-code"
                    value={field.state.value}
                    disabled={isEdit || pending}
                    className={
                      isEdit ? "bg-muted/40 font-mono font-medium" : "font-mono"
                    }
                    placeholder="VD: 4551050156"
                    onBlur={field.handleBlur}
                    onChange={(e) => field.handleChange(e.target.value)}
                    aria-invalid={Boolean(error)}
                  />
                  {error ? <FieldError>{error}</FieldError> : null}
                </Field>
              );
            }}
          </form.Field>

          <form.Field name="fullName">
            {(field) => {
              const error =
                firstError(field.state.meta.errors) ?? serverFields.fullName;
              return (
                <Field>
                  <FieldLabel
                    htmlFor="student-name"
                    className="flex items-center gap-1.5 text-xs font-medium"
                  >
                    <UserCheck className="size-3.5 text-muted-foreground" />
                    <span>Họ và tên</span>
                    <span className="text-destructive">*</span>
                  </FieldLabel>
                  <Input
                    id="student-name"
                    value={field.state.value}
                    disabled={pending}
                    placeholder="VD: Nguyễn Xuân Quỳnh Như"
                    onBlur={field.handleBlur}
                    onChange={(e) => field.handleChange(e.target.value)}
                    aria-invalid={Boolean(error)}
                  />
                  {error ? <FieldError>{error}</FieldError> : null}
                </Field>
              );
            }}
          </form.Field>

          <form.Field name="gender">
            {(field) => (
              <Field>
                <FieldLabel className="flex items-center gap-1.5 text-xs font-medium">
                  <User className="size-3.5 text-muted-foreground" />
                  <span>Giới tính</span>
                </FieldLabel>
                <Select
                  value={field.state.value}
                  onValueChange={(value) =>
                    field.handleChange(value as StudentFormValues["gender"])
                  }
                >
                  <SelectTrigger className="text-xs">
                    <SelectValue placeholder="Chọn giới tính" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="male">Nam</SelectItem>
                    <SelectItem value="female">Nữ</SelectItem>
                    <SelectItem value="other">Khác</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
            )}
          </form.Field>

          <form.Field name="dateOfBirth">
            {(field) => (
              <Field>
                <FieldLabel className="flex items-center gap-1.5 text-xs font-medium">
                  <Calendar className="size-3.5 text-muted-foreground" />
                  <span>Ngày sinh</span>
                </FieldLabel>
                <DatePicker
                  value={field.state.value}
                  disabled={pending}
                  onChange={field.handleChange}
                />
              </Field>
            )}
          </form.Field>

          <form.Field name="faculty">
            {(field) => {
              const error =
                firstError(field.state.meta.errors) ?? serverFields.faculty;
              return (
                <Field>
                  <FieldLabel
                    htmlFor="student-faculty"
                    className="flex items-center gap-1.5 text-xs font-medium"
                  >
                    <Building2 className="size-3.5 text-muted-foreground" />
                    <span>Khoa</span>
                  </FieldLabel>
                  <Input
                    id="student-faculty"
                    value={field.state.value}
                    disabled={pending}
                    placeholder="VD: Khoa Công nghệ thông tin"
                    onBlur={field.handleBlur}
                    onChange={(e) => field.handleChange(e.target.value)}
                    aria-invalid={Boolean(error)}
                  />
                  {error ? <FieldError>{error}</FieldError> : null}
                </Field>
              );
            }}
          </form.Field>

          <form.Field name="className">
            {(field) => {
              const error =
                firstError(field.state.meta.errors) ?? serverFields.className;
              return (
                <Field>
                  <FieldLabel
                    htmlFor="student-class"
                    className="flex items-center gap-1.5 text-xs font-medium"
                  >
                    <BookOpen className="size-3.5 text-muted-foreground" />
                    <span>Lớp</span>
                  </FieldLabel>
                  <Input
                    id="student-class"
                    value={field.state.value}
                    disabled={pending}
                    placeholder="VD: CNTT45C"
                    onBlur={field.handleBlur}
                    onChange={(e) => field.handleChange(e.target.value)}
                    aria-invalid={Boolean(error)}
                  />
                  {error ? <FieldError>{error}</FieldError> : null}
                </Field>
              );
            }}
          </form.Field>

          <form.Field name="major">
            {(field) => {
              const error =
                firstError(field.state.meta.errors) ?? serverFields.major;
              return (
                <Field>
                  <FieldLabel
                    htmlFor="student-major"
                    className="flex items-center gap-1.5 text-xs font-medium"
                  >
                    <Sparkles className="size-3.5 text-muted-foreground" />
                    <span>Ngành</span>
                  </FieldLabel>
                  <Input
                    id="student-major"
                    value={field.state.value}
                    disabled={pending}
                    placeholder="VD: Công nghệ phần mềm"
                    onBlur={field.handleBlur}
                    onChange={(e) => field.handleChange(e.target.value)}
                    aria-invalid={Boolean(error)}
                  />
                  {error ? <FieldError>{error}</FieldError> : null}
                </Field>
              );
            }}
          </form.Field>

          <form.Field name="phoneNumber">
            {(field) => {
              const error =
                firstError(field.state.meta.errors) ?? serverFields.phoneNumber;
              return (
                <Field>
                  <FieldLabel
                    htmlFor="student-phone"
                    className="flex items-center gap-1.5 text-xs font-medium"
                  >
                    <Phone className="size-3.5 text-muted-foreground" />
                    <span>Số điện thoại</span>
                  </FieldLabel>
                  <Input
                    id="student-phone"
                    value={field.state.value}
                    disabled={pending}
                    placeholder="VD: 0395503445"
                    onBlur={field.handleBlur}
                    onChange={(e) => field.handleChange(e.target.value)}
                    aria-invalid={Boolean(error)}
                  />
                  {error ? <FieldError>{error}</FieldError> : null}
                </Field>
              );
            }}
          </form.Field>

          <div className="sm:col-span-2">
            <form.Field name="email">
              {(field) => {
                const error =
                  firstError(field.state.meta.errors) ?? serverFields.email;
                return (
                  <Field>
                    <FieldLabel
                      htmlFor="student-email"
                      className="flex items-center gap-1.5 text-xs font-medium"
                    >
                      <Mail className="size-3.5 text-muted-foreground" />
                      <span>Email trường (QNU)</span>
                    </FieldLabel>
                    <Input
                      id="student-email"
                      type="email"
                      value={field.state.value}
                      disabled={pending}
                      placeholder="VD: masv@st.qnu.edu.vn"
                      onBlur={field.handleBlur}
                      onChange={(e) => field.handleChange(e.target.value)}
                      aria-invalid={Boolean(error)}
                    />
                    {error ? <FieldError>{error}</FieldError> : null}
                  </Field>
                );
              }}
            </form.Field>
          </div>

          <div className="sm:col-span-2">
            <form.Field name="permanentAddress">
              {(field) => (
                <Field>
                  <FieldLabel className="flex items-center gap-1.5 text-xs font-medium">
                    <MapPin className="size-3.5 text-muted-foreground" />
                    <span>Địa chỉ thường trú</span>
                  </FieldLabel>
                  <Textarea
                    rows={2}
                    className="text-xs"
                    value={field.state.value}
                    placeholder="VD: Thôn An Quang Đông, xã Đề Gi, Gia Lai"
                    disabled={pending}
                    onChange={(e) => field.handleChange(e.target.value)}
                  />
                </Field>
              )}
            </form.Field>
          </div>

          <div className="sm:col-span-2">
            <form.Field name="contactAddress">
              {(field) => (
                <Field>
                  <FieldLabel className="flex items-center gap-1.5 text-xs font-medium">
                    <MapPin className="size-3.5 text-muted-foreground" />
                    <span>Địa chỉ liên hệ</span>
                  </FieldLabel>
                  <Textarea
                    rows={2}
                    className="text-xs"
                    value={field.state.value}
                    placeholder="Nhập địa chỉ tạm trú hoặc liên hệ nếu khác địa chỉ thường trú"
                    disabled={pending}
                    onChange={(e) => field.handleChange(e.target.value)}
                  />
                </Field>
              )}
            </form.Field>
          </div>
        </div>
      </div>

      <ResponsiveDialogFooter className="border-t bg-card px-4 py-3 sm:px-6 sm:py-3.5">
        <div className="grid grid-cols-2 gap-3 w-full sm:flex sm:w-auto sm:items-center sm:justify-end sm:gap-2.5">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="w-full sm:w-auto h-9 text-xs"
            disabled={pending}
            onClick={() => onOpenChange(false)}
          >
            Hủy
          </Button>
          <form.Subscribe
            selector={(state) => [state.canSubmit, state.isSubmitting]}
          >
            {([canSubmit, submitting]) => (
              <Button
                type="submit"
                size="sm"
                className="w-full sm:w-auto h-9 text-xs font-semibold"
                disabled={!canSubmit || submitting || pending}
              >
                {pending
                  ? "Đang lưu..."
                  : isEdit
                    ? "Lưu thay đổi"
                    : "Tạo sinh viên"}
              </Button>
            )}
          </form.Subscribe>
        </div>
      </ResponsiveDialogFooter>
    </form>
  );
}
