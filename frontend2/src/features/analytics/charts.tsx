import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type {
  AnalyticsCategory,
  AnalyticsPoint,
  AnalyticsRole,
} from "@/features/analytics/analytics-types";

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

export function ActivityTrendChart({
  data,
  compact = false,
}: {
  data: AnalyticsPoint[];
  compact?: boolean;
}) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart
        accessibilityLayer
        data={data}
        margin={{ top: 12, right: 8, left: -16, bottom: 0 }}
      >
        <defs>
          <linearGradient id="activity-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.22} />
            <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid
          vertical={false}
          stroke="var(--border)"
          strokeDasharray="3 3"
        />
        <XAxis
          dataKey="label"
          interval={compact || data.length > 14 ? "preserveStartEnd" : 0}
          {...axisProps}
        />
        <YAxis {...axisProps} width={38} />
        <Tooltip {...tooltipProps} />
        <Area
          type="monotone"
          dataKey="events"
          name="Sự kiện"
          stroke="var(--chart-1)"
          strokeWidth={2}
          fill="url(#activity-fill)"
          activeDot={{ r: 4, fill: "var(--chart-1)" }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function UserGrowthChart({ data }: { data: AnalyticsPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart
        accessibilityLayer
        data={data}
        margin={{ top: 12, right: 8, left: -16, bottom: 0 }}
      >
        <CartesianGrid
          vertical={false}
          stroke="var(--border)"
          strokeDasharray="3 3"
        />
        <XAxis dataKey="label" interval="preserveStartEnd" {...axisProps} />
        <YAxis {...axisProps} width={38} />
        <Tooltip {...tooltipProps} />
        <Legend
          wrapperStyle={{ fontSize: 12, color: "var(--muted-foreground)" }}
        />
        <Line
          type="monotone"
          dataKey="users"
          name="Tổng người dùng"
          stroke="var(--chart-2)"
          strokeWidth={2}
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="newUsers"
          name="Người dùng mới"
          stroke="var(--chart-3)"
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function CategoryChart({ data }: { data: AnalyticsCategory[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        accessibilityLayer
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 16, left: 8, bottom: 0 }}
      >
        <CartesianGrid
          horizontal={false}
          stroke="var(--border)"
          strokeDasharray="3 3"
        />
        <XAxis type="number" allowDecimals={false} {...axisProps} />
        <YAxis type="category" dataKey="label" width={72} {...axisProps} />
        <Tooltip {...tooltipProps} />
        <Bar
          dataKey="value"
          name="Sự kiện"
          fill="var(--chart-2)"
          radius={[0, 4, 4, 0]}
          barSize={20}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function RoleDistributionChart({ data }: { data: AnalyticsRole[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        accessibilityLayer
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 16, left: 8, bottom: 0 }}
      >
        <CartesianGrid
          horizontal={false}
          stroke="var(--border)"
          strokeDasharray="3 3"
        />
        <XAxis type="number" allowDecimals={false} {...axisProps} />
        <YAxis type="category" dataKey="label" width={86} {...axisProps} />
        <Tooltip {...tooltipProps} />
        <Bar
          dataKey="value"
          name="Người dùng"
          fill="var(--chart-4)"
          radius={[0, 4, 4, 0]}
          barSize={22}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
