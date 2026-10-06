import {
  AlertCircle,
  Bell,
  ClipboardList,
  GraduationCap,
  House,
  Mail,
  RefreshCw,
  User,
  Wallet,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ApiError } from "@/app/api/client";
import { useAuth } from "@/app/auth";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useMyPaymentInvoicesQuery } from "@/features/payments/api";
import {
  useMyApplicationsQuery,
  useMyNotificationsQuery,
  useOpenRegistrationPeriodsQuery,
  useStudentRegistrationCatalogQuery,
  useStudentRoomSelectionQuery,
  useWithdrawStudentApplication,
} from "@/features/student/api";
import {
  OpenPeriodsSection,
  OtherApplicationsSection,
} from "@/features/student/dashboard/applications-section";
import { StudentDashboardSkeleton } from "@/features/student/dashboard/dashboard-skeleton";
import { money } from "@/features/student/dashboard/helpers";
import { InvoiceCard } from "@/features/student/dashboard/invoice-card";
import {
  type QuickStatItem,
  QuickStatsGrid,
} from "@/features/student/dashboard/quick-stats";
import { RoomCard } from "@/features/student/dashboard/room-card";
import { StatusHeroSection } from "@/features/student/dashboard/status-hero";
import { SupportCard } from "@/features/student/dashboard/support-card";
import {
  applicationStatusLabels,
  type MyApplication,
} from "@/features/student/types";
import { formatDate } from "@/lib/date-utils";
import { cn } from "@/lib/utils";
import { useRbac } from "@/rbac/context";

export function StudentDashboardPage() {
  const { user } = useAuth();
  const { can } = useRbac();
  const canViewPayments = can("ktx.payments.view");

  const periodsQuery = useOpenRegistrationPeriodsQuery();
  const applicationsQuery = useMyApplicationsQuery();
  const notificationsQuery = useMyNotificationsQuery();
  const withdrawMutation = useWithdrawStudentApplication();
  const paymentsQuery = useMyPaymentInvoicesQuery(
    { page: 1, pageSize: 5 },
    canViewPayments,
  );

  const isInitialLoading =
    (periodsQuery.isLoading || applicationsQuery.isLoading) &&
    !periodsQuery.data &&
    !applicationsQuery.data;

  const [isManualRefreshing, setIsManualRefreshing] = useState(false);
  const isFetchingAny =
    periodsQuery.isFetching ||
    applicationsQuery.isFetching ||
    notificationsQuery.isFetching ||
    paymentsQuery.isFetching;

  async function handleManualRefresh() {
    setIsManualRefreshing(true);
    try {
      await Promise.allSettled([
        periodsQuery.refetch(),
        applicationsQuery.refetch(),
        notificationsQuery.refetch(),
        paymentsQuery.refetch(),
      ]);
      toast.success("Đã làm mới dữ liệu mới nhất.");
    } catch {
      toast.error("Không thể làm mới dữ liệu.");
    } finally {
      setIsManualRefreshing(false);
    }
  }

  const applications = applicationsQuery.data ?? [];
  const periods = periodsQuery.data ?? [];
  const activePeriod = periods[0];

  const focusApplication =
    (activePeriod
      ? applications.find(
          (item) => item.registrationPeriodId === activePeriod.id,
        )
      : undefined) ??
    applications.find(
      (item) => item.status === "approved" || item.status === "assigned",
    ) ??
    applications[0];
  // Room data only relevant for approved/assigned applications.
  const roomApplication =
    focusApplication &&
    (focusApplication.status === "approved" ||
      focusApplication.status === "assigned")
      ? focusApplication
      : applications.find(
          (item) => item.status === "approved" || item.status === "assigned",
        );
  const roomSelectionQuery = useStudentRoomSelectionQuery(
    roomApplication?.registrationPeriodId,
  );
  const roomSelection = roomSelectionQuery.data ?? null;
  const catalogPeriodId =
    focusApplication?.registrationPeriodId ?? activePeriod?.id;
  const catalogQuery = useStudentRegistrationCatalogQuery(catalogPeriodId);
  const student = catalogQuery.data?.student ?? null;

  const displayName = student?.fullName || user?.name || "bạn";
  const displayCode =
    student?.studentCode ||
    (user?.name && /^\d+$/.test(user.name) ? user.name : null);
  const displayClassFaculty = [student?.className, student?.faculty]
    .filter(Boolean)
    .join(" · ");
  const displayEmail =
    student?.schoolEmail ||
    (displayCode ? `${displayCode.toLowerCase()}@st.qnu.edu.vn` : user?.email);

  const unreadCount =
    notificationsQuery.data?.filter((item) => !item.readAt).length ?? 0;
  const profileNotLinked =
    applicationsQuery.error instanceof ApiError &&
    applicationsQuery.error.status === 403;

  const invoices = paymentsQuery.data?.items ?? [];
  const unpaidInvoices = invoices.filter(
    (invoice) => invoice.remainingAmount > 0,
  );
  const totalUnpaid = unpaidInvoices.reduce(
    (sum, invoice) => sum + invoice.remainingAmount,
    0,
  );
  const latestInvoice = unpaidInvoices[0] ?? invoices[0] ?? null;

  const [pendingWithdrawal, setPendingWithdrawal] =
    useState<MyApplication | null>(null);

  function withdraw(application: MyApplication) {
    setPendingWithdrawal(application);
  }

  function confirmWithdrawal() {
    if (!pendingWithdrawal) return;
    void withdrawMutation
      .mutateAsync(pendingWithdrawal.id)
      .then(() => {
        setPendingWithdrawal(null);
        toast.success("Đã rút hồ sơ đăng ký.");
      })
      .catch((error: unknown) =>
        toast.error(
          error instanceof Error ? error.message : "Không thể rút hồ sơ.",
        ),
      );
  }

  const isWithdrawing = (application: MyApplication) =>
    withdrawMutation.isPending && withdrawMutation.variables === application.id;
  const canWithdrawApplications = can("ktx.applications.withdraw");

  const quickStats: QuickStatItem[] = [];
  if (focusApplication) {
    quickStats.push({
      icon: ClipboardList,
      label: "Hồ sơ",
      value: focusApplication.applicationCode,
      sub: focusApplication.registrationPeriodName,
      badge: {
        text: applicationStatusLabels[focusApplication.status],
        variant:
          focusApplication.status === "rejected" ||
          focusApplication.status === "cancelled"
            ? "warning"
            : focusApplication.status === "assigned"
              ? "success"
              : "default",
      },
      to: "/student/registration-history",
    });
  }
  if (
    roomApplication &&
    (roomApplication.status === "approved" ||
      roomApplication.status === "assigned")
  ) {
    const selectedRoom = roomSelection?.currentSelection;
    const roomValue = selectedRoom
      ? `Phòng ${selectedRoom.roomName}`
      : "Chưa xếp";
    const roomSub = selectedRoom
      ? `${selectedRoom.buildingName} · Tầng ${selectedRoom.floorName}`
      : roomSelection?.selectionStatus === "open"
        ? "Đủ điều kiện chọn phòng"
        : "Đang chờ cập nhật";
    const roomBadgeText = selectedRoom
      ? selectedRoom.status === "checked_in"
        ? "Đang cư trú"
        : selectedRoom.status === "assigned"
          ? "Đã xếp chỗ"
          : "Đã chọn phòng"
      : "Đã duyệt hồ sơ";
    quickStats.push({
      icon: House,
      label: "Phòng",
      value: roomValue,
      sub: roomSub,
      badge: { text: roomBadgeText, variant: "success" },
      to: "/student/room-selection",
      search: {
        registrationPeriodId: roomApplication.registrationPeriodId,
      },
    });
  }
  if (canViewPayments) {
    const hasOverdue = unpaidInvoices.some(
      (inv) => inv.dueDate && new Date(inv.dueDate).getTime() < Date.now(),
    );
    quickStats.push({
      icon: Wallet,
      label: "KTX phí",
      value: totalUnpaid > 0 ? money(totalUnpaid) : "Không có nợ",
      sub:
        unpaidInvoices.length > 0
          ? `${unpaidInvoices.length} hóa đơn chưa thanh toán`
          : undefined,
      badge:
        totalUnpaid > 0
          ? hasOverdue
            ? { text: "Quá hạn", variant: "warning" }
            : { text: "Chưa nộp", variant: "warning" }
          : { text: "Không nợ", variant: "success" },
      to: "/student/payments",
    });
  } else {
    quickStats.push({
      icon: House,
      label: "Đợt đăng ký",
      value:
        periods.length > 0 ? `${periods.length} đang mở` : "Không có đợt mở",
      sub:
        applications.length > 0
          ? `${applications.length} hồ sơ của bạn`
          : "Theo dõi thông báo từ KTX",
      badge:
        periods.length > 0
          ? { text: "Có thể đăng ký", variant: "success" }
          : { text: "Đang theo dõi", variant: "secondary" },
      ...(periods.length > 0 ? { to: "/student/register" } : {}),
    });
  }
  quickStats.push({
    icon: Bell,
    label: "Thông báo",
    value: notificationsQuery.isLoading
      ? "Đang tải..."
      : unreadCount > 0
        ? `${unreadCount} chưa đọc`
        : "Đã đọc hết",
    sub:
      unreadCount > 0
        ? `${notificationsQuery.data?.length ?? 0} thông báo gần đây`
        : undefined,
  });

  if (isInitialLoading) {
    return <StudentDashboardSkeleton />;
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header with Student Profile Info & Manual Refresh */}
      <div className="flex flex-col gap-3.5 rounded-xl border bg-card p-4 shadow-xs sm:flex-row sm:items-center sm:justify-between sm:p-5">
        <div className="flex items-center gap-3.5">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary sm:size-11">
            <User className="size-5" />
          </div>
          <div className="min-w-0 space-y-0.5 sm:space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-base font-bold tracking-tight text-foreground sm:text-xl">
                Xin chào, {displayName}
              </h1>
              {displayCode ? (
                <Badge
                  variant="outline"
                  className="font-mono text-[11px] sm:text-xs"
                >
                  MSSV: {displayCode}
                </Badge>
              ) : null}
            </div>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
              {displayClassFaculty ? (
                <span className="flex items-center gap-1">
                  <GraduationCap className="size-3.5 shrink-0" />
                  <span>{displayClassFaculty}</span>
                </span>
              ) : null}
              {displayEmail ? (
                <span className="hidden items-center gap-1 sm:flex">
                  <Mail className="size-3.5 shrink-0" />
                  <span>{displayEmail}</span>
                </span>
              ) : null}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-center">
          <span className="hidden text-xs text-muted-foreground sm:inline">
            {formatDate(new Date())}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={isManualRefreshing || isFetchingAny}
            onClick={() => void handleManualRefresh()}
            className="h-8 gap-1.5 px-2.5 text-xs"
          >
            <RefreshCw
              className={cn(
                "size-3.5",
                (isManualRefreshing || isFetchingAny) && "animate-spin",
              )}
            />
            <span>
              {isManualRefreshing || isFetchingAny ? "Đang tải..." : "Làm mới"}
            </span>
          </Button>
        </div>
      </div>

      {profileNotLinked ? (
        <Alert variant="warning">
          <AlertCircle />
          <div>
            <AlertTitle>Chưa có hồ sơ sinh viên</AlertTitle>
            <AlertDescription>
              Hệ thống chưa tìm thấy hồ sơ được đồng bộ từ UIS nên bạn chưa thể
              nộp hồ sơ. Vui lòng đăng nhập lại hoặc liên hệ phòng Công tác sinh
              viên.
            </AlertDescription>
          </div>
        </Alert>
      ) : null}
      {periodsQuery.isError ? (
        <Alert variant="destructive">
          <AlertCircle />
          <div>
            <AlertTitle>Không thể tải đợt đăng ký</AlertTitle>
            <AlertDescription className="flex items-center gap-3">
              {periodsQuery.error instanceof Error
                ? periodsQuery.error.message
                : "Vui lòng thử lại."}
              <Button
                variant="outline"
                size="sm"
                onClick={() => void periodsQuery.refetch()}
              >
                <RefreshCw /> Thử lại
              </Button>
            </AlertDescription>
          </div>
        </Alert>
      ) : null}

      {/* 1. Status Hero (nếu SV đã có hồ sơ đang xử lý) */}
      {focusApplication ? (
        <StatusHeroSection
          application={focusApplication}
          period={
            periods.find(
              (item) => item.id === focusApplication.registrationPeriodId,
            ) ?? activePeriod
          }
          selection={roomSelection}
        />
      ) : null}

      {/* 2. Đợt đăng ký đang mở (Được đưa lên vị trí đầu cho sinh viên dễ thấy & đăng ký ngay) */}
      <OpenPeriodsSection
        periods={periods}
        applications={applications}
        onWithdraw={withdraw}
        isWithdrawing={isWithdrawing}
        canWithdrawApplications={canWithdrawApplications}
      />

      {/* 3. Empty state nếu không có hồ sơ và không có đợt mở nào */}
      {!focusApplication && !periods.length ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center gap-3 py-12 text-center">
            <House className="size-10 text-muted-foreground/50" />
            <p className="font-semibold">Hiện chưa có đợt đăng ký mở</p>
            <p className="max-w-md text-sm text-muted-foreground">
              Bạn có thể quay lại sau hoặc theo dõi thông báo từ nhà trường.
            </p>
          </CardContent>
        </Card>
      ) : null}

      {/* 4. Quick stats */}
      {quickStats.length ? <QuickStatsGrid items={quickStats} /> : null}

      {/* 5. Thông tin phòng & KTX phí */}
      {roomApplication || canViewPayments ? (
        <div
          className={cn(
            "grid gap-4 sm:gap-6",
            roomApplication && canViewPayments && "lg:grid-cols-2",
          )}
        >
          {roomApplication ? <RoomCard selection={roomSelection} /> : null}
          {canViewPayments ? (
            <InvoiceCard invoice={latestInvoice} totalUnpaid={totalUnpaid} />
          ) : null}
        </div>
      ) : null}

      {/* 6. Banner Hỗ trợ & báo cáo sự cố */}
      <SupportCard />

      {/* 7. Hồ sơ các đợt khác */}
      <OtherApplicationsSection
        applications={applications}
        focusApplicationId={focusApplication?.id}
        onWithdraw={withdraw}
        isWithdrawing={isWithdrawing}
        canWithdrawApplications={canWithdrawApplications}
      />

      <ConfirmDialog
        open={pendingWithdrawal !== null}
        onOpenChange={(open) => {
          if (!open) setPendingWithdrawal(null);
        }}
        title="Rút hồ sơ đăng ký"
        description={
          pendingWithdrawal
            ? `Bạn có chắc muốn rút hồ sơ ${pendingWithdrawal.applicationCode}?`
            : ""
        }
        confirmLabel="Rút hồ sơ"
        isLoading={withdrawMutation.isPending}
        onConfirm={confirmWithdrawal}
      />
    </div>
  );
}
