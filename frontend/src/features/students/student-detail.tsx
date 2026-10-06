import { Link } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowLeft,
  ArrowUpRight,
  BookOpen,
  Building2,
  Calendar,
  Check,
  Clock,
  Copy,
  FileCheck2,
  GraduationCap,
  Home,
  Mail,
  MapPin,
  Pencil,
  Phone,
  ShieldCheck,
  Sparkles,
  User,
  UserCheck,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useStudentQuery } from "@/features/students/api";
import { StudentFormDialog } from "@/features/students/student-form-dialog";
import type { StudentStatus } from "@/features/students/types";
import { formatDateTimeValue, formatDateValue } from "@/lib/date-utils";
import { cn } from "@/lib/utils";
import { useRbac } from "@/rbac/context";

const statusLabels: Record<StudentStatus, string> = {
  studying: "Đang học",
  paused: "Tạm dừng",
  graduated: "Đã tốt nghiệp",
  unknown: "Chưa xác định",
  inactive: "Ngừng hoạt động",
};

export function StudentDetail({ studentId }: { studentId: string }) {
  const { can } = useRbac();
  const query = useStudentQuery(studentId);
  const [editOpen, setEditOpen] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);

  if (query.isLoading) {
    return <StudentDetailSkeleton />;
  }

  if (query.isError || !query.data) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center rounded-xl border border-dashed p-8 text-center bg-card">
        <div className="flex size-14 items-center justify-center rounded-full bg-destructive/10 text-destructive mb-4">
          <AlertCircle className="size-7" />
        </div>
        <h3 className="text-lg font-semibold text-foreground">
          Không thể tải thông tin sinh viên
        </h3>
        <p className="mt-1.5 max-w-md text-sm text-muted-foreground">
          Đã xảy ra lỗi khi tải hồ sơ sinh viên hoặc sinh viên không tồn tại.
        </p>
        <div className="mt-6 flex items-center gap-3">
          <Button variant="outline" onClick={() => window.history.back()}>
            <ArrowLeft className="mr-2 size-4" /> Quay lại
          </Button>
          <Button onClick={() => void query.refetch()}>Thử lại</Button>
        </div>
      </div>
    );
  }

  const student = query.data;

  const initials = (student.fullName ?? "SV")
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const handleCopyCode = () => {
    if (!student.studentCode) return;
    void navigator.clipboard.writeText(student.studentCode);
    setCopiedCode(true);
    toast.success("Đã sao chép mã sinh viên.");
    setTimeout(() => setCopiedCode(false), 2000);
  };

  return (
    <div className="w-full space-y-5 pb-20 sm:pb-10">
      {/* Breadcrumb Navigation Header */}
      <div className="flex items-center justify-between gap-4 border-b pb-3.5">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <button
            type="button"
            onClick={() => window.history.back()}
            className="inline-flex items-center gap-1 hover:text-foreground transition-colors font-medium"
          >
            <ArrowLeft className="size-3.5" />
            <span>Danh sách sinh viên</span>
          </button>
          <span>/</span>
          <span className="truncate font-semibold text-foreground">
            {student.fullName}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {can("ktx.students.update") ? (
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5 h-8 text-xs font-medium"
              onClick={() => setEditOpen(true)}
            >
              <Pencil className="size-3.5" />
              <span>Chỉnh sửa</span>
            </Button>
          ) : null}
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5 h-8 text-xs font-medium"
            onClick={() => window.history.back()}
          >
            <ArrowLeft className="size-3.5" />
            <span>Quay lại</span>
          </Button>
        </div>
      </div>

      {/* Main 2-Column Balanced Layout */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 items-start">
        {/* LEFT COLUMN: Student Profile, KTX Stats & System Info (4 cols) */}
        <div className="lg:col-span-4 space-y-5">
          <Card className="shadow-2xs overflow-hidden">
            {/* Profile Hero Header */}
            <div className="p-5 text-center flex flex-col items-center bg-muted/15 border-b">
              <Avatar className="size-16 border-2 border-primary/20 bg-primary/10 text-primary mb-3 shadow-xs">
                <AvatarFallback className="font-bold text-lg">
                  {initials}
                </AvatarFallback>
              </Avatar>
              <h2 className="text-base font-bold text-foreground">
                {student.fullName}
              </h2>
              <div className="flex items-center gap-1.5 mt-1.5">
                <span className="font-mono font-medium text-xs bg-background border px-2 py-0.5 rounded text-foreground">
                  MSSV: {student.studentCode}
                </span>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        onClick={handleCopyCode}
                        className="inline-flex size-6 items-center justify-center rounded border bg-background text-muted-foreground hover:text-foreground transition-colors"
                        aria-label="Sao chép mã sinh viên"
                      >
                        {copiedCode ? (
                          <Check className="size-3.5 text-emerald-600" />
                        ) : (
                          <Copy className="size-3.5" />
                        )}
                      </button>
                    </TooltipTrigger>
                    <TooltipContent>Sao chép MSSV</TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>

              <div className="mt-2.5">
                <StudentStatusBadge status={student.status} />
              </div>
            </div>

            <CardContent className="p-5 space-y-4 text-xs">
              {/* Section 1: KTX Stats (Stacked vertical list) */}
              <div className="space-y-2.5">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <Home className="size-3.5 text-primary" />
                  <span>Hoạt động Ký túc xá</span>
                </p>

                <div className="space-y-2">
                  <div className="flex items-center justify-between p-2.5 rounded-lg border bg-muted/20">
                    <div className="flex items-center gap-2">
                      <div className="flex size-7 items-center justify-center rounded bg-primary/10 text-primary">
                        <FileCheck2 className="size-3.5" />
                      </div>
                      <div>
                        <p className="text-xs font-medium text-foreground">
                          Hồ sơ đăng ký
                        </p>
                        <p className="text-[11px] text-muted-foreground font-semibold">
                          {student.applicationCount} đơn đã nộp
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      asChild
                      className="h-7 px-2 text-xs text-primary"
                    >
                      <Link
                        to="/applications"
                        search={{
                          q: student.studentCode,
                          page: 1,
                          pageSize: 10,
                        }}
                      >
                        <span>Xem đơn</span>
                        <ArrowUpRight className="size-3 ml-0.5" />
                      </Link>
                    </Button>
                  </div>

                  <div className="flex items-center justify-between p-2.5 rounded-lg border bg-muted/20">
                    <div className="flex items-center gap-2">
                      <div className="flex size-7 items-center justify-center rounded bg-emerald-500/10 text-emerald-600">
                        <Home className="size-3.5" />
                      </div>
                      <div>
                        <p className="text-xs font-medium text-foreground">
                          Lần lưu trú KTX
                        </p>
                        <p className="text-[11px] text-muted-foreground font-semibold">
                          {student.residenceCount} lần lưu trú
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      asChild
                      className="h-7 px-2 text-xs text-emerald-600"
                    >
                      <Link
                        to="/residence-contracts"
                        search={{
                          q: student.studentCode,
                          page: 1,
                          pageSize: 10,
                        }}
                      >
                        <span>Hợp đồng</span>
                        <ArrowUpRight className="size-3 ml-0.5" />
                      </Link>
                    </Button>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Section 2: System Metadata */}
              <div className="space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <Clock className="size-3.5 text-primary" />
                  <span>Thời gian hệ thống</span>
                </p>

                <div className="grid grid-cols-2 gap-3 pt-0.5">
                  <div>
                    <p className="text-[11px] text-muted-foreground font-medium">
                      Ngày tạo hồ sơ
                    </p>
                    <p className="text-xs font-semibold text-foreground mt-0.5">
                      {student.created
                        ? formatDateTimeValue(student.created)
                        : "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-[11px] text-muted-foreground font-medium">
                      Cập nhật lần cuối
                    </p>
                    <p className="text-xs font-semibold text-foreground mt-0.5">
                      {student.lastModified
                        ? formatDateTimeValue(student.lastModified)
                        : "—"}
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* RIGHT COLUMN: Academic, Personal & Contact Information (8 cols) */}
        <div className="lg:col-span-8 space-y-5">
          <Card className="shadow-2xs overflow-hidden">
            <CardHeader className="border-b bg-muted/20 px-5 py-4">
              <CardTitle className="flex items-center gap-2 text-sm sm:text-base font-semibold">
                <GraduationCap className="size-4.5 text-primary" />
                <span>Thông tin Đào tạo & Cá nhân</span>
              </CardTitle>
            </CardHeader>

            <CardContent className="p-5 sm:p-6 space-y-5">
              {/* Academic Information */}
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-1.5">
                  <BookOpen className="size-3.5 text-primary" />
                  <span>Thông tin học tập</span>
                </h3>
                <div className="grid gap-4 sm:grid-cols-2 text-xs sm:text-sm">
                  <InfoItem
                    icon={
                      <Building2 className="size-4 text-muted-foreground" />
                    }
                    label="Khoa / Đơn vị"
                    value={student.faculty}
                  />
                  <InfoItem
                    icon={<BookOpen className="size-4 text-muted-foreground" />}
                    label="Lớp sinh hoạt"
                    value={student.className}
                  />
                  <InfoItem
                    icon={<Sparkles className="size-4 text-muted-foreground" />}
                    label="Ngành đào tạo"
                    value={student.major}
                  />
                  <InfoItem
                    icon={
                      <ShieldCheck className="size-4 text-muted-foreground" />
                    }
                    label="Trạng thái đào tạo"
                    value={<StudentStatusBadge status={student.status} />}
                  />
                </div>
              </div>

              <Separator />

              {/* Personal & Contact Information */}
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-1.5">
                  <User className="size-3.5 text-primary" />
                  <span>Thông tin cá nhân & Liên hệ</span>
                </h3>
                <div className="grid gap-4 sm:grid-cols-2 text-xs sm:text-sm">
                  <InfoItem
                    icon={
                      <UserCheck className="size-4 text-muted-foreground" />
                    }
                    label="Giới tính"
                    value={
                      student.gender === "male"
                        ? "Nam"
                        : student.gender === "female"
                          ? "Nữ"
                          : "Khác"
                    }
                  />
                  <InfoItem
                    icon={<Calendar className="size-4 text-muted-foreground" />}
                    label="Ngày sinh"
                    value={formatDateValue(student.dateOfBirth)}
                  />
                  <InfoItem
                    icon={<Phone className="size-4 text-muted-foreground" />}
                    label="Số điện thoại"
                    value={
                      student.phoneNumber ? (
                        <a
                          href={`tel:${student.phoneNumber}`}
                          className="text-primary hover:underline font-medium inline-block"
                        >
                          {student.phoneNumber}
                        </a>
                      ) : null
                    }
                  />
                  <InfoItem
                    icon={<Mail className="size-4 text-muted-foreground" />}
                    label="Email trường (QNU)"
                    value={(() => {
                      const emailToDisplay =
                        student.schoolEmail ||
                        (student.studentCode
                          ? `${student.studentCode.toLowerCase()}@st.qnu.edu.vn`
                          : student.email);
                      return emailToDisplay ? (
                        <a
                          href={`mailto:${emailToDisplay}`}
                          className="text-primary hover:underline font-medium break-all"
                          title={emailToDisplay}
                        >
                          {emailToDisplay}
                        </a>
                      ) : null;
                    })()}
                  />
                  <div className="sm:col-span-2">
                    <InfoItem
                      icon={<MapPin className="size-4 text-muted-foreground" />}
                      label="Hộ khẩu thường trú"
                      value={student.permanentAddress}
                    />
                  </div>
                  {student.contactAddress ? (
                    <div className="sm:col-span-2">
                      <InfoItem
                        icon={
                          <MapPin className="size-4 text-muted-foreground" />
                        }
                        label="Địa chỉ liên hệ"
                        value={student.contactAddress}
                      />
                    </div>
                  ) : null}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Edit Form Dialog */}
      <StudentFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        student={student}
      />
    </div>
  );
}

// Clean Information Item with Icon
function InfoItem({
  icon,
  label,
  value,
}: {
  icon?: React.ReactNode;
  label: string;
  value?: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-2.5">
      {icon ? <div className="mt-0.5 shrink-0">{icon}</div> : null}
      <div className="min-w-0 flex-1">
        <p className="text-xs text-muted-foreground font-medium">{label}</p>
        <div className="text-xs sm:text-sm font-medium text-foreground mt-0.5 break-words">
          {value || (
            <span className="text-muted-foreground/60 font-normal">—</span>
          )}
        </div>
      </div>
    </div>
  );
}

// Student Status Badge
function StudentStatusBadge({ status }: { status: StudentStatus }) {
  const label = statusLabels[status] || status;

  return (
    <Badge
      variant="outline"
      className={cn(
        "gap-1.5 px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide shrink-0",
        status === "studying" &&
          "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30",
        status === "graduated" &&
          "bg-blue-500/15 text-blue-700 dark:text-blue-400 border-blue-500/30",
        status === "paused" &&
          "bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30",
        status === "inactive" &&
          "bg-destructive/15 text-destructive border-destructive/30",
        status === "unknown" && "bg-muted text-muted-foreground",
      )}
    >
      <span
        className={cn(
          "size-1.5 rounded-full",
          status === "studying" && "bg-emerald-500",
          status === "graduated" && "bg-blue-500",
          status === "paused" && "bg-amber-500",
          status === "inactive" && "bg-destructive",
          status === "unknown" && "bg-muted-foreground/60",
        )}
      />
      {label}
    </Badge>
  );
}

// Skeleton Loader
function StudentDetailSkeleton() {
  return (
    <div className="space-y-5 w-full">
      <div className="flex justify-between items-center border-b pb-4">
        <Skeleton className="h-8 w-44" />
        <Skeleton className="h-9 w-32" />
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="lg:col-span-4">
          <Skeleton className="h-[420px] w-full rounded-xl" />
        </div>
        <div className="lg:col-span-8">
          <Skeleton className="h-[420px] w-full rounded-xl" />
        </div>
      </div>
    </div>
  );
}
