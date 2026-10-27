import type { TimeRange } from "@/components/admin/time-range-select";

export type AnalyticsPoint = {
  label: string;
  users: number;
  events: number;
  newUsers: number;
};
export type AnalyticsCategory = { label: string; value: number };
export type AnalyticsRole = { label: string; value: number };
export type AnalyticsData = {
  range: TimeRange;
  trend: AnalyticsPoint[];
  categories: AnalyticsCategory[];
  roleDistribution: AnalyticsRole[];
};
