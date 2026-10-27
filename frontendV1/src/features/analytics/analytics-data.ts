import type { TimeRange } from "@/components/admin/time-range-select";
import { activityEvents } from "@/features/activity/data";
import type {
  AnalyticsData,
  AnalyticsPoint,
} from "@/features/analytics/analytics-types";
import { users } from "@/features/users/data";
import { demoRoles } from "@/rbac/demo";

const rangeLength: Record<TimeRange, number> = {
  "7d": 7,
  "30d": 30,
  "90d": 12,
  "1y": 12,
};
const activityPattern = [18, 24, 21, 29, 26, 34, 31, 38, 35, 42, 39, 47];

function makeTrend(range: TimeRange): AnalyticsPoint[] {
  const count = rangeLength[range];
  return Array.from({ length: count }, (_, index) => {
    const value =
      activityPattern[index % activityPattern.length] +
      Math.floor(index / 6) * 3;
    const date = new Date(
      2026,
      range === "1y" ? index : 7,
      range === "1y" ? 1 : index + 1,
    );
    const label =
      range === "1y"
        ? date.toLocaleDateString("vi-VN", { month: "short" })
        : date.toLocaleDateString("vi-VN", { day: "numeric", month: "short" });
    return {
      label,
      users: 92 + index * 4 + (index % 3) * 3,
      events: value,
      newUsers: 4 + (index % 5),
    };
  });
}

export function getAnalyticsData(range: TimeRange): AnalyticsData {
  const categoryCounts = new Map<string, number>([
    ["users", 0],
    ["roles", 0],
    ["settings", 0],
    ["security", 0],
  ]);
  for (const event of activityEvents)
    categoryCounts.set(
      event.resource,
      (categoryCounts.get(event.resource) ?? 0) + 1,
    );
  return {
    range,
    trend: makeTrend(range),
    categories: [
      { label: "Người dùng", value: categoryCounts.get("users") ?? 0 },
      { label: "Vai trò", value: categoryCounts.get("roles") ?? 0 },
      { label: "Cài đặt", value: categoryCounts.get("settings") ?? 0 },
      { label: "Bảo mật", value: categoryCounts.get("security") ?? 0 },
    ],
    roleDistribution: demoRoles.map((role) => ({
      label: role.name,
      value: users.filter((user) => user.role === role.name).length,
    })),
  };
}

export function getDashboardMetrics() {
  const activeUsers = users.filter((user) => user.status === "active").length;
  return {
    totalUsers: users.length,
    activeUsers,
    activeRate: Math.round((activeUsers / users.length) * 100),
    roles: demoRoles.length,
    events: activityEvents.length,
  };
}

export function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}
