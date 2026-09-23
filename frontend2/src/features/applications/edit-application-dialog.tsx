import { useForm } from "@tanstack/react-form";
import {
  AlertCircle,
  Building2,
  GraduationCap,
  Loader2,
  Mail,
  Pencil,
  Phone,
  RotateCcw,
  Search,
  User,
  UserCheck,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { ApiError } from "@/app/api/client";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
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
import {
  useApplicationQuery,
  useUpdateApplication,
} from "@/features/applications/api";
import type {
  ApplicationDetail,
  DormitoryApplication,
} from "@/features/applications/types";
import { usePriorityObjectsQuery } from "@/features/priority-objects/api";
import { useRoomTypesQuery } from "@/features/room-types/api";
import { useLookupStudentQuery } from "@/features/students/api";
import type { StudentLookupDto } from "@/features/students/types";
import { getFormErrorMessage } from "@/lib/form-errors";

const schema = z.object({
  studentId: z.string().min(1, "Vui lòng chọn sinh viên hợp lệ."),
  requestedRoomTypeId: z.string(),
  priorityObjectId: z.string(),
  reason: z.string().max(1000, "Lý do không được quá 1000 ký tự."),
});

type FormValues = {
  studentId: string;
  requestedRoomTypeId: string;
  priorityObjectId: string;
  reason: string;
};

function firstError(errors: unknown[]) {
  return getFormErrorMessage(errors[0]);
}

export function EditApplicationDialog({
  open,
  onOpenChange,
  application,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  application: DormitoryApplication | ApplicationDetail | null;
}) {
  const updateMutation = useUpdateApplication();

  // Full detail query in case partial item passed
  const detailQuery = useApplicationQuery(application?.id ?? "");
  const currentItem = detailQuery.data ?? application;

  // Search state for student lookup via UIS API
  const [isChangingStudent, setIsChangingStudent] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [submittedCode, setSubmittedCode] = useState("");
  const [newStudent, setNewStudent] = useState<StudentLookupDto | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingValues, setPendingValues] = useState<FormValues | null>(null);

  const lookupQuery = useLookupStudentQuery(submittedCode, {
    enabled: Boolean(submittedCode.trim()),
  });

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

  const form = useForm({
    defaultValues: {
      studentId: currentItem?.studentId ?? "",
      requestedRoomTypeId:
        (currentItem as ApplicationDetail)?.requestedRoomTypeId ?? "none",
      priorityObjectId:
        (currentItem as ApplicationDetail)?.priorityObjectId ?? "none",
      reason: (currentItem as ApplicationDetail)?.reason ?? "",
    } satisfies FormValues,
    validators: {
      onSubmit: schema,
    },
    onSubmit: ({ value }) => {
      setPendingValues(value);
      setConfirmOpen(true);
    },
  });

  // Re-sync form when currentItem updates or dialog opens
  useEffect(() => {
    if (currentItem && open) {
      form.setFieldValue("studentId", currentItem.studentId);
      form.setFieldValue(
        "requestedRoomTypeId",
        (currentItem as ApplicationDetail)?.requestedRoomTypeId ?? "none",
      );
      form.setFieldValue(
        "priorityObjectId",
        (currentItem as ApplicationDetail)?.priorityObjectId ?? "none",
      );
      form.setFieldValue(
        "reason",
        (currentItem as ApplicationDetail)?.reason ?? "",
      );
      setIsChangingStudent(false);
      setNewStudent(null);
      setSearchInput("");
      setSubmittedCode("");
    }
  }, [currentItem, open, form]);

  // Update selected student when lookup query succeeds
  useEffect(() => {
    if (lookupQuery.data) {
      setNewStudent(lookupQuery.data);
      form.setFieldValue("studentId", lookupQuery.data.id);
    }
  }, [lookupQuery.data, form]);

  const handleResetDialog = () => {
    setIsChangingStudent(false);
    setSearchInput("");
    setSubmittedCode("");
    setNewStudent(null);
    setPendingValues(null);
  };

  const handleSearchStudent = () => {
    const term = searchInput.trim();
    if (!term) {
      toast.error("Vui lòng nhập mã sinh viên để tra cứu trên UIS.");
      return;
    }
    setNewStudent(null);
    setSubmittedCode(term);
  };

  const handleConfirmSave = async () => {
    if (!currentItem || !pendingValues) return;
    try {
      await updateMutation.mutateAsync({
        id: currentItem.id,
        input: {
          studentId: pendingValues.studentId,
          requestedRoomTypeId:
            pendingValues.requestedRoomTypeId &&
            pendingValues.requestedRoomTypeId !== "none"
              ? pendingValues.requestedRoomTypeId
              : null,
          priorityObjectId:
            pendingValues.priorityObjectId &&
            pendingValues.priorityObjectId !== "none"
              ? pendingValues.priorityObjectId
              : null,
          reason: pendingValues.reason?.trim() || null,
        },
      });

      toast.success("Cập nhật hồ sơ đăng ký thành công.");
      setConfirmOpen(false);
      handleResetDialog();
      onOpenChange(false);
    } catch (error) {
      toast.error(
        error instanceof ApiError
          ? error.message
          : error instanceof Error
            ? error.message
            : "Không thể cập nhật hồ sơ đăng ký.",
      );
    }
  };

  const hasStudentChanged =
    Boolean(newStudent) && newStudent?.id !== currentItem?.studentId;

  return (
    <>
      <ResponsiveDialog
        open={open}
        onOpenChange={(val) => {
          if (!val) handleResetDialog();
          onOpenChange(val);
        }}
      >
        <ResponsiveDialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <ResponsiveDialogHeader>
            <div className="flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Pencil className="size-5" />
              </div>
              <div>
                <ResponsiveDialogTitle>
                  Chỉnh sửa hồ sơ đăng ký
                </ResponsiveDialogTitle>
                <ResponsiveDialogDescription>
                  Cập nhật thông tin sinh viên, nguyện vọng và diện ưu tiên của
                  hồ sơ {currentItem?.applicationCode}.
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
            {/* 1. THÔNG TIN SINH VIÊN */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <FieldLabel className="text-xs font-semibold">
                  1. Thông tin sinh viên đứng tên hồ sơ
                </FieldLabel>
                {!isChangingStudent ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs px-2.5 text-primary border-primary/30 hover:bg-primary/5"
                    onClick={() => {
                      setIsChangingStudent(true);
                      setSearchInput("");
                    }}
                  >
                    <RotateCcw className="size-3 mr-1" />
                    Đổi mã sinh viên
                  </Button>
                ) : (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs px-2 text-muted-foreground hover:text-foreground"
                    onClick={() => {
                      setIsChangingStudent(false);
                      setNewStudent(null);
                      setSearchInput("");
                      setSubmittedCode("");
                      if (currentItem) {
                        form.setFieldValue("studentId", currentItem.studentId);
                      }
                    }}
                  >
                    <X className="size-3 mr-1" />
                    Hủy đổi sinh viên
                  </Button>
                )}
              </div>

              {/* Nếu đang ở chế độ đổi sinh viên: Hiện ô tra cứu UIS */}
              {isChangingStudent && (
                <div className="space-y-2 rounded-lg border border-primary/20 bg-primary/5 p-3">
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                      <Input
                        value={searchInput}
                        onChange={(e) => setSearchInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            handleSearchStudent();
                          }
                        }}
                        placeholder="Nhập Mã sinh viên mới (ví dụ: 4851050001)..."
                        className="pl-9 h-9 text-xs bg-background"
                      />
                    </div>
                    <Button
                      type="button"
                      size="sm"
                      onClick={handleSearchStudent}
                      disabled={lookupQuery.isFetching}
                      className="h-9 px-3 text-xs shrink-0"
                    >
                      {lookupQuery.isFetching ? (
                        <Loader2 className="size-4 animate-spin mr-1" />
                      ) : (
                        <Search className="size-4 mr-1" />
                      )}
                      Tra cứu UIS
                    </Button>
                  </div>

                  {lookupQuery.isError && (
                    <div className="rounded-md border border-destructive/30 bg-destructive/10 p-2.5 text-xs text-destructive flex items-center gap-2">
                      <AlertCircle className="size-4 shrink-0" />
                      <span>
                        {lookupQuery.error instanceof Error
                          ? lookupQuery.error.message
                          : "Không tìm thấy thông tin sinh viên trên hệ thống đào tạo."}
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* Thẻ hiển thị sinh viên (Mới nếu có tra cứu, hoặc Hiện tại) */}
              {newStudent ? (
                /* Card Sinh viên MỚI */
                <div className="rounded-lg border-2 border-primary/40 bg-card p-3.5 space-y-2 shadow-xs">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="size-8 rounded-full bg-primary/20 text-primary flex items-center justify-center font-bold text-xs shrink-0">
                        <UserCheck className="size-4" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-bold text-sm text-foreground">
                            {newStudent.fullName}
                          </p>
                          <Badge
                            variant="outline"
                            className="text-[10px] text-primary border-primary"
                          >
                            Sinh viên mới chọn
                          </Badge>
                        </div>
                        <p className="font-mono text-xs text-muted-foreground">
                          {newStudent.studentCode}
                        </p>
                      </div>
                    </div>
                    <Badge
                      variant={
                        newStudent.gender === "male" ? "default" : "secondary"
                      }
                      className="text-xs font-semibold px-2 py-0.5"
                    >
                      {newStudent.gender === "male"
                        ? "Nam"
                        : newStudent.gender === "female"
                          ? "Nữ"
                          : "Khác"}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-muted-foreground pt-1 border-t">
                    <div className="flex items-center gap-1.5 truncate">
                      <GraduationCap className="size-3.5 shrink-0 text-primary" />
                      <span className="truncate">
                        {[newStudent.faculty, newStudent.className]
                          .filter(Boolean)
                          .join(" · ") || "Chưa có khoa/lớp"}
                      </span>
                    </div>
                    {newStudent.major && (
                      <div className="flex items-center gap-1.5 truncate">
                        <Building2 className="size-3.5 shrink-0 text-primary" />
                        <span className="truncate">
                          Ngành: {newStudent.major}
                        </span>
                      </div>
                    )}
                    {newStudent.phoneNumber && (
                      <div className="flex items-center gap-1.5 truncate">
                        <Phone className="size-3.5 shrink-0 text-primary" />
                        <span>{newStudent.phoneNumber}</span>
                      </div>
                    )}
                    {newStudent.schoolEmail && (
                      <div className="flex items-center gap-1.5 truncate">
                        <Mail className="size-3.5 shrink-0 text-primary" />
                        <span className="truncate">
                          {newStudent.schoolEmail}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ) : currentItem ? (
                /* Card Sinh viên HIỆN TẠI */
                <div className="rounded-lg border bg-card p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="size-8 rounded-full bg-muted flex items-center justify-center font-bold text-xs text-muted-foreground shrink-0">
                        <User className="size-4" />
                      </div>
                      <div>
                        <p className="font-semibold text-xs text-foreground">
                          {currentItem.studentName}
                        </p>
                        <p className="font-mono text-[11px] text-muted-foreground">
                          Mã SV: {currentItem.studentCode}
                        </p>
                      </div>
                    </div>
                    <Badge variant="outline" className="text-[11px]">
                      Đang liên kết
                    </Badge>
                  </div>

                  <div className="text-xs text-muted-foreground flex items-center gap-2 pt-1 border-t">
                    <GraduationCap className="size-3.5 shrink-0 text-primary" />
                    <span>
                      {[
                        (currentItem as ApplicationDetail)?.faculty,
                        (currentItem as ApplicationDetail)?.className,
                      ]
                        .filter(Boolean)
                        .join(" · ") ||
                        currentItem.faculty ||
                        "Chưa có khoa/lớp"}
                    </span>
                  </div>
                </div>
              ) : null}
            </div>

            {/* 2. ĐỢT ĐĂNG KÝ (CHỈ ĐỌC) */}
            <div className="space-y-1.5">
              <FieldLabel className="text-xs font-semibold">
                2. Đợt đăng ký KTX
              </FieldLabel>
              <div className="rounded-lg border bg-muted/30 px-3 py-2 text-xs flex items-center justify-between text-muted-foreground">
                <span className="font-medium text-foreground">
                  {currentItem?.registrationPeriodName || "Đợt đăng ký"}
                </span>
                <Badge variant="outline" className="text-[10px]">
                  Cố định theo đợt
                </Badge>
              </div>
            </div>

            {/* 3. NGUYỆN VỌNG LOẠI PHÒNG */}
            <form.Field name="requestedRoomTypeId">
              {(field) => (
                <Field className="space-y-1.5">
                  <FieldLabel className="text-xs font-semibold">
                    3. Nguyện vọng loại phòng
                  </FieldLabel>
                  <Select
                    value={field.state.value}
                    onValueChange={field.handleChange}
                  >
                    <SelectTrigger className="h-9 text-xs">
                      <SelectValue placeholder="Chọn loại phòng nguyện vọng" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">
                        Không chỉ định (Xếp theo sắp xếp của ban quản lý)
                      </SelectItem>
                      {roomTypesQuery.data?.items.map((rt) => (
                        <SelectItem key={rt.id} value={rt.id}>
                          {rt.name} ({rt.capacity} chỗ)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FieldDescription className="text-[11px]">
                    Loại phòng mong muốn của sinh viên khi phân bổ phòng.
                  </FieldDescription>
                </Field>
              )}
            </form.Field>

            {/* 4. ĐỐI TƯỢNG ƯU TIÊN */}
            <form.Field name="priorityObjectId">
              {(field) => (
                <Field className="space-y-1.5">
                  <FieldLabel className="text-xs font-semibold">
                    4. Đối tượng ưu tiên
                  </FieldLabel>
                  <Select
                    value={field.state.value}
                    onValueChange={field.handleChange}
                  >
                    <SelectTrigger className="h-9 text-xs">
                      <SelectValue placeholder="Chọn đối tượng ưu tiên" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">
                        Không thuộc diện ưu tiên (0 điểm)
                      </SelectItem>
                      {priorityObjectsQuery.data?.items.map((po) => (
                        <SelectItem key={po.id} value={po.id}>
                          {po.name} (+{po.score} điểm)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FieldDescription className="text-[11px]">
                    Điểm ưu tiên sẽ được tự động tính toán lại theo đối tượng
                    được chọn.
                  </FieldDescription>
                </Field>
              )}
            </form.Field>

            {/* 5. LÝ DO / GHI CHÚ */}
            <form.Field name="reason">
              {(field) => (
                <Field className="space-y-1.5">
                  <FieldLabel className="text-xs font-semibold">
                    5. Lý do / Ghi chú hồ sơ
                  </FieldLabel>
                  <Textarea
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    placeholder="Nhập lý do hoặc ghi chú của cán bộ quản lý..."
                    className="min-h-[70px] text-xs resize-none"
                    maxLength={1000}
                  />
                  {field.state.meta.errors.length > 0 && (
                    <FieldError>
                      {firstError(field.state.meta.errors)}
                    </FieldError>
                  )}
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
              >
                Hủy
              </Button>
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending && (
                  <Loader2 className="size-4 animate-spin mr-1.5" />
                )}
                Lưu thay đổi
              </Button>
            </ResponsiveDialogFooter>
          </form>
        </ResponsiveDialogContent>
      </ResponsiveDialog>

      {/* CONFIRM DIALOG TRƯỚC KHI LƯU */}
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Xác nhận lưu thay đổi hồ sơ"
        description={
          hasStudentChanged
            ? `CẢNH BÁO QUAN TRỌNG: Bạn đang thay đổi sinh viên của hồ sơ từ "${currentItem?.studentName} (${currentItem?.studentCode})" sang "${newStudent?.fullName} (${newStudent?.studentCode}) - Giới tính: ${newStudent?.gender === "male" ? "Nam" : "Nữ"}". Toàn bộ thông tin học vụ, giới tính và phân bổ phòng sẽ được cập nhật sang sinh viên mới. Bạn có chắc chắn muốn thực hiện?`
            : `Bạn có chắc chắn muốn lưu các thay đổi cho hồ sơ ${currentItem?.applicationCode}?`
        }
        confirmLabel="Xác nhận lưu"
        confirmVariant={hasStudentChanged ? "destructive" : "default"}
        isLoading={updateMutation.isPending}
        onConfirm={() => void handleConfirmSave()}
      />
    </>
  );
}
