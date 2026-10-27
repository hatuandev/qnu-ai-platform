import { Link } from "@tanstack/react-router";
import {
  AlertTriangle,
  BarChart3,
  Building2,
  CheckCircle2,
  ClipboardList,
  Home,
  Receipt,
  RefreshCw,
  Users,
} from "lucide-react";
import { ChartCard } from "@/components/admin/chart-card";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ApplicationStatusChart,
  BuildingOccupancyChart,
  InvoiceStatusChart,
} from "@/features/dashboard/dashboard-charts";
import { DashboardTrendChart } from "@/features/dashboard/dashboard-trend-chart";
import {
  useDashboardStatsQuery,
  useRoomOccupancyQuery,
} from "@/features/reports/api";
import type { DashboardStats } from "@/features/reports/types";
import { cn } from "@/lib/utils";

const dashboardSkeletonKeys = [
  "students",
  "residences",
  "occupancy",
  "available-places",
  "applications",
  "outstanding",
];

function formatNumber(value: number) {
  return new Intl.NumberFormat("vi-VN").format(value);
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(value);
}

function statusCount(values: Record<string, number>, status: string): number {
  return values[status] ?? 0;
}

function DashboardLoading() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-9 w-56" />
        <Skeleton className="h-5 w-full max-w-xl" />
      </div>
      <div className="grid gap-px overflow-hidden rounded-xl border bg-border sm:grid-cols-2 xl:grid-cols-6">
        {dashboardSkeletonKeys.map((key) => (
          <Skeleton key={key} className="h-32 rounded-none bg-card" />
        ))}
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <Skeleton className="h-80 rounded-xl" />
        <Skeleton className="h-80 rounded-xl" />
      </div>
    </div>
  );
}

function DashboardError({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="rounded-xl border border-dashed p-10 text-center">
      <p className="font-semibold text-base">
        Không thể tải dữ liệu tổng quan KTX.
      </p>
      <p className="type-supporting mt-1 text-muted-foreground text-xs">
        Vui lòng kiểm tra kết nối mạng hoặc thử lại sau.
      </p>
      <Button
        className="mt-4 gap-1.5 text-xs"
        variant="outline"
        size="sm"
        onClick={onRetry}
      >
        <RefreshCw className="size-3.5" /> Thử lại
      </Button>
    </div>
  );
}

function DashboardAlerts({ data }: { data: DashboardStats }) {
  const ac = data.actionCenter;
  const submitted =
    ac?.pendingApplicationsCount ??
    statusCount(data.applicationsByStatus, "submitted");
  const needSupplement =
    ac?.needSupplementApplicationsCount ??
    statusCount(data.applicationsByStatus, "need_supplement");
  const maintenance =
    ac?.maintenanceRequestsCount ??
    Object.entries(data.supportRequestsByStatus)
      .filter(
        ([status]) => !["resolved", "closed", "cancelled"].includes(status),
      )
      .reduce((total, [, count]) => total + count, 0);
  const expiring = ac?.expiringContractsCount ?? 0;
  const overdue = ac?.overdueInvoicesCount ?? 0;

  const alerts = [
    {
      label: "Hồ sơ chờ xét duyệt",
      value: submitted,
      description: "Cần kiểm tra đối tượng ưu tiên & duyệt",
      dotColor: "bg-amber-500",
      variant: submitted > 0 ? ("warning" as const) : ("secondary" as const),
      to: "/applications" as const,
      search: {
        q: "",
        status: "submitted" as const,
        registrationPeriodId: undefined,
        page: 1,
        pageSize: 10 as const,
      },
    },
    {
      label: "Hồ sơ cần bổ sung",
      value: needSupplement,
      description: "Chưa đủ minh chứng ưu tiên hợp lệ",
      dotColor: "bg-purple-500",
      variant:
        needSupplement > 0 ? ("warning" as const) : ("secondary" as const),
      to: "/applications" as const,
      search: {
        q: "",
        status: "need_supplement" as const,
        registrationPeriodId: undefined,
        page: 1,
        pageSize: 10 as const,
      },
    },
    {
      label: "Sự cố & Sửa chữa KTX",
      value: maintenance,
      description: "Yêu cầu sửa điện nước, phòng ở, thiết bị",
      dotColor: "bg-rose-500",
      variant:
        maintenance > 0 ? ("destructive" as const) : ("secondary" as const),
      to: "/support" as const,
      search: {
        q: "",
        status: undefined,
        type: undefined,
        page: 1,
        pageSize: 10,
      },
    },
    {
      label: "Hợp đồng sắp hết hạn",
      value: expiring,
      description: "Cần gửi nhắc gia hạn hoặc trả phòng trong 15 ngày",
      dotColor: "bg-blue-500",
      variant: expiring > 0 ? ("default" as const) : ("secondary" as const),
      to: "/residences" as const,
      search: {
        q: "",
        status: "active" as const,
        page: 1,
        pageSize: 10 as const,
      },
    },
    {
      label: "Hóa đơn quá hạn nộp",
      value: overdue,
      description: ac?.overdueInvoicesAmount
        ? `Nợ quá hạn: ${formatCurrency(ac.overdueInvoicesAmount)}`
        : "Các khoản nợ phí cần đôn đốc",
      dotColor: "bg-destructive",
      variant: overdue > 0 ? ("destructive" as const) : ("secondary" as const),
      to: "/debts" as const,
      search: {
        q: "",
        academicYearId: undefined,
      },
    },
  ];

  return (
    <ChartCard
      title="Trung tâm tác nghiệp"
      description="Các công việc cần xử lý và theo dõi ngay trong ca trực."
    >
      <div className="divide-y">
        {alerts.map((alert) => (
          <Link
            key={alert.label}
            to={alert.to}
            search={alert.search}
            className="flex items-center justify-between gap-4 px-4 py-3.5 transition-colors hover:bg-muted/50 sm:px-5"
          >
            <div className="flex min-w-0 items-start gap-3">
              <div className="mt-0.5 relative flex items-center justify-center">
                <AlertTriangle
                  className="size-4 shrink-0 text-amber-500"
                  aria-hidden="true"
                />
                {alert.value > 0 && (
                  <span
                    className={cn(
                      "absolute -top-1 -right-1 size-2 rounded-full animate-pulse",
                      alert.dotColor,
                    )}
                  />
                )}
              </div>
              <div className="min-w-0">
                <p className="font-semibold text-sm text-foreground">
                  {alert.label}
                </p>
                <p className="type-supporting text-muted-foreground text-xs">
                  {alert.description}
                </p>
              </div>
            </div>
            <Badge
              variant={alert.variant}
              className="font-mono font-semibold text-xs px-2 py-0.5 tabular-nums"
            >
              {formatNumber(alert.value)}
            </Badge>
          </Link>
        ))}
      </div>
    </ChartCard>
  );
}

function DashboardSummary({ data }: { data: DashboardStats }) {
  const collectionRate =
    data.totalInvoicedAmount > 0
      ? (data.totalPaidAmount / data.totalInvoicedAmount) * 100
      : 0;
  const pendingApplications =
    statusCount(data.applicationsByStatus, "submitted") +
    statusCount(data.applicationsByStatus, "need_supplement");

  const rows = [
    {
      label: "Quy mô chỗ ở",
      value: `${formatNumber(data.totalRooms)} phòng`,
      detail: `${formatNumber(data.totalPlaces)} chỗ trong danh mục KTX`,
    },
    {
      label: "Chỗ còn khả dụng",
      value: formatNumber(data.availablePlaces),
      detail: `${Number(data.placeOccupancyRate).toFixed(1)}% chỗ đang sử dụng`,
    },
    {
      label: "Hồ sơ cần xử lý",
      value: formatNumber(pendingApplications),
      detail: `${formatNumber(data.totalApplications)} hồ sơ đã ghi nhận`,
    },
    {
      label: "Tỷ lệ thu phí",
      value: `${collectionRate.toFixed(1)}%`,
      detail: `${formatCurrency(data.totalPaidAmount)} đã thu thực tế`,
    },
  ];

  return (
    <ChartCard
      title="Tóm tắt vận hành"
      description="Các chỉ số chính của hoạt động ký túc xá."
    >
      <div className="divide-y">
        {rows.map((row) => (
          <div
            key={row.label}
            className="flex items-center justify-between gap-4 px-4 py-3.5 sm:px-5 hover:bg-muted/30 transition-colors"
          >
            <div className="min-w-0">
              <p className="font-semibold text-sm text-foreground">
                {row.label}
              </p>
              <p className="type-supporting text-muted-foreground text-xs">
                {row.detail}
              </p>
            </div>
            <p className="shrink-0 text-right text-base sm:text-lg font-bold font-mono text-foreground">
              {row.value}
            </p>
          </div>
        ))}
      </div>
    </ChartCard>
  );
}

export function DashboardPage() {
  const dashboard = useDashboardStatsQuery();
  const occupancy = useRoomOccupancyQuery({});

  const isFetching = dashboard.isFetching || occupancy.isFetching;

  const retry = () => {
    void dashboard.refetch();
    void occupancy.refetch();
  };

  if (dashboard.isLoading || occupancy.isLoading) {
    return <DashboardLoading />;
  }

  if (
    dashboard.isError ||
    occupancy.isError ||
    !dashboard.data ||
    !occupancy.data
  ) {
    return <DashboardError onRetry={retry} />;
  }

  const data = dashboard.data;
  const occupancyData = occupancy.data;
  const availableRoomRate = data.totalPlaces
    ? (data.availablePlaces / Math.max(data.totalPlaces, 1)) * 100
    : 0;

  return (
    <div className="space-y-6">
      {/* 1. Page Header */}
      <PageHeader
        eyebrow="KÝ TÚC XÁ / TỔNG QUAN"
        title="Tổng quan KTX"
        description="Theo dõi sinh viên, chỗ ở, hồ sơ đăng ký và tình hình thu phí trong một màn hình."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs font-semibold"
              onClick={retry}
              disabled={isFetching}
            >
              <RefreshCw
                className={cn("size-3.5", isFetching && "animate-spin")}
              />
              <span>Làm mới</span>
            </Button>
            <Button size="sm" className="gap-1.5 text-xs font-semibold" asChild>
              <Link to="/reports">
                <BarChart3 className="size-3.5" />
                <span>Báo cáo chi tiết</span>
              </Link>
            </Button>
          </div>
        }
      />

      {/* 2. Top 6 KPI Metrics Cards */}
      <Card className="overflow-hidden border bg-card shadow-xs">
        <CardContent className="grid p-0 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 divide-y sm:divide-y-0 sm:divide-x">
          <KpiMetric
            label="Sinh viên đang học"
            value={formatNumber(data.activeStudents)}
            helper={`${formatNumber(data.totalStudents)} hồ sơ sinh viên`}
            icon={Users}
          />
          <KpiMetric
            label="Đang cư trú"
            value={formatNumber(data.totalActiveResidences)}
            helper={`${formatNumber(data.totalCheckedOutResidences)} lượt đã trả phòng`}
            icon={Home}
          />
          <KpiMetric
            label="Tỷ lệ sử dụng chỗ"
            value={`${Number(data.placeOccupancyRate).toFixed(1)}%`}
            delta={`${formatNumber(data.occupiedPlaces)}/${formatNumber(data.totalPlaces)}`}
            helper="chỗ đang sử dụng"
            icon={Building2}
          />
          <KpiMetric
            label="Chỗ còn trống"
            value={formatNumber(data.availablePlaces)}
            helper={`${formatNumber(data.totalRooms)} phòng trong danh mục`}
            icon={Building2}
          />
          <KpiMetric
            label="Hồ sơ cần xử lý"
            value={formatNumber(
              statusCount(data.applicationsByStatus, "submitted") +
                statusCount(data.applicationsByStatus, "need_supplement"),
            )}
            helper={`${formatNumber(data.totalApplications)} hồ sơ đã ghi nhận`}
            icon={ClipboardList}
          />
          <KpiMetric
            label="Công nợ cần thu"
            value={formatCurrency(data.totalOutstandingAmount)}
            trend="negative"
            helper={`${formatNumber(data.totalInvoices)} hóa đơn đã lập`}
            icon={Receipt}
          />
        </CardContent>
      </Card>

      {/* 3. Trend & Summary */}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.65fr)_minmax(280px,0.85fr)]">
        <ChartCard
          title="Xu hướng hồ sơ đăng ký"
          description="Số hồ sơ theo ngày trong 30 ngày gần nhất."
          action={
            <Badge variant="outline" className="text-xs font-mono font-normal">
              30 ngày qua
            </Badge>
          }
        >
          <div className="h-[220px] p-3 sm:h-[280px] sm:p-5">
            <DashboardTrendChart data={data.dailyApplicationTrends} />
          </div>
        </ChartCard>
        <DashboardSummary data={data} />
      </div>

      {/* 4. Room Occupancy Status & Action Alerts */}
      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <ChartCard
          title="Tình trạng chỗ ở"
          description="Tổng hợp số chỗ và mức độ sử dụng hiện tại."
          action={
            <Link
              to="/rooms"
              search={{
                q: "",
                buildingId: "",
                floorId: "",
                roomTypeId: "",
                status: undefined,
                page: 1,
                pageSize: 10,
              }}
              className="type-supporting text-xs font-semibold text-primary hover:underline"
            >
              Xem danh sách phòng →
            </Link>
          }
        >
          <div className="space-y-5 px-4 py-5 sm:px-5">
            <div className="flex items-end justify-between gap-4">
              <div>
                <p className="type-supporting text-muted-foreground text-xs">
                  Đã sử dụng
                </p>
                <p className="mt-1 text-3xl font-bold font-mono tracking-tight text-foreground">
                  {formatNumber(data.occupiedPlaces)}
                  <span className="type-supporting ml-2 font-normal text-muted-foreground text-sm">
                    / {formatNumber(data.totalPlaces)} chỗ
                  </span>
                </p>
              </div>
              <p className="text-lg font-bold font-mono text-primary">
                {Number(data.placeOccupancyRate).toFixed(1)}%
              </p>
            </div>
            <Progress
              value={Math.min(
                100,
                Math.max(0, Number(data.placeOccupancyRate)),
              )}
              aria-label={`Tỷ lệ sử dụng ${Number(data.placeOccupancyRate).toFixed(1)} phần trăm`}
              className="h-2.5"
            />
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="rounded-lg border bg-muted/20 p-3">
                <p className="text-base sm:text-lg font-bold font-mono text-foreground">
                  {formatNumber(data.availablePlaces)}
                </p>
                <p className="type-supporting text-muted-foreground text-xs mt-0.5">
                  Còn trống
                </p>
              </div>
              <div className="rounded-lg border bg-emerald-500/5 border-emerald-500/20 p-3">
                <p className="text-base sm:text-lg font-bold font-mono text-emerald-600 dark:text-emerald-400">
                  {formatNumber(data.occupiedPlaces)}
                </p>
                <p className="type-supporting text-emerald-600 dark:text-emerald-400 text-xs mt-0.5">
                  Đang ở
                </p>
              </div>
              <div className="rounded-lg border bg-muted/20 p-3">
                <p className="text-base sm:text-lg font-bold font-mono text-foreground">
                  {formatNumber(
                    statusCount(occupancyData.roomsByStatus, "maintenance"),
                  )}
                </p>
                <p className="type-supporting text-muted-foreground text-xs mt-0.5">
                  Bảo trì
                </p>
              </div>
            </div>
            <p className="type-supporting text-muted-foreground text-xs">
              {availableRoomRate > 0
                ? `${availableRoomRate.toFixed(1)}% tổng số chỗ hiện còn khả dụng để sắp xếp sinh viên.`
                : "Hiện chưa có chỗ khả dụng trong danh mục."}
            </p>
          </div>
        </ChartCard>

        <DashboardAlerts data={data} />
      </div>

      {/* 5. Charts: Building Occupancy & Application Status */}
      <div className="grid gap-6 xl:grid-cols-2">
        <ChartCard
          title="Phân bổ chỗ ở theo tòa"
          description="So sánh số chỗ và tỷ lệ sử dụng giữa các tòa nhà."
        >
          <div className="h-[220px] p-3 sm:h-[240px] sm:p-5">
            <BuildingOccupancyChart data={occupancyData.byBuilding} />
          </div>
        </ChartCard>

        <ChartCard
          title="Hồ sơ đăng ký"
          description="Phân loại hồ sơ theo trạng thái xử lý hiện tại."
          action={
            <Link
              to="/applications"
              search={{
                q: "",
                status: undefined,
                registrationPeriodId: undefined,
                page: 1,
                pageSize: 10,
              }}
              className="type-supporting text-xs font-semibold text-primary hover:underline"
            >
              Xem tất cả hồ sơ →
            </Link>
          }
        >
          <div className="h-[220px] p-3 sm:h-[240px] sm:p-5">
            <ApplicationStatusChart data={data.applicationsByStatus} />
          </div>
          <p className="type-supporting border-t px-4 py-3 text-muted-foreground text-xs sm:px-5">
            Tổng cộng {formatNumber(data.totalApplications)} hồ sơ đã ghi nhận
            trong hệ thống.
          </p>
        </ChartCard>
      </div>

      {/* 6. Financial Overview Card */}
      <ChartCard
        title="Tài chính và Doanh thu"
        description="Tổng hợp hóa đơn, số tiền đã thu và công nợ hiện tại."
        action={
          <Link
            to="/invoices"
            search={{ q: "", status: undefined, page: 1, pageSize: 10 }}
            className="type-supporting text-xs font-semibold text-primary hover:underline"
          >
            Xem danh sách hóa đơn →
          </Link>
        }
      >
        <div className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-4 sm:p-5">
          <div className="rounded-lg border bg-muted/20 p-3">
            <p className="type-supporting text-muted-foreground text-xs">
              Đã lập hóa đơn
            </p>
            <p className="mt-1 text-base sm:text-lg font-bold font-mono text-foreground">
              {formatCurrency(data.totalInvoicedAmount)}
            </p>
          </div>
          <div className="rounded-lg border bg-emerald-500/5 border-emerald-500/20 p-3">
            <p className="type-supporting text-emerald-600 dark:text-emerald-400 text-xs font-medium">
              Đã thu thực tế
            </p>
            <p className="mt-1 text-base sm:text-lg font-bold font-mono text-emerald-600 dark:text-emerald-400">
              {formatCurrency(data.totalPaidAmount)}
            </p>
          </div>
          <div className="rounded-lg border bg-destructive/5 border-destructive/20 p-3">
            <p className="type-supporting text-destructive text-xs font-medium">
              Còn phải thu (Nợ)
            </p>
            <p className="mt-1 text-base sm:text-lg font-bold font-mono text-destructive">
              {formatCurrency(data.totalOutstandingAmount)}
            </p>
          </div>
          <div className="rounded-lg border bg-muted/20 p-3">
            <p className="type-supporting text-muted-foreground text-xs">
              Tỷ lệ hoàn thành
            </p>
            <div className="mt-1 flex items-center gap-1.5">
              <span className="text-base sm:text-lg font-bold font-mono text-foreground">
                {data.totalInvoicedAmount > 0
                  ? (
                      (data.totalPaidAmount / data.totalInvoicedAmount) *
                      100
                    ).toFixed(1)
                  : "0.0"}
                %
              </span>
              <CheckCircle2 className="size-3.5 text-emerald-600 dark:text-emerald-400" />
            </div>
          </div>
        </div>
        <div className="border-t">
          <div className="h-[220px] p-3 sm:h-[240px] sm:p-5">
            <InvoiceStatusChart data={data.invoicesByStatus} />
          </div>
        </div>
      </ChartCard>
    </div>
  );
}
