import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DailyTrendItem } from "@/features/reports/types";

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
    fontSize: 13,
  },
  labelStyle: { color: "var(--popover-foreground)", fontWeight: 600 },
  itemStyle: { color: "var(--popover-foreground)" },
  cursor: { stroke: "var(--border)" },
};

type DashboardTrendChartProps = {
  data?: DailyTrendItem[];
};

export function DashboardTrendChart({ data = [] }: DashboardTrendChartProps) {
  const chartData = data.map((item) => ({
    label: item.label,
    applications: item.count,
  }));

  if (chartData.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
        Chưa có dữ liệu biến động hồ sơ trong 30 ngày qua.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart
        accessibilityLayer
        data={chartData}
        margin={{ top: 12, right: 8, left: -16, bottom: 0 }}
      >
        <defs>
          <linearGradient id="dashboard-trend-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.22} />
            <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid
          vertical={false}
          stroke="var(--border)"
          strokeDasharray="3 3"
        />
        <XAxis dataKey="label" interval="preserveStartEnd" {...axisProps} />
        <YAxis {...axisProps} width={38} allowDecimals={false} />
        <Tooltip
          {...tooltipProps}
          formatter={(value) => [`${value} hồ sơ`, "Số lượng"]}
        />
        <Area
          type="monotone"
          dataKey="applications"
          name="Hồ sơ đăng ký"
          stroke="var(--chart-1)"
          strokeWidth={2}
          fill="url(#dashboard-trend-fill)"
          activeDot={{ r: 4, fill: "var(--chart-1)" }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
