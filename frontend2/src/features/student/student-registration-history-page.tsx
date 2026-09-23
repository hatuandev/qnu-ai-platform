import { Link } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowRight,
  Award,
  CheckCircle2,
  Clock3,
  DoorOpen,
  FileCheck2,
  FileEdit,
  FileText,
  History,
  Layers3,
  RotateCcw,
  Sparkles,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useMyApplicationsQuery,
  useWithdrawStudentApplication,
} from "@/features/student/api";
import {
  applicationStatusLabels,
  applicationStatusVariants,
  type MyApplication,
  type StudentApplicationStatus,
} from "@/features/student/types";
import { formatDateValue } from "@/lib/date-utils";
import { cn } from "@/lib/utils";
import { useRbac } from "@/rbac/context";

function formatDate(value?: string | null) {
  return value ? formatDateValue(value) : "Chưa cập nhật";
}

export function StudentRegistrationHistoryPage() {
  const { can } = useRbac();
  const query = useMyApplicationsQuery();
  const withdrawMutation = useWithdrawStudentApplication();
  const [pendingWithdrawal, setPendingWithdrawal] =
    useState<MyApplication | null>(null);

  const applications = query.data ?? [];

  function withdraw(application: MyApplication) {
    setPendingWithdrawal(application);
  }

  function confirmWithdrawal() {
    if (!pendingWithdrawal) return;

    void withdrawMutation
      .mutateAsync(pendingWithdrawal.id)
      .then(() => {
        setPendingWithdrawal(null);
        toast.success("Đã rút hồ sơ đăng ký thành công.");
      })
      .catch((error: unknown) =>
        toast.error(
          error instanceof Error ? error.message : "Không thể rút hồ sơ.",
        ),
      );
  }

  if (query.isLoading) {
    return <RegistrationHistorySkeleton />;
  }

  if (query.isError) {
    return (
      <div className="mx-auto max-w-5xl px-3.5 py-6 sm:px-6">
        <Alert variant="destructive">
          <AlertCircle className="size-4" />
          <div>
            <AlertTitle>Không thể tải lịch sử đăng ký</AlertTitle>
            <AlertDescription>
              {query.error instanceof Error
                ? query.error.message
                : "Vui lòng tải lại trang và thử lại sau."}
            </AlertDescription>
          </div>
        </Alert>
      </div>
    );
  }

  const submittedCount = applications.filter(
    (item) => item.status === "submitted" || item.status === "need_supplement",
  ).length;

  const approvedCount = applications.filter(
    (item) => item.status === "approved" || item.status === "assigned",
  ).length;

  return (
    <div className="mx-auto max-w-5xl space-y-5 px-3.5 pb-16 sm:space-y-6 sm:px-6">
      {/* Page Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="inline-flex items-center gap-1.5 rounded-md bg-primary/10 px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider text-primary">
            <History className="size-3.5" /> Tra cứu hồ sơ
          </div>
          <h1 className="mt-1.5 text-xl font-bold tracking-tight sm:text-2xl md:text-3xl">
            Lịch sử đăng ký phòng
          </h1>
          <p className="mt-1 text-xs text-muted-foreground sm:text-sm">
            Theo dõi tiến độ xét duyệt hồ sơ, kết quả và quản lý lựa chọn phòng
            ở của bạn.
          </p>
        </div>
        <Button asChild className="w-full sm:w-auto shrink-0 shadow-xs">
          <Link to="/student/register">
            <Sparkles className="size-4" /> Đăng ký hồ sơ mới
          </Link>
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-3 sm:grid-cols-3">
        <Card className="shadow-xs">
          <CardContent className="flex items-center gap-4 p-4 sm:p-5">
            <div className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <FileText className="size-5" />
            </div>
            <div className="space-y-0.5">
              <p className="text-xs font-medium text-muted-foreground">
                Tổng hồ sơ đã tạo
              </p>
              <p className="text-xl font-bold text-foreground sm:text-2xl">
                {applications.length}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-xs">
          <CardContent className="flex items-center gap-4 p-4 sm:p-5">
            <div className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
              <Clock3 className="size-5" />
            </div>
            <div className="space-y-0.5">
              <p className="text-xs font-medium text-muted-foreground">
                Đang chờ duyệt / Bổ sung
              </p>
              <p className="text-xl font-bold text-amber-600 dark:text-amber-400 sm:text-2xl">
                {submittedCount}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-xs">
          <CardContent className="flex items-center gap-4 p-4 sm:p-5">
            <div className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="size-5" />
            </div>
            <div className="space-y-0.5">
              <p className="text-xs font-medium text-muted-foreground">
                Đã duyệt / Đã xếp phòng
              </p>
              <p className="text-xl font-bold text-emerald-600 dark:text-emerald-400 sm:text-2xl">
                {approvedCount}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Applications List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold sm:text-base text-foreground">
            Danh sách hồ sơ ({applications.length})
          </h2>
        </div>

        {applications.length > 0 ? (
          <div className="space-y-4">
            {applications.map((application) => (
              <ApplicationHistoryCard
                key={application.id}
                application={application}
                onWithdraw={withdraw}
                canWithdraw={can("ktx.applications.withdraw")}
                isWithdrawing={
                  withdrawMutation.isPending &&
                  withdrawMutation.variables === application.id
                }
              />
            ))}
          </div>
        ) : (
          <Card className="border-dashed shadow-xs">
            <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
              <div className="flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
                <History className="size-6" />
              </div>
              <div className="space-y-1">
                <p className="text-base font-semibold sm:text-lg">
                  Bạn chưa có hồ sơ đăng ký nào
                </p>
                <p className="max-w-md text-xs text-muted-foreground sm:text-sm">
                  Hãy kiểm tra các đợt đăng ký ký túc xá đang mở để nộp hồ sơ
                  nguyện vọng chỗ ở.
                </p>
              </div>
              <Button asChild className="mt-2">
                <Link to="/student/register">
                  <Sparkles className="size-4" /> Đăng ký phòng ngay
                </Link>
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Withdrawal Confirmation Dialog */}
      <ConfirmDialog
        open={Boolean(pendingWithdrawal)}
        onOpenChange={(open) => {
          if (!open && !withdrawMutation.isPending) setPendingWithdrawal(null);
        }}
        title="Rút hồ sơ đăng ký?"
        description={
          pendingWithdrawal
            ? `Bạn có chắc chắn muốn rút hồ sơ ${pendingWithdrawal.applicationCode}? Sau khi rút, hồ sơ sẽ chuyển sang trạng thái Đã rút.`
            : ""
        }
        confirmLabel="Xác nhận rút hồ sơ"
        isLoading={withdrawMutation.isPending}
        onConfirm={confirmWithdrawal}
      />
    </div>
  );
}

function ApplicationHistoryCard({
  application,
  onWithdraw,
  isWithdrawing,
  canWithdraw,
}: {
  application: MyApplication;
  onWithdraw: (application: MyApplication) => void;
  isWithdrawing: boolean;
  canWithdraw: boolean;
}) {
  const canWithdrawStatus =
    application.status === "draft" ||
    application.status === "submitted" ||
    application.status === "need_supplement";

  const isApprovedOrAssigned =
    application.status === "approved" || application.status === "assigned";

  return (
    <Card className="shadow-xs overflow-hidden transition-all hover:shadow-sm">
      <CardHeader className="p-4 sm:p-5 sm:pb-3 border-b bg-muted/20">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle className="text-base font-bold sm:text-lg">
                {application.registrationPeriodName}
              </CardTitle>
              <Badge
                variant={applicationStatusVariants[application.status]}
                className="text-xs"
              >
                {applicationStatusLabels[application.status]}
              </Badge>
            </div>
            <CardDescription className="text-xs sm:text-sm">
              Mã hồ sơ:{" "}
              <span className="font-mono font-semibold text-foreground">
                {application.applicationCode}
              </span>
            </CardDescription>
          </div>
          <div className="text-xs text-muted-foreground">
            Ngày nộp:{" "}
            <span className="font-medium text-foreground">
              {formatDate(application.submittedAt ?? application.created)}
            </span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-4 sm:p-5 space-y-4">
        {/* Progress Step Indicator */}
        <ApplicationProgressTracker status={application.status} />

        {/* Details Grid */}
        <div className="grid gap-2.5 rounded-lg border bg-muted/20 p-3.5 text-xs sm:text-sm sm:grid-cols-2">
          <div className="space-y-1">
            <span className="text-muted-foreground flex items-center gap-1.5">
              <Layers3 className="size-3.5 text-primary" /> Nguyện vọng loại
              phòng:
            </span>
            <p className="font-semibold text-foreground">
              {application.requestedRoomTypeName ?? "Chưa chọn loại phòng"}
            </p>
          </div>

          <div className="space-y-1">
            <span className="text-muted-foreground flex items-center gap-1.5">
              <Award className="size-3.5 text-primary" /> Diện ưu tiên:
            </span>
            <p className="font-semibold text-foreground">
              {application.priorityObjectName ?? "Không thuộc diện ưu tiên"}
            </p>
          </div>

          {application.reason ? (
            <div className="space-y-1 sm:col-span-2 pt-1 border-t border-border/60">
              <span className="text-muted-foreground">Lý do / Hoàn cảnh:</span>
              <p className="text-foreground italic font-normal">
                "{application.reason}"
              </p>
            </div>
          ) : null}
        </div>

        {/* Review Note Alert Box */}
        {application.reviewNote ? (
          <div
            className={cn(
              "rounded-lg p-3 text-xs sm:text-sm flex items-start gap-2.5",
              application.status === "need_supplement"
                ? "border border-amber-500/30 bg-amber-500/10 text-amber-900 dark:text-amber-200"
                : application.status === "rejected"
                  ? "border border-destructive/30 bg-destructive/10 text-destructive dark:text-red-300"
                  : "border border-primary/20 bg-primary/5 text-foreground",
            )}
          >
            {application.status === "need_supplement" ? (
              <AlertCircle className="size-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
            ) : application.status === "rejected" ? (
              <XCircle className="size-4 text-destructive shrink-0 mt-0.5" />
            ) : (
              <FileCheck2 className="size-4 text-primary shrink-0 mt-0.5" />
            )}
            <div className="space-y-0.5">
              <p className="font-semibold">Ghi chú từ cán bộ quản lý KTX:</p>
              <p className="leading-relaxed">{application.reviewNote}</p>
            </div>
          </div>
        ) : null}
      </CardContent>

      <CardFooter className="p-4 sm:p-5 sm:pt-0 flex flex-wrap items-center justify-between gap-2.5 border-t pt-3.5">
        <div className="text-xs text-muted-foreground">
          {application.status === "approved" && (
            <span className="text-emerald-600 dark:text-emerald-400 font-medium">
              ✓ Hồ sơ đã được duyệt. Bạn có thể vào chọn phòng.
            </span>
          )}
          {application.status === "assigned" && (
            <span className="text-blue-600 dark:text-blue-400 font-medium">
              ✓ Bạn đã được xếp phòng chính thức trong đợt này.
            </span>
          )}
          {application.status === "submitted" && (
            <span>Hồ sơ đang chờ cán bộ phòng CTSV xét duyệt.</span>
          )}
          {application.status === "need_supplement" && (
            <span className="text-amber-600 dark:text-amber-400 font-medium">
              ⚠ Vui lòng cập nhật hồ sơ theo yêu cầu của cán bộ.
            </span>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto justify-end">
          {canWithdraw && canWithdrawStatus && (
            <Button
              variant="outline"
              size="sm"
              disabled={isWithdrawing}
              onClick={() => onWithdraw(application)}
              className="text-muted-foreground hover:text-destructive"
            >
              <RotateCcw className="size-3.5" /> Rút hồ sơ
            </Button>
          )}

          {application.status === "need_supplement" && (
            <Button asChild size="sm">
              <Link
                to="/student/register"
                search={{
                  registrationPeriodId: application.registrationPeriodId,
                }}
              >
                <FileEdit className="size-3.5" /> Bổ sung hồ sơ
              </Link>
            </Button>
          )}

          {isApprovedOrAssigned && (
            <Button asChild size="sm">
              <Link
                to="/student/room-selection"
                search={{
                  registrationPeriodId: application.registrationPeriodId,
                }}
              >
                <DoorOpen className="size-3.5" />
                {application.status === "assigned"
                  ? "Xem chỗ ở đã chốt"
                  : "Quản lý & Đổi phòng"}
                <ArrowRight className="size-3.5" />
              </Link>
            </Button>
          )}
        </div>
      </CardFooter>
    </Card>
  );
}

function ApplicationProgressTracker({
  status,
}: {
  status: StudentApplicationStatus;
}) {
  const isSubmitted = status !== "draft";
  const isApproved = status === "approved" || status === "assigned";
  const isAssigned = status === "assigned";
  const isRejected = status === "rejected";
  const isCancelled = status === "cancelled";

  if (isCancelled) {
    return (
      <div className="flex items-center gap-2 rounded-md bg-muted/40 p-2.5 text-xs text-muted-foreground">
        <RotateCcw className="size-4 shrink-0" />
        <span>Hồ sơ này đã được rút khỏi đợt đăng ký.</span>
      </div>
    );
  }

  if (isRejected) {
    return (
      <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-2.5 text-xs text-destructive">
        <XCircle className="size-4 shrink-0" />
        <span>Hồ sơ không được phê duyệt trong đợt này.</span>
      </div>
    );
  }

  const steps = [
    {
      label: "1. Đã nộp",
      done: isSubmitted,
      active: status === "submitted",
    },
    {
      label: "2. Xét duyệt",
      done: isApproved,
      active: status === "need_supplement",
    },
    {
      label: "3. Chọn phòng",
      done: isAssigned,
      active: status === "approved",
    },
    {
      label: "4. Chốt phòng",
      done: isAssigned,
      active: isAssigned,
    },
  ];

  return (
    <div className="py-1">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {steps.map((step) => (
          <div
            key={step.label}
            className={cn(
              "flex items-center gap-1.5 sm:gap-2 rounded-md border p-2 text-[11px] sm:text-xs transition-all",
              step.done
                ? "border-emerald-500/40 bg-emerald-500/5 text-emerald-800 dark:text-emerald-300 font-semibold"
                : step.active
                  ? "border-primary bg-primary/10 text-primary font-bold ring-1 ring-primary/30"
                  : "border-border/60 bg-muted/20 text-muted-foreground/70",
            )}
          >
            {step.done ? (
              <CheckCircle2 className="size-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
            ) : step.active ? (
              <Clock3 className="size-3.5 text-primary shrink-0 animate-pulse" />
            ) : (
              <div className="size-3.5 rounded-full border border-muted-foreground/40 shrink-0" />
            )}
            <span className="truncate">{step.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function RegistrationHistorySkeleton() {
  return (
    <div className="mx-auto max-w-5xl space-y-5 px-3.5 pb-16 sm:space-y-6 sm:px-6">
      <div className="flex justify-between items-center">
        <div className="space-y-2">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-8 w-60" />
          <Skeleton className="h-4 w-80" />
        </div>
        <Skeleton className="h-10 w-36" />
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: skeleton items
          <Card key={i}>
            <CardContent className="flex items-center gap-4 p-5">
              <Skeleton className="size-11 rounded-lg" />
              <div className="space-y-2">
                <Skeleton className="h-3 w-28" />
                <Skeleton className="h-6 w-12" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="space-y-4">
        <Skeleton className="h-5 w-40" />
        {Array.from({ length: 2 }).map((_, i) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: skeleton items
          <Card key={i}>
            <CardHeader className="p-5 pb-3 border-b">
              <div className="flex justify-between">
                <Skeleton className="h-6 w-48" />
                <Skeleton className="h-4 w-24" />
              </div>
              <Skeleton className="h-4 w-36" />
            </CardHeader>
            <CardContent className="p-5 space-y-3">
              <div className="grid grid-cols-4 gap-2">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </div>
              <Skeleton className="h-16 w-full rounded-lg" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
