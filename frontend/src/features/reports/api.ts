import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/app/api/client";
import type {
  ApplicationStats,
  DashboardStats,
  RevenueStats,
  RoomOccupancyStats,
} from "@/features/reports/types";
export const reportQueryKeys = {
  all: ["reports"] as const,
  dashboard: () => [...reportQueryKeys.all, "dashboard"] as const,
  applications: (params: object) =>
    [...reportQueryKeys.all, "applications", params] as const,
  occupancy: (params: object) =>
    [...reportQueryKeys.all, "occupancy", params] as const,
  revenue: (params: object) =>
    [...reportQueryKeys.all, "revenue", params] as const,
};
export function useDashboardStatsQuery() {
  return useQuery({
    queryKey: reportQueryKeys.dashboard(),
    queryFn: () => apiClient.get<DashboardStats>("/Reports/dashboard"),
  });
}
export function useApplicationStatsQuery(params: {
  status?: string;
  academicYearId?: string;
  fromDate?: string;
  toDate?: string;
}) {
  return useQuery({
    queryKey: reportQueryKeys.applications(params),
    queryFn: () =>
      apiClient.get<ApplicationStats>("/Reports/applications", {
        searchParams: {
          Status: params.status,
          AcademicYearId: params.academicYearId,
          FromDate: params.fromDate,
          ToDate: params.toDate,
        },
      }),
  });
}
export function useRoomOccupancyQuery(params: {
  buildingId?: string;
  floorId?: string;
}) {
  return useQuery({
    queryKey: reportQueryKeys.occupancy(params),
    queryFn: () =>
      apiClient.get<RoomOccupancyStats>("/Reports/room-occupancy", {
        searchParams: {
          BuildingId: params.buildingId,
          FloorId: params.floorId,
        },
      }),
  });
}
export function useRevenueStatsQuery(params: {
  academicYearId?: string;
  fromDate?: string;
  toDate?: string;
}) {
  return useQuery({
    queryKey: reportQueryKeys.revenue(params),
    queryFn: () =>
      apiClient.get<RevenueStats>("/Reports/revenue", {
        searchParams: {
          AcademicYearId: params.academicYearId,
          FromDate: params.fromDate,
          ToDate: params.toDate,
        },
      }),
  });
}
