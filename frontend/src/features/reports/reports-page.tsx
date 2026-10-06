import {
  BarChart3,
  Building2,
  CheckCircle2,
  ClipboardList,
  Home,
  PieChart,
  Receipt,
  RefreshCw,
  RotateCcw,
  TrendingUp,
  Users,
} from "lucide-react";
import { useMemo } from "react";
import { Combobox } from "@/components/admin/combobox";
import { EmptyState } from "@/components/admin/empty-state";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAcademicYearsQuery } from "@/features/academic-years/api";
import { money } from "@/features/invoices/invoices-page";
import {
  useApplicationStatsQuery,
  useDashboardStatsQuery,
  useRevenueStatsQuery,
  useRoomOccupancyQuery,
} from "@/features/reports/api";
import {
  ApplicationStatusChart,
  ApplicationYearTrendChart,
  BuildingOccupancyBarChart,
  RevenueDonutChart,
} from "@/features/reports/reports-charts";
import { cn } from "@/lib/utils";

const applicationStatusConfig: Record<
  string,
  {
    label: string;
    dot: string;
    variant: "success" | "info" | "warning" | "secondary" | "destructive";
  }
> = {
  Approved: { label: "Đã duyệt", dot: "bg-emerald-500", variant: "success" },
  UnderReview: { label: "Đang xét duyệt", dot: "bg-blue-500", variant: "info" },
  Submitted: { label: "Đã nộp", dot: "bg-amber-500", variant: "warning" },
  NeedsSupplement: {
    label: "Yêu cầu bổ sung",
    dot: "bg-purple-500",
    variant: "secondary",
  },
  Rejected: { label: "Từ chối", dot: "bg-red-500", variant: "destructive" },
  Cancelled: {
    label: "Đã hủy",
    dot: "bg-muted-foreground/60",
    variant: "secondary",
  },
  Draft: { label: "Nháp", dot: "bg-muted-foreground/40", variant: "secondary" },
};

function getApplicationStatusInfo(status: string) {
  return (
    applicationStatusConfig[status] ?? {
      label: status,
      dot: "bg-muted-foreground/60",
      variant: "secondary" as const,
    }
  );
}

export function ReportsPage({
  academicYearId,
  onAcademicYearChange,
}: {
  academicYearId?: string;
  onAcademicYearChange: (value: string | undefined) => void;
}) {
  const dashboard = useDashboardStatsQuery();
  const revenue = useRevenueStatsQuery({ academicYearId });
  const applications = useApplicationStatsQuery({ academicYearId });
  const occupancy = useRoomOccupancyQuery({});
  const years = useAcademicYearsQuery({ page: 1, pageSize: 50 });

  const isFetching =
    dashboard.isFetching ||
    revenue.isFetching ||
    applications.isFetching ||
    occupancy.isFetching;

  const retry = () => {
    void dashboard.refetch();
    void revenue.refetch();
    void applications.refetch();
    void occupancy.refetch();
  };

  const academicYearOptions = useMemo(() => {
    const list = years.data?.items ?? [];
    return [
      { value: "all", label: "Tất cả năm học" },
      ...list.map((y) => ({ value: y.id, label: `Năm học ${y.code}` })),
    ];
  }, [years.data]);

  if (dashboard.isLoading) {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-8 w-60" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {[1, 2, 3, 4, 5].map((item) => (
            <Skeleton key={item} className="h-28 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (
    dashboard.isError ||
    revenue.isError ||
    applications.isError ||
    occupancy.isError
  ) {
    return (
      <EmptyState
        icon={Receipt}
        title="Không thể tải báo cáo KTX"
        description="Đã xảy ra sự cố khi tải dữ liệu thống kê từ hệ thống. Vui lòng thử lại."
        action={{
          label: "Thử lại",
          onClick: retry,
        }}
      />
    );
  }

  const data = dashboard.data;
  const revenueData = revenue.data;
  const occupancyData = occupancy.data;
  const applicationData = applications.data;

  const collectionRate = Number(revenueData?.collectionRate ?? 0);

  return (
    <div className="space-y-6">
      {/* 1. Page Header */}
      <PageHeader
        eyebrow="KÝ TÚC XÁ / PHÂN TÍCH"
        title="Báo cáo thống kê"
        description="Tổng quan điều hành về sinh viên, tỷ lệ cư trú, hồ sơ xét duyệt và doanh thu tài chính KTX."
        actions={
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
            <span>Làm mới dữ liệu</span>
          </Button>
        }
      />

      {/* 2. Filter Toolbar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-muted-foreground">
          Dữ liệu thống kê và chỉ số tài chính được tổng hợp tự động theo thời
          gian thực.
        </p>

        <div className="flex items-center gap-2">
          <Combobox
            className="w-full sm:w-56 text-xs"
            options={academicYearOptions}
            value={academicYearId ?? "all"}
            searchPlaceholder="Tìm năm học..."
            onValueChange={(value) =>
              onAcademicYearChange(value === "all" ? undefined : value)
            }
          />

          {Boolean(academicYearId) && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground"
              onClick={() => onAcademicYearChange(undefined)}
            >
              <RotateCcw className="size-3.5 mr-1" />
              <span>Đặt lại</span>
            </Button>
          )}
        </div>
      </div>

      {/* 3. Top 5 KPI Metrics Card */}
      <Card className="overflow-hidden border bg-card shadow-xs">
        <CardContent className="grid p-0 sm:grid-cols-2 lg:grid-cols-5 divide-y sm:divide-y-0 sm:divide-x">
          <KpiMetric
            icon={Users}
            label="Sinh viên"
            value={(data?.totalStudents ?? 0).toLocaleString("vi-VN")}
            helper="Tổng sinh viên trong hệ thống"
          />
          <KpiMetric
            icon={Home}
            label="Đang cư trú"
            value={(data?.totalActiveResidences ?? 0).toLocaleString("vi-VN")}
            helper="Hợp đồng phòng đang hiệu lực"
          />
          <KpiMetric
            icon={Building2}
            label="Tỷ lệ sử dụng chỗ"
            value={`${Number(data?.placeOccupancyRate ?? 0).toFixed(1)}%`}
            helper="Tỷ lệ lấp đầy toàn bộ KTX"
          />
          <KpiMetric
            icon={ClipboardList}
            label="Hồ sơ đăng ký"
            value={(data?.totalApplications ?? 0).toLocaleString("vi-VN")}
            helper="Hồ sơ đăng ký đợt ở KTX"
          />
          <KpiMetric
            icon={Receipt}
            label="Còn phải thu"
            value={money(data?.totalOutstandingAmount ?? 0)}
            trend="negative"
            helper="Tổng tiền công nợ chưa thu"
          />
        </CardContent>
      </Card>

      {/* 4. Section: Revenue Breakdown & Application Status Breakdown */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Doanh thu & Công nợ */}
        <Card className="shadow-xs overflow-hidden border">
          <CardHeader className="border-b bg-muted/20 pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <PieChart className="size-4 text-muted-foreground" />
                <CardTitle className="text-base font-semibold">
                  Cơ cấu Doanh thu & Thu hồi
                </CardTitle>
              </div>
              <Badge variant="outline" className="font-mono text-xs">
                Thu {collectionRate.toFixed(1)}%
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="p-5 space-y-5">
            {/* Donut Chart */}
            <RevenueDonutChart revenue={revenueData} />

            {/* Metric Pills Grid */}
            <div className="grid grid-cols-2 gap-3 pt-2">
              <div className="rounded-lg border bg-muted/20 p-3">
                <span className="text-[11px] text-muted-foreground block">
                  Đã lập hóa đơn
                </span>
                <span className="mt-0.5 text-sm sm:text-base font-bold font-mono text-foreground block">
                  {money(revenueData?.totalInvoicedAmount ?? 0)}
                </span>
              </div>

              <div className="rounded-lg border bg-emerald-500/5 border-emerald-500/20 p-3">
                <span className="text-[11px] text-emerald-600 dark:text-emerald-400 block font-medium">
                  Đã thu thực tế
                </span>
                <span className="mt-0.5 text-sm sm:text-base font-bold font-mono text-emerald-600 dark:text-emerald-400 block">
                  {money(revenueData?.totalCollectedAmount ?? 0)}
                </span>
              </div>

              <div className="rounded-lg border bg-destructive/5 border-destructive/20 p-3">
                <span className="text-[11px] text-destructive block font-medium">
                  Còn phải thu (Nợ)
                </span>
                <span className="mt-0.5 text-sm sm:text-base font-bold font-mono text-destructive block">
                  {money(revenueData?.totalOutstandingAmount ?? 0)}
                </span>
              </div>

              <div className="rounded-lg border bg-muted/20 p-3">
                <span className="text-[11px] text-muted-foreground block">
                  Tỷ lệ hoàn thành
                </span>
                <div className="mt-0.5 flex items-center gap-1.5">
                  <span className="text-sm sm:text-base font-bold font-mono text-foreground">
                    {collectionRate.toFixed(1)}%
                  </span>
                  <CheckCircle2 className="size-3.5 text-emerald-600 dark:text-emerald-400" />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Hồ sơ theo trạng thái */}
        <Card className="shadow-xs overflow-hidden border">
          <CardHeader className="border-b bg-muted/20 pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <BarChart3 className="size-4 text-muted-foreground" />
                <CardTitle className="text-base font-semibold">
                  Phân bố Hồ sơ theo Trạng thái
                </CardTitle>
              </div>
              <Badge variant="outline" className="font-mono text-xs">
                {applicationData?.totalCount ?? 0} hồ sơ
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="p-5 space-y-4">
            {/* Horizontal Bar Chart */}
            <ApplicationStatusChart byStatus={applicationData?.byStatus} />

            {/* Status list with semantic dot pills */}
            <div className="divide-y border rounded-lg overflow-hidden bg-card">
              {Object.entries(applicationData?.byStatus ?? {}).map(
                ([status, count]) => {
                  const info = getApplicationStatusInfo(status);
                  return (
                    <div
                      key={status}
                      className="flex items-center justify-between px-3.5 py-2 text-xs hover:bg-muted/30 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className={cn("size-1.5 rounded-full", info.dot)}
                        />
                        <span className="font-medium text-foreground">
                          {info.label}
                        </span>
                      </div>
                      <Badge
                        variant={info.variant}
                        className="font-mono text-[11px] px-2 py-0"
                      >
                        {count} hồ sơ
                      </Badge>
                    </div>
                  );
                },
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 5. Section: Visual Building Occupancy & Multi-year Trends */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Biểu đồ So sánh Chỗ ở theo Tòa nhà */}
        <Card className="shadow-xs overflow-hidden border">
          <CardHeader className="border-b bg-muted/20 pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Building2 className="size-4 text-muted-foreground" />
                <CardTitle className="text-base font-semibold">
                  So sánh Chỗ ở theo Tòa nhà
                </CardTitle>
              </div>
              <Badge variant="outline" className="font-mono text-xs">
                {occupancyData?.byBuilding?.length ?? 0} tòa nhà
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="p-5">
            <BuildingOccupancyBarChart data={occupancyData?.byBuilding ?? []} />
          </CardContent>
        </Card>

        {/* Biểu đồ Xu hướng Hồ sơ qua các Năm học */}
        <Card className="shadow-xs overflow-hidden border">
          <CardHeader className="border-b bg-muted/20 pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <TrendingUp className="size-4 text-muted-foreground" />
                <CardTitle className="text-base font-semibold">
                  Xu hướng Hồ sơ qua các Năm học
                </CardTitle>
              </div>
              <Badge variant="outline" className="font-mono text-xs">
                Theo năm học
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="p-5">
            <ApplicationYearTrendChart
              byYear={applicationData?.byAcademicYear}
            />
          </CardContent>
        </Card>
      </div>

      {/* 6. Section: Occupancy Table Details */}
      <Card className="shadow-xs overflow-hidden border">
        <CardHeader className="border-b bg-muted/20 pb-3">
          <CardTitle className="text-base font-semibold">
            Chi tiết Lấp đầy từng Tòa nhà
          </CardTitle>
          <p className="text-xs text-muted-foreground mt-0.5">
            Bảng theo dõi số lượng phòng, tổng chỗ ở và tỷ lệ sử dụng thực tế
            của từng tòa nhà.
          </p>
        </CardHeader>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap min-w-[200px]">
                  Tòa nhà
                </TableHead>
                <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap text-right min-w-[120px]">
                  Tổng phòng
                </TableHead>
                <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap text-right min-w-[120px]">
                  Tổng chỗ
                </TableHead>
                <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap text-right min-w-[140px]">
                  Đã sử dụng
                </TableHead>
                <TableHead className="font-semibold text-xs text-muted-foreground uppercase tracking-wider py-3 whitespace-nowrap text-right min-w-[160px]">
                  Tỷ lệ lấp đầy
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(occupancyData?.byBuilding ?? []).map((building) => {
                const rate = Number(building.occupancyRate ?? 0);
                const rateBadgeVariant =
                  rate >= 80 ? "success" : rate >= 50 ? "warning" : "secondary";

                return (
                  <TableRow
                    key={building.buildingId}
                    className="hover:bg-muted/50 transition-colors whitespace-nowrap"
                  >
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="font-mono text-xs">
                          {building.buildingCode}
                        </Badge>
                        <span className="font-semibold text-foreground text-sm">
                          {building.buildingName}
                        </span>
                      </div>
                    </TableCell>

                    <TableCell className="text-right font-mono text-sm tabular-nums">
                      {building.totalRooms}
                    </TableCell>

                    <TableCell className="text-right font-mono text-sm tabular-nums">
                      {building.totalPlaces}
                    </TableCell>

                    <TableCell className="text-right font-mono font-semibold text-foreground text-sm tabular-nums">
                      {building.occupiedPlaces}
                    </TableCell>

                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2.5">
                        <div className="w-16 h-1.5 rounded-full bg-muted overflow-hidden hidden sm:block">
                          <div
                            className={cn(
                              "h-full rounded-full transition-all",
                              rate >= 80
                                ? "bg-emerald-500"
                                : rate >= 50
                                  ? "bg-amber-500"
                                  : "bg-muted-foreground",
                            )}
                            style={{
                              width: `${Math.min(100, Math.max(0, rate))}%`,
                            }}
                          />
                        </div>
                        <Badge
                          variant={rateBadgeVariant}
                          className="font-mono text-xs px-2 py-0.5 tabular-nums"
                        >
                          {rate.toFixed(1)}%
                        </Badge>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
              {(occupancyData?.byBuilding ?? []).length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={5}
                    className="py-12 text-center text-xs text-muted-foreground"
                  >
                    Chưa có dữ liệu thống kê tòa nhà.
                  </TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
        </div>
      </Card>
    </div>
  );
}
