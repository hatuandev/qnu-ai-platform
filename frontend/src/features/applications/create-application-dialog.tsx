import { useForm } from "@tanstack/react-form";
import {
  AlertCircle,
  Building2,
  Calendar,
  Globe2,
  GraduationCap,
  Loader2,
  Mail,
  MapPin,
  Phone,
  Plus,
  RotateCcw,
  Search,
  UserCheck,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
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
import { Badge } from "@/components/ui/badge";
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
import { useCreateApplication } from "@/features/applications/api";
import { usePriorityObjectsQuery } from "@/features/priority-objects/api";
import { useRegistrationPeriodsQuery } from "@/features/registration-periods/api";
import { useRoomTypesQuery } from "@/features/room-types/api";
import { useLookupStudentQuery } from "@/features/students/api";
import type { StudentLookupDto } from "@/features/students/types";
import { getFormErrorMessage } from "@/lib/form-errors";

const schema = z.object({
  studentId: z.string().min(1, "Vui lòng tra cứu và chọn sinh viên từ UIS."),
  registrationPeriodId: z.string().min(1, "Vui lòng chọn đợt đăng ký."),
  requestedRoomTypeId: z.string(),
  priorityObjectId: z.string(),
  gender: z.string(),
  initialStatus: z.enum(["submitted", "approved"]),
  reason: z.string().max(1000, "Lý do không được quá 1000 ký tự."),
});

type FormValues = {
  studentId: string;
  registrationPeriodId: string;
  requestedRoomTypeId: string;
  priorityObjectId: string;
  gender: string;
  initialStatus: "submitted" | "approved";
  reason: string;
};

function firstError(errors: unknown[]) {
  return getFormErrorMessage(errors[0]);
}

export function CreateApplicationDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const createMutation = useCreateApplication();

  // Search state for student lookup via UIS API
  const [searchInput, setSearchInput] = useState("");
  const [submittedCode, setSubmittedCode] = useState("");
  const [selectedStudent, setSelectedStudent] =
    useState<StudentLookupDto | null>(null);

  const lookupQuery = useLookupStudentQuery(submittedCode, {
    enabled: Boolean(submittedCode.trim()),
  });

  const periodsQuery = useRegistrationPeriodsQuery({ page: 1, pageSize: 100 });
  const roomTypesQuery = useRoomTypesQuery({
    page: 1,
    pageSize: 100,
    isActive: true,
  });
  const priorityObjectsQuery = usePriorityObjectsQuery({
    page: 1,
    pageSize: 100,
    isActive: true,
  });

  const defaultPeriodId = useMemo(() => {
    const items = periodsQuery.data?.items ?? [];
    const openPeriod = items.find((p) => p.status === "open");
    return openPeriod?.id ?? items[0]?.id ?? "";
  }, [periodsQuery.data]);

  const form = useForm({
    defaultValues: {
      studentId: "",
      registrationPeriodId: defaultPeriodId,
      requestedRoomTypeId: "none",
      priorityObjectId: "none",
      gender: "male",
      initialStatus: "submitted" as "submitted" | "approved",
      reason: "",
    } satisfies FormValues,
    validators: {
      onSubmit: schema,
    },
    onSubmit: async ({ value }) => {
      try {
        await createMutation.mutateAsync({
          studentId: value.studentId,
          registrationPeriodId: value.registrationPeriodId || defaultPeriodId,
          requestedRoomTypeId:
            value.requestedRoomTypeId && value.requestedRoomTypeId !== "none"
              ? value.requestedRoomTypeId
              : undefined,
          priorityObjectId:
            value.priorityObjectId && value.priorityObjectId !== "none"
              ? value.priorityObjectId
              : undefined,
          gender: value.gender || selectedStudent?.gender || "male",
          initialStatus: value.initialStatus,
          reason: value.reason?.trim() || undefined,
        });

        toast.success("Tạo hồ sơ đăng ký KTX thành công.");
        handleResetDialog();
        onOpenChange(false);
      } catch (error) {
        toast.error(
          error instanceof ApiError
            ? error.message
            : error instanceof Error
              ? error.message
              : "Không thể tạo hồ sơ đăng ký.",
        );
      }
    },
  });

  // Automatically update selected student when lookup query succeeds
  useEffect(() => {
    if (lookupQuery.data) {
      setSelectedStudent(lookupQuery.data);
      form.setFieldValue("studentId", lookupQuery.data.id);
      form.setFieldValue("gender", lookupQuery.data.gender || "male");
    }
  }, [lookupQuery.data, form]);

  const handleResetDialog = () => {
    form.reset();
    setSearchInput("");
    setSubmittedCode("");
    setSelectedStudent(null);
  };

  const handleSearchStudent = () => {
    const term = searchInput.trim();
    if (!term) {
      toast.error("Vui lòng nhập mã sinh viên để tra cứu trên UIS.");
      return;
    }
    setSelectedStudent(null);
    form.setFieldValue("studentId", "");
    setSubmittedCode(term);
  };

  const handleClearStudent = () => {
    setSelectedStudent(null);
    form.setFieldValue("studentId", "");
    setSearchInput("");
    setSubmittedCode("");
  };

  return (
    <ResponsiveDialog
      open={open}
      onOpenChange={(val) => {
        if (!val) handleResetDialog();
        onOpenChange(val);
      }}
    >
      <ResponsiveDialogContent className="sm:max-w-xl max-h-[90vh] overflow-y-auto">
        <ResponsiveDialogHeader>
          <div className="flex items-center gap-2">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Plus className="size-5" />
            </div>
            <div>
              <ResponsiveDialogTitle>
                Tạo hồ sơ đăng ký KTX
              </ResponsiveDialogTitle>
              <ResponsiveDialogDescription>
                Nhập mã sinh viên để tra cứu dữ liệu thời gian thực từ UIS và
                khởi tạo hồ sơ nội trú.
              </ResponsiveDialogDescription>
            </div>
          </div>
        </ResponsiveDialogHeader>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            e.stopPropagation();
            void form.handleSubmit();
          }}
          className="space-y-4 py-2"
        >
          {/* 1. Tra cứu Sinh viên theo Mã trên UIS API */}
          <form.Field name="studentId">
            {(field) => (
              <Field>
                <div className="flex items-center justify-between">
                  <FieldLabel>
                    Sinh viên <span className="text-destructive">*</span>
                  </FieldLabel>
                  <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                    <Globe2 className="size-3 text-sky-500" />
                    Dữ liệu UIS QNU
                  </span>
                </div>

                {selectedStudent ? (
                  /* Đã tìm thấy sinh viên từ UIS / DB: Hiển thị Card thông tin chi tiết */
                  <div className="rounded-xl border bg-muted/30 p-3.5 space-y-3 shadow-xs">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2.5">
                        <div className="flex size-10 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                          <UserCheck className="size-5" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-semibold text-sm text-foreground">
                              {selectedStudent.fullName}
                            </span>
                            <Badge
                              variant="secondary"
                              className="font-mono text-xs font-bold"
                            >
                              {selectedStudent.studentCode}
                            </Badge>
                            {selectedStudent.fromUis ? (
                              <Badge
                                variant="outline"
                                className="text-[10px] bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/30"
                              >
                                Đã đồng bộ UIS
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="text-[10px]">
                                KTX DB
                              </Badge>
                            )}
                          </div>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                            <span className="flex items-center gap-1">
                              <GraduationCap className="size-3" />
                              {selectedStudent.className || "Chưa có lớp"}
                            </span>
                            <span>•</span>
                            <span className="flex items-center gap-1">
                              <Building2 className="size-3" />
                              {selectedStudent.faculty || "Chưa có khoa"}
                            </span>
                          </div>
                        </div>
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs text-muted-foreground hover:text-foreground"
                        onClick={handleClearStudent}
                      >
                        <RotateCcw className="size-3 mr-1" />
                        Đổi mã
                      </Button>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-border/60">
                      <div>
                        <span className="text-muted-foreground flex items-center gap-1 mb-0.5">
                          <Mail className="size-3" /> Email trường:
                        </span>
                        <span className="font-medium text-foreground truncate block">
                          {selectedStudent.schoolEmail ||
                            (selectedStudent.studentCode
                              ? `${selectedStudent.studentCode.toLowerCase()}@st.qnu.edu.vn`
                              : selectedStudent.email || "—")}
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground flex items-center gap-1 mb-0.5">
                          <Phone className="size-3" /> SĐT:
                        </span>
                        <span className="font-medium text-foreground">
                          {selectedStudent.phoneNumber || "—"}
                        </span>
                      </div>
                      {selectedStudent.permanentAddress && (
                        <div className="col-span-2">
                          <span className="text-muted-foreground flex items-center gap-1 mb-0.5">
                            <MapPin className="size-3" /> Hộ khẩu:
                          </span>
                          <span className="font-medium text-foreground truncate block">
                            {selectedStudent.permanentAddress}
                          </span>
                        </div>
                      )}
                      {selectedStudent.dateOfBirth && (
                        <div>
                          <span className="text-muted-foreground flex items-center gap-1 mb-0.5">
                            <Calendar className="size-3" /> Ngày sinh:
                          </span>
                          <span className="font-medium text-foreground">
                            {selectedStudent.dateOfBirth}
                          </span>
                        </div>
                      )}
                      <div>
                        <span className="text-muted-foreground mb-0.5 block">
                          Giới tính <span className="text-destructive">*</span>:
                        </span>
                        <Select
                          value={
                            form.getFieldValue("gender") ||
                            selectedStudent.gender ||
                            "male"
                          }
                          onValueChange={(val) => {
                            form.setFieldValue("gender", val);
                            setSelectedStudent((prev) =>
                              prev ? { ...prev, gender: val } : prev,
                            );
                          }}
                        >
                          <SelectTrigger className="h-7 text-xs font-medium bg-background border-border/80">
                            <SelectValue placeholder="Chọn giới tính" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="male">Nam</SelectItem>
                            <SelectItem value="female">Nữ</SelectItem>
                            <SelectItem value="other">Khác</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </div>
                ) : (
                  /* Chưa tìm thấy: Input nhập mã và nút Tra cứu UIS */
                  <div className="space-y-2">
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <Input
                          placeholder="Nhập mã sinh viên (VD: 4551050156, 4451050168)..."
                          value={searchInput}
                          onChange={(e) => setSearchInput(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              handleSearchStudent();
                            }
                          }}
                          className="font-mono"
                        />
                      </div>
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={handleSearchStudent}
                        disabled={lookupQuery.isFetching || !searchInput.trim()}
                      >
                        {lookupQuery.isFetching ? (
                          <Loader2 className="size-4 animate-spin mr-1.5" />
                        ) : (
                          <Search className="size-4 mr-1.5" />
                        )}
                        Tra cứu UIS
                      </Button>
                    </div>

                    {/* Trạng thái tra cứu */}
                    {lookupQuery.isFetching && (
                      <div className="flex items-center gap-2 p-2.5 text-xs text-sky-600 dark:text-sky-400 rounded-lg border border-sky-500/20 bg-sky-500/5">
                        <Loader2 className="size-3.5 animate-spin" />
                        <span>
                          Đang kết nối API UIS để lấy thông tin sinh viên...
                        </span>
                      </div>
                    )}

                    {!lookupQuery.isFetching &&
                      submittedCode &&
                      lookupQuery.isError && (
                        <div className="flex items-center gap-2 p-2.5 text-xs text-destructive rounded-lg border border-destructive/20 bg-destructive/5">
                          <AlertCircle className="size-4 shrink-0" />
                          <span>
                            Không tìm thấy sinh viên có mã &quot;{submittedCode}
                            &quot; trên hệ thống UIS cũng như cơ sở dữ liệu KTX.
                            Vui lòng kiểm tra lại.
                          </span>
                        </div>
                      )}

                    {!submittedCode && !lookupQuery.isFetching && (
                      <FieldDescription>
                        Nhập chính xác mã sinh viên của trường Đại học Quy Nhơn
                        để hệ thống tự động tải thông tin hồ sơ.
                      </FieldDescription>
                    )}
                  </div>
                )}

                {field.state.meta.errors.length ? (
                  <FieldError>{firstError(field.state.meta.errors)}</FieldError>
                ) : null}
              </Field>
            )}
          </form.Field>

          {/* 2. Chọn đợt đăng ký */}
          <form.Field name="registrationPeriodId">
            {(field) => (
              <Field>
                <FieldLabel>
                  Đợt đăng ký <span className="text-destructive">*</span>
                </FieldLabel>
                <Select
                  value={field.state.value || defaultPeriodId}
                  onValueChange={field.handleChange}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Chọn đợt đăng ký" />
                  </SelectTrigger>
                  <SelectContent>
                    {(periodsQuery.data?.items ?? []).map((period) => (
                      <SelectItem key={period.id} value={period.id}>
                        {period.code} · {period.name}{" "}
                        {period.status === "open" ? "(Đang mở)" : ""}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {field.state.meta.errors.length ? (
                  <FieldError>{firstError(field.state.meta.errors)}</FieldError>
                ) : null}
              </Field>
            )}
          </form.Field>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* 3. Loại phòng mong muốn */}
            <form.Field name="requestedRoomTypeId">
              {(field) => (
                <Field>
                  <FieldLabel>Loại phòng mong muốn</FieldLabel>
                  <Select
                    value={field.state.value ?? "none"}
                    onValueChange={field.handleChange}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Chọn loại phòng" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Tất cả loại phòng</SelectItem>
                      {(roomTypesQuery.data?.items ?? []).map((rt) => (
                        <SelectItem key={rt.id} value={rt.id}>
                          {rt.name} ({rt.capacity} người)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
              )}
            </form.Field>

            {/* 4. Đối tượng ưu tiên */}
            <form.Field name="priorityObjectId">
              {(field) => (
                <Field>
                  <FieldLabel>Đối tượng ưu tiên</FieldLabel>
                  <Select
                    value={field.state.value ?? "none"}
                    onValueChange={field.handleChange}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Chọn đối tượng" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Không có ưu tiên</SelectItem>
                      {(priorityObjectsQuery.data?.items ?? []).map((p) => (
                        <SelectItem key={p.id} value={p.id}>
                          {p.name} (+{p.score}đ)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
              )}
            </form.Field>
          </div>

          {/* 5. Trạng thái khởi tạo */}
          <form.Field name="initialStatus">
            {(field) => (
              <Field>
                <FieldLabel>
                  Trạng thái khởi tạo{" "}
                  <span className="text-destructive">*</span>
                </FieldLabel>
                <Select
                  value={field.state.value}
                  onValueChange={(val) =>
                    field.handleChange(val as "submitted" | "approved")
                  }
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Chọn trạng thái" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="submitted">
                      Đã nộp (Chờ cán bộ duyệt hồ sơ)
                    </SelectItem>
                    <SelectItem value="approved">
                      Duyệt ngay (Đủ điều kiện xếp phòng)
                    </SelectItem>
                  </SelectContent>
                </Select>
                <FieldDescription>
                  Chọn &quot;Duyệt ngay&quot; nếu sinh viên đã được xét duyệt
                  trực tiếp tại văn phòng.
                </FieldDescription>
              </Field>
            )}
          </form.Field>

          {/* 6. Lý do / Ghi chú */}
          <form.Field name="reason">
            {(field) => (
              <Field>
                <FieldLabel>Lý do / Ghi chú</FieldLabel>
                <Textarea
                  placeholder="Nhập lý do nộp hồ sơ hoặc ghi chú của cán bộ..."
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  rows={3}
                />
                {field.state.meta.errors.length ? (
                  <FieldError>{firstError(field.state.meta.errors)}</FieldError>
                ) : null}
              </Field>
            )}
          </form.Field>

          <ResponsiveDialogFooter className="pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                handleResetDialog();
                onOpenChange(false);
              }}
              disabled={createMutation.isPending}
            >
              Hủy
            </Button>
            <form.Subscribe
              selector={(state) => [state.canSubmit, state.isSubmitting]}
            >
              {([canSubmit, isSubmitting]) => (
                <Button
                  type="submit"
                  disabled={
                    !selectedStudent ||
                    !canSubmit ||
                    isSubmitting ||
                    createMutation.isPending
                  }
                >
                  {createMutation.isPending || isSubmitting ? (
                    <>
                      <Loader2 className="size-4 animate-spin mr-1.5" />
                      Đang tạo...
                    </>
                  ) : (
                    <>
                      <Plus className="size-4 mr-1.5" />
                      Tạo hồ sơ
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
