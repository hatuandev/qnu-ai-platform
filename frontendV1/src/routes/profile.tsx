import { createFileRoute } from "@tanstack/react-router";
import {
  CheckCircle2,
  Laptop,
  Moon,
  ShieldCheck,
  Sparkles,
  Sun,
  UserCheck,
} from "lucide-react";
import { useAuth } from "@/app/auth";
import { useTheme } from "@/app/theme-provider";
import { PageHeader } from "@/components/admin/page-header";
import { StatusBadge } from "@/components/admin/status-badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { useStudentRegistrationCatalogQuery } from "@/features/student/api";
import { cn } from "@/lib/utils";
import { isStudentAccount } from "@/rbac/backend-role-map";
import { useRbac } from "@/rbac/context";

export const Route = createFileRoute("/profile")({ component: ProfilePage });

function ProfilePage() {
  const { user } = useAuth();
  const { roleKey, roleName } = useRbac();
  const { theme, setTheme } = useTheme();

  const isStudent = roleKey === "student" || isStudentAccount(user?.userType);

  // If student, query profile catalog to get rich synced data (FullName, Class, Faculty, Major, Phone)
  const catalogQuery = useStudentRegistrationCatalogQuery(undefined, isStudent);
  const student = catalogQuery.data?.student;

  const rawName = user?.name?.trim() ?? "";
  const isNameDigits = /^\d+$/.test(rawName);

  const studentCode =
    student?.studentCode || (isNameDigits ? rawName : undefined);
  const displayName =
    student?.fullName ||
    (!isNameDigits && rawName ? rawName : undefined) ||
    (isStudent ? "Sinh viên" : "Cán bộ KTX");

  const displayEmail =
    student?.schoolEmail ||
    student?.email ||
    user?.email ||
    (studentCode
      ? `${studentCode.toLowerCase()}@st.qnu.edu.vn`
      : "ktx@qnu.edu.vn");

  const defaultJobTitle = isStudent
    ? "Sinh viên nội trú"
    : user?.userType === "admin"
      ? "Quản trị viên hệ thống"
      : "Cán bộ quản lý KTX";

  const initials =
    displayName
      .split(/\s+/)
      .filter(Boolean)
      .map((part) => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase() || (isStudent ? "SV" : "CB");

  return (
    <div className="mx-auto max-w-4xl space-y-4 sm:space-y-6">
      <PageHeader
        eyebrow={isStudent ? "Sinh viên / Tài khoản" : "Hệ thống / Tài khoản"}
        title="Thông tin cá nhân & Tài khoản"
        description="Xem thông tin tài khoản được đồng bộ trực tiếp từ hệ thống QNU và tùy chỉnh giao diện làm việc."
      />

      {/* Header Profile Card */}
      <Card className="border-border/60 bg-gradient-to-r from-card via-card to-primary/5">
        <CardContent className="flex flex-col items-start gap-4 p-4 sm:flex-row sm:items-center sm:gap-5 sm:p-5">
          <Avatar className="size-13 sm:size-14 border border-primary/30 bg-primary/10 shadow-sm shrink-0">
            <AvatarFallback className="text-base sm:text-lg font-bold tracking-wider text-primary">
              {initials}
            </AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1 space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg sm:text-xl font-bold tracking-tight text-foreground">
                {displayName}
              </h2>
              {studentCode ? (
                <Badge
                  variant="secondary"
                  className="font-mono text-xs font-semibold px-2 py-0.5"
                >
                  MSSV: {studentCode}
                </Badge>
              ) : null}
              <Badge
                variant="outline"
                className="border-primary/30 bg-primary/10 font-medium text-primary text-xs px-2 py-0.5"
              >
                {roleName}
              </Badge>
              <StatusBadge status="active" />
            </div>
            <p className="flex flex-wrap items-center gap-1.5 text-xs sm:text-sm text-muted-foreground">
              <span>{displayEmail}</span>
              <span>·</span>
              <span className="inline-flex items-center gap-1 font-medium text-emerald-600 dark:text-emerald-400">
                <ShieldCheck className="size-3.5 sm:size-4" /> Đã xác thực QNU
                SSO
              </span>
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Identity & Educational Information */}
      <Card>
        <CardHeader className="gap-1">
          <CardTitle className="flex items-center gap-2 text-base">
            <UserCheck className="size-4 text-primary" />{" "}
            {isStudent ? "Thông tin sinh viên" : "Thông tin định danh cán bộ"}
          </CardTitle>
          <CardDescription>
            Dữ liệu định danh được đồng bộ trực tiếp qua Cổng đăng nhập tập
            trung QNU SSO của Nhà trường.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1 rounded-lg border bg-muted/30 p-3.5">
            <p className="type-supporting font-medium text-muted-foreground">
              {isStudent ? "Họ và tên sinh viên" : "Họ và tên"}
            </p>
            <p className="text-sm font-semibold text-foreground sm:text-base">
              {displayName}
            </p>
          </div>

          {studentCode ? (
            <div className="space-y-1 rounded-lg border bg-muted/30 p-3.5">
              <p className="type-supporting font-medium text-muted-foreground">
                Mã số sinh viên (MSSV)
              </p>
              <p className="font-mono text-sm font-semibold text-foreground sm:text-base">
                {studentCode}
              </p>
            </div>
          ) : null}

          <div className="space-y-1 rounded-lg border bg-muted/30 p-3.5">
            <div className="flex items-center justify-between">
              <p className="type-supporting font-medium text-muted-foreground">
                Địa chỉ email liên hệ
              </p>
              <Badge variant="success" className="h-5 gap-1 py-0 text-xs">
                <CheckCircle2 className="size-3" /> Đã xác minh
              </Badge>
            </div>
            <p className="text-sm font-semibold text-foreground sm:text-base">
              {displayEmail}
            </p>
          </div>

          {isStudent && (student?.faculty || student?.className) ? (
            <div className="space-y-1 rounded-lg border bg-muted/30 p-3.5">
              <p className="type-supporting font-medium text-muted-foreground">
                Khoa / Lớp hành chính
              </p>
              <p className="text-sm font-semibold text-foreground sm:text-base">
                {[student?.faculty, student?.className]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            </div>
          ) : null}

          {isStudent && student?.major ? (
            <div className="space-y-1 rounded-lg border bg-muted/30 p-3.5">
              <p className="type-supporting font-medium text-muted-foreground">
                Chuyên ngành đào tạo
              </p>
              <p className="text-sm font-semibold text-foreground sm:text-base">
                {student.major}
              </p>
            </div>
          ) : null}

          {isStudent && student?.phoneNumber ? (
            <div className="space-y-1 rounded-lg border bg-muted/30 p-3.5">
              <p className="type-supporting font-medium text-muted-foreground">
                Số điện thoại liên hệ
              </p>
              <p className="font-mono text-sm font-semibold text-foreground sm:text-base">
                {student.phoneNumber}
              </p>
            </div>
          ) : null}

          <div className="space-y-1 rounded-lg border bg-muted/30 p-3.5">
            <p className="type-supporting font-medium text-muted-foreground">
              {isStudent ? "Đối tượng người dùng" : "Chức vụ / Vị trí"}
            </p>
            <p className="text-sm font-semibold text-foreground sm:text-base">
              {defaultJobTitle}
            </p>
          </div>

          <div className="space-y-1 rounded-lg border bg-muted/30 p-3.5">
            <p className="type-supporting font-medium text-muted-foreground">
              Cơ chế xác thực
            </p>
            <p className="flex items-center gap-1.5 text-sm font-semibold text-primary sm:text-base">
              <ShieldCheck className="size-4" /> Single Sign-On (QNU SSO)
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Theme Preferences (Live Reactive Change - No save button needed) */}
      <Card>
        <CardHeader className="gap-1">
          <CardTitle className="flex items-center gap-2 text-base">
            <Sparkles className="size-4 text-primary" /> Tùy chọn giao diện
          </CardTitle>
          <CardDescription>
            Lựa chọn chế độ hiển thị phù hợp với thiết bị và môi trường làm việc
            của bạn (tự động áp dụng ngay).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <RadioGroup
            value={theme}
            onValueChange={(value) =>
              setTheme(value as "light" | "dark" | "system")
            }
            className="grid gap-3 sm:grid-cols-3"
          >
            <label
              htmlFor="profile-theme-system"
              className={cn(
                "flex cursor-pointer select-none flex-col gap-2 rounded-lg border p-4 transition-all hover:bg-muted/50",
                theme === "system"
                  ? "border-primary bg-primary/5 ring-2 ring-primary/20"
                  : "border-border",
              )}
            >
              <div className="flex items-center justify-between">
                <div className="rounded-md bg-muted p-2 text-muted-foreground">
                  <Laptop className="size-4" />
                </div>
                <RadioGroupItem id="profile-theme-system" value="system" />
              </div>
              <div>
                <span className="block text-sm font-semibold">
                  Theo hệ thống
                </span>
                <span className="type-supporting mt-0.5 block text-muted-foreground">
                  Tự động theo cài đặt thiết bị
                </span>
              </div>
            </label>

            <label
              htmlFor="profile-theme-light"
              className={cn(
                "flex cursor-pointer select-none flex-col gap-2 rounded-lg border p-4 transition-all hover:bg-muted/50",
                theme === "light"
                  ? "border-primary bg-primary/5 ring-2 ring-primary/20"
                  : "border-border",
              )}
            >
              <div className="flex items-center justify-between">
                <div className="rounded-md bg-amber-100 p-2 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300">
                  <Sun className="size-4" />
                </div>
                <RadioGroupItem id="profile-theme-light" value="light" />
              </div>
              <div>
                <span className="block text-sm font-semibold">
                  Giao diện Sáng
                </span>
                <span className="type-supporting mt-0.5 block text-muted-foreground">
                  Màu sắc rõ ràng, tươi sáng
                </span>
              </div>
            </label>

            <label
              htmlFor="profile-theme-dark"
              className={cn(
                "flex cursor-pointer select-none flex-col gap-2 rounded-lg border p-4 transition-all hover:bg-muted/50",
                theme === "dark"
                  ? "border-primary bg-primary/5 ring-2 ring-primary/20"
                  : "border-border",
              )}
            >
              <div className="flex items-center justify-between">
                <div className="rounded-md bg-indigo-100 p-2 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">
                  <Moon className="size-4" />
                </div>
                <RadioGroupItem id="profile-theme-dark" value="dark" />
              </div>
              <div>
                <span className="block text-sm font-semibold">
                  Giao diện Tối
                </span>
                <span className="type-supporting mt-0.5 block text-muted-foreground">
                  Nền tối dịu mắt, tiết kiệm pin
                </span>
              </div>
            </label>
          </RadioGroup>
        </CardContent>
      </Card>
    </div>
  );
}
