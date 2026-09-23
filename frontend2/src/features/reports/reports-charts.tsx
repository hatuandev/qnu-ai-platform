import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { money } from "@/features/invoices/invoices-page";
import type {
  ApplicationStats,
  RevenueStats,
  RoomOccupancyStats,
} from "@/features/reports/types";

const axisProps = {
  tick: { fill: "var(--muted-foreground)", fontSize: 12 },
  axisLine: false,
  tickLine: false,
};

const tooltipProps = {
  contentStyle: {
    background: "var(--popover)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius)",
    color: "var(--popover-foreground)",
    fontSize: 12,
    boxShadow: "0 4px 12px rgba(0, 0, 0, 0.1)",
  },
  labelStyle: { color: "var(--popover-foreground)", fontWeight: 600 },
  itemStyle: { color: "var(--popover-foreground)" },
  cursor: { fill: "var(--muted)", opacity: 0.4 },
};

/* -------------------------------------------------------------------------- */
/* 1. Building Occupancy Bar Chart (Grouped Bar Chart)                        */
/* -------------------------------------------------------------------------- */
export function BuildingOccupancyBarChart({
  data,
}: {
  data: RoomOccupancyStats["byBuilding"];
}) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-xs text-muted-foreground">
        Chưa có dữ liệu tòa nhà
      </div>
    );
  }

  const chartData = data.map((b) => ({
    name: b.buildingCode,
    fullName: `${b.buildingCode} - ${b.buildingName}`,
    "Đã sử dụng": b.occupiedPlaces,
    "Tổng số chỗ": b.totalPlaces,
    "Còn trống": Math.max(0, b.totalPlaces - b.occupiedPlaces),
    occupancyRate: b.occupancyRate,
  }));

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          accessibilityLayer
          data={chartData}
          margin={{ top: 16, right: 16, left: -16, bottom: 8 }}
        >
          <CartesianGrid
            vertical={false}
            stroke="var(--border)"
            strokeDasharray="3 3"
          />
          <XAxis dataKey="name" {...axisProps} />
          <YAxis {...axisProps} width={45} allowDecimals={false} />
          <Tooltip
            {...tooltipProps}
            formatter={(value, name) => [
              `${value} chỗ`,
              name === "Đã sử dụng" ? "Đang ở" : "Tổng chỗ",
            ]}
            labelFormatter={(label) => {
              const item = chartData.find((d) => d.name === label);
              return item
                ? `${item.fullName} (Lấp đầy ${Number(item.occupancyRate).toFixed(1)}%)`
                : label;
            }}
          />
          <Legend
            verticalAlign="top"
            align="right"
            iconType="circle"
            wrapperStyle={{ paddingBottom: 12, fontSize: 12 }}
          />
          <Bar
            dataKey="Đã sử dụng"
            fill="var(--chart-1, #2563eb)"
            radius={[4, 4, 0, 0]}
            maxBarSize={32}
          />
          <Bar
            dataKey="Tổng số chỗ"
            fill="var(--muted-foreground, #94a3b8)"
            opacity={0.35}
            radius={[4, 4, 0, 0]}
            maxBarSize={32}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* 2. Revenue Donut Chart                                                     */
/* -------------------------------------------------------------------------- */
const REVENUE_COLORS = {
  collected: "#10b981", // Emerald
  outstanding: "#ef4444", // Red
  voided: "#94a3b8", // Slate
};

export function RevenueDonutChart({
  revenue,
}: {
  revenue?: RevenueStats | null;
}) {
  const collected = revenue?.totalCollectedAmount ?? 0;
  const outstanding = revenue?.totalOutstandingAmount ?? 0;
  const voided = revenue?.totalVoidedAmount ?? 0;
  const total = collected + outstanding + voided;

  if (!revenue || total === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-xs text-muted-foreground">
        Chưa có dữ liệu tài chính
      </div>
    );
  }

  const chartData = [
    { name: "Đã thu", value: collected, color: REVENUE_COLORS.collected },
    {
      name: "Còn phải thu",
      value: outstanding,
      color: REVENUE_COLORS.outstanding,
    },
    ...(voided > 0
      ? [{ name: "Đã hủy", value: voided, color: REVENUE_COLORS.voided }]
      : []),
  ].filter((item) => item.value > 0);

  const collectionRate = Number(revenue.collectionRate ?? 0);

  return (
    <div className="relative flex flex-col items-center justify-center">
      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip
              {...tooltipProps}
              formatter={(val) => [money(Number(val)), ""]}
            />
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={58}
              outerRadius={84}
              paddingAngle={3}
              dataKey="value"
            >
              {chartData.map((entry) => (
                <Cell
                  key={entry.name}
                  fill={entry.color}
                  stroke="transparent"
                />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Center Percentage Display */}
      <div className="pointer-events-none absolute top-[90px] flex flex-col items-center justify-center text-center">
        <span className="text-2xl font-bold font-mono text-foreground tracking-tight">
          {collectionRate.toFixed(0)}%
        </span>
        <span className="text-[11px] text-muted-foreground font-medium">
          Tỷ lệ thu
        </span>
      </div>

      {/* Custom Legend */}
      <div className="mt-2 flex flex-wrap items-center justify-center gap-4 text-xs">
        <div className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full bg-emerald-500" />
          <span className="text-muted-foreground">Đã thu:</span>
          <span className="font-semibold font-mono text-emerald-600 dark:text-emerald-400">
            {money(collected)}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full bg-red-500" />
          <span className="text-muted-foreground">Còn nợ:</span>
          <span className="font-semibold font-mono text-destructive">
            {money(outstanding)}
          </span>
        </div>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* 3. Application Status Horizontal Bar Chart                                  */
/* -------------------------------------------------------------------------- */
const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  Approved: { label: "Đã duyệt", color: "#10b981" },
  UnderReview: { label: "Đang xét duyệt", color: "#3b82f6" },
  Submitted: { label: "Đã nộp", color: "#f59e0b" },
  NeedsSupplement: { label: "Yêu cầu bổ sung", color: "#a855f7" },
  Rejected: { label: "Từ chối", color: "#ef4444" },
  Cancelled: { label: "Đã hủy", color: "#64748b" },
  Draft: { label: "Nháp", color: "#94a3b8" },
};

export function ApplicationStatusChart({
  byStatus,
}: {
  byStatus?: ApplicationStats["byStatus"];
}) {
  if (!byStatus || Object.keys(byStatus).length === 0) {
    return (
      <div className="flex h-56 items-center justify-center text-xs text-muted-foreground">
        Chưa có dữ liệu hồ sơ
      </div>
    );
  }

  const chartData = Object.entries(byStatus)
    .filter(([, count]) => count > 0)
    .map(([status, count]) => {
      const config = STATUS_LABELS[status] ?? {
        label: status,
        color: "#64748b",
      };
      return {
        status,
        label: config.label,
        count,
        color: config.color,
      };
    });

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          accessibilityLayer
          data={chartData}
          layout="vertical"
          margin={{ top: 8, right: 24, left: 8, bottom: 8 }}
        >
          <CartesianGrid
            horizontal={false}
            stroke="var(--border)"
            strokeDasharray="3 3"
          />
          <XAxis type="number" allowDecimals={false} {...axisProps} />
          <YAxis type="category" dataKey="label" width={110} {...axisProps} />
          <Tooltip
            {...tooltipProps}
            formatter={(value) => [`${value} hồ sơ`, "Số lượng"]}
          />
          <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={20}>
            {chartData.map((entry) => (
              <Cell key={entry.status} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* 4. Application Academic Year Trend Area Chart                              */
/* -------------------------------------------------------------------------- */
export function ApplicationYearTrendChart({
  byYear,
}: {
  byYear?: Record<string, number>;
}) {
  if (!byYear || Object.keys(byYear).length === 0) {
    return (
      <div className="flex h-56 items-center justify-center text-xs text-muted-foreground">
        Chưa có dữ liệu qua các năm học
      </div>
    );
  }

  const chartData = Object.entries(byYear).map(([year, count]) => ({
    year,
    "Hồ sơ": count,
  }));

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          accessibilityLayer
          data={chartData}
          margin={{ top: 12, right: 16, left: -16, bottom: 0 }}
        >
          <defs>
            <linearGradient id="year-trend-fill" x1="0" y1="0" x2="0" y2="1">
              <stop
                offset="0%"
                stopColor="var(--chart-1, #2563eb)"
                stopOpacity={0.25}
              />
              <stop
                offset="100%"
                stopColor="var(--chart-1, #2563eb)"
                stopOpacity={0.02}
              />
            </linearGradient>
          </defs>
          <CartesianGrid
            vertical={false}
            stroke="var(--border)"
            strokeDasharray="3 3"
          />
          <XAxis dataKey="year" {...axisProps} />
          <YAxis {...axisProps} width={45} allowDecimals={false} />
          <Tooltip
            {...tooltipProps}
            formatter={(value) => [`${value} hồ sơ`, "Số lượng"]}
          />
          <Area
            type="monotone"
            dataKey="Hồ sơ"
            stroke="var(--chart-1, #2563eb)"
            strokeWidth={2.5}
            fill="url(#year-trend-fill)"
            activeDot={{ r: 5, fill: "var(--chart-1, #2563eb)" }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
