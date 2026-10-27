import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartEmpty } from "@/components/admin/chart-card";
import { applicationStatusLabels } from "@/features/applications/types";
import { invoiceStatusLabels } from "@/features/invoices/types";
import type { RoomOccupancyStats } from "@/features/reports/types";

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
  cursor: { fill: "var(--muted)" },
};

type StatusChartProps = {
  data: Record<string, number>;
};

function StatusChart({
  data,
  labels,
  color,
  name,
  emptyTitle,
  compact,
}: StatusChartProps & {
  labels: Record<string, string>;
  color: string;
  name: string;
  emptyTitle: string;
  compact?: boolean;
}) {
  const chartData = Object.entries(data)
    .filter(([, value]) => value > 0)
    .map(([status, value]) => ({
      label: labels[status] ?? status,
      value,
    }));

  if (chartData.length === 0) {
    return <ChartEmpty title={emptyTitle} compact={compact} />;
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        accessibilityLayer
        data={chartData}
        layout="vertical"
        margin={{ top: 8, right: 16, left: 0, bottom: 8 }}
      >
        <CartesianGrid
          horizontal={false}
          stroke="var(--border)"
          strokeDasharray="3 3"
        />
        <XAxis
          type="number"
          allowDecimals={false}
          axisLine={false}
          tickLine={false}
          tick={axisProps.tick}
        />
        <YAxis
          type="category"
          dataKey="label"
          width={132}
          axisLine={false}
          tickLine={false}
          tick={axisProps.tick}
        />
        <Tooltip {...tooltipProps} formatter={(value) => [value, name]} />
        <Bar
          dataKey="value"
          name={name}
          fill={color}
          radius={[0, 4, 4, 0]}
          maxBarSize={28}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function BuildingOccupancyChart({
  data,
}: {
  data: RoomOccupancyStats["byBuilding"];
}) {
  if (data.length === 0) {
    return <ChartEmpty title="Chưa có dữ liệu tòa nhà" compact />;
  }

  const chartData = data.map((building) => ({
    label: `${building.buildingCode} · ${building.buildingName}`,
    occupancyRate: Number(building.occupancyRate),
  }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        accessibilityLayer
        data={chartData}
        layout="vertical"
        margin={{ top: 8, right: 16, left: 0, bottom: 8 }}
      >
        <CartesianGrid
          horizontal={false}
          stroke="var(--border)"
          strokeDasharray="3 3"
        />
        <XAxis
          type="number"
          domain={[0, 100]}
          tickFormatter={(value) => `${value}%`}
          {...axisProps}
        />
        <YAxis type="category" dataKey="label" width={132} {...axisProps} />
        <Tooltip
          {...tooltipProps}
          formatter={(value) => [`${Number(value).toFixed(1)}%`, "Lấp đầy"]}
        />
        <Bar
          dataKey="occupancyRate"
          name="Tỷ lệ lấp đầy"
          fill="var(--chart-2)"
          radius={[0, 4, 4, 0]}
          maxBarSize={28}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ApplicationStatusChart({ data }: StatusChartProps) {
  return (
    <StatusChart
      data={data}
      labels={applicationStatusLabels}
      color="var(--chart-3)"
      name="Hồ sơ"
      emptyTitle="Chưa có hồ sơ đăng ký"
      compact
    />
  );
}

export function InvoiceStatusChart({ data }: StatusChartProps) {
  return (
    <StatusChart
      data={data}
      labels={invoiceStatusLabels}
      color="var(--chart-4)"
      name="Hóa đơn"
      emptyTitle="Chưa có hóa đơn"
      compact
    />
  );
}
