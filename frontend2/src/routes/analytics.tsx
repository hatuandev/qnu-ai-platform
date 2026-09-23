import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Activity, ShieldCheck, UserCheck, Users } from "lucide-react";
import { z } from "zod";
import { AccessDenied } from "@/components/admin/access-denied";
import {
  ChartCard,
  ChartEmpty,
  ChartError,
  ChartLoading,
} from "@/components/admin/chart-card";
import { KpiMetric } from "@/components/admin/kpi-metric";
import { PageHeader } from "@/components/admin/page-header";
import {
  TimeRangeSelect,
  timeRangeValues,
} from "@/components/admin/time-range-select";
import {
  formatNumber,
  getAnalyticsData,
  getDashboardMetrics,
} from "@/features/analytics/analytics-data";
import {
  ActivityTrendChart,
  CategoryChart,
  RoleDistributionChart,
  UserGrowthChart,
} from "@/features/analytics/charts";
import { useRbac } from "@/rbac/context";

const searchSchema = z.object({ range: z.enum(timeRangeValues).catch("30d") });

export const Route = createFileRoute("/analytics")({
  validateSearch: (search) => searchSchema.parse(search),
  component: AnalyticsPage,
});

function AnalyticsPage() {
  const { can } = useRbac();
  const search = Route.useSearch();
  const navigate = useNavigate({ from: "/analytics" });
  const data = getAnalyticsData(search.range);
  const metrics = getDashboardMetrics();
  const updateRange = (range: typeof search.range) =>
    void navigate({ search: { range } });
  const isLoading = false;
  const isError = false;
  if (!can("analytics.read")) return <AccessDenied />;
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Quản trị / Giám sát"
        title="Phân tích"
        description="Khám phá mức sử dụng và xu hướng hoạt động của workspace."
        actions={
          <TimeRangeSelect value={search.range} onChange={updateRange} />
        }
      />
      <section
        aria-label="Chỉ số phân tích"
        className="grid overflow-hidden rounded-lg border bg-card sm:grid-cols-2 xl:grid-cols-4"
      >
        <KpiMetric
          label="Tổng số người dùng"
          value={formatNumber(metrics.totalUsers)}
          delta="+8.2%"
          trend="positive"
          helper="so với kỳ trước"
          icon={Users}
        />
        <div className="border-t sm:border-t-0 sm:border-l">
          <KpiMetric
            label="Tỷ lệ hoạt động"
            value={`${metrics.activeRate}%`}
            delta="+5.1%"
            trend="positive"
            helper="người dùng hoạt động"
            icon={UserCheck}
          />
        </div>
        <div className="border-t sm:border-t-0 sm:border-l xl:border-l">
          <KpiMetric
            label="Sự kiện"
            value={formatNumber(metrics.events)}
            delta="+12.4%"
            trend="positive"
            helper="sự kiện quản trị"
            icon={Activity}
          />
        </div>
        <div className="border-t sm:border-t-0 sm:border-l">
          <KpiMetric
            label="Vai trò"
            value={formatNumber(metrics.roles)}
            delta="Ổn định"
            trend="neutral"
            helper="trong catalog demo"
            icon={ShieldCheck}
          />
        </div>
      </section>
      <ChartCard
        title="Xu hướng hoạt động"
        description={`Tổng số sự kiện theo ${search.range === "1y" ? "tháng" : "ngày"}`}
      >
        {isLoading ? (
          <ChartLoading />
        ) : isError ? (
          <ChartError />
        ) : (
          <div className="h-[240px] p-3 sm:h-[320px] sm:p-5">
            {data.trend.length ? (
              <ActivityTrendChart data={data.trend} />
            ) : (
              <ChartEmpty />
            )}
          </div>
        )}
      </ChartCard>
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard
          title="Tăng trưởng người dùng"
          description="Tổng người dùng và người dùng mới trong kỳ đã chọn."
        >
          <div className="h-[240px] p-3 sm:h-[300px] sm:p-5">
            <UserGrowthChart data={data.trend} />
          </div>
        </ChartCard>
        <ChartCard
          title="Hoạt động theo nhóm"
          description="So sánh số sự kiện theo resource."
        >
          <div className="h-[240px] p-3 sm:h-[300px] sm:p-5">
            <CategoryChart data={data.categories} />
          </div>
        </ChartCard>
      </div>
      <ChartCard
        title="Phân bổ người dùng theo vai trò"
        description="Số người dùng hiện tại trên các vai trò trong demo catalog."
      >
        <div className="h-[240px] p-3 sm:h-[300px] sm:p-5">
          <RoleDistributionChart data={data.roleDistribution} />
        </div>
      </ChartCard>
    </div>
  );
}
