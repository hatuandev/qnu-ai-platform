import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/app/api/client";
import type {
  DifficultAreasListParams,
  DifficultAreasPage,
  DifficultAreasStats,
} from "@/features/difficult-areas/types";

const path = "/AdministrativeAreas";

export const difficultAreasQueryKeys = {
  all: ["difficult-areas"] as const,
  list: (params: DifficultAreasListParams) =>
    [...difficultAreasQueryKeys.all, "list", params] as const,
  provinces: () => [...difficultAreasQueryKeys.all, "provinces"] as const,
  stats: () => [...difficultAreasQueryKeys.all, "stats"] as const,
};

export function useDifficultAreasQuery(params: DifficultAreasListParams) {
  return useQuery({
    queryKey: difficultAreasQueryKeys.list(params),
    queryFn: async () => {
      const response = await apiClient.get<DifficultAreasPage>(path, {
        searchParams: {
          Search: params.search,
          ProvinceName: params.provinceName,
          ProvinceCode: params.provinceCode,
          DivisionType: params.divisionType,
          IsWholeArea: params.isWholeArea,
          PageIndex: params.page,
          PageSize: params.pageSize,
        },
      });
      return response;
    },
    placeholderData: (previous) => previous,
  });
}

export function useDifficultAreaProvincesQuery() {
  return useQuery({
    queryKey: difficultAreasQueryKeys.provinces(),
    queryFn: async () => {
      const response = await apiClient.get<string[]>(`${path}/provinces`);
      return Array.isArray(response) ? response : [];
    },
    staleTime: 10 * 60 * 1000,
  });
}

export function useDifficultAreaStatsQuery() {
  return useQuery({
    queryKey: difficultAreasQueryKeys.stats(),
    queryFn: async () => {
      const response = await apiClient.get<DifficultAreasStats>(
        `${path}/stats`,
      );
      return response;
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateDifficultArea() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: import("./types").CreateDifficultAreaInput) => {
      return apiClient.post<import("./types").DifficultAreaItem>(path, payload);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: difficultAreasQueryKeys.all,
      });
    },
  });
}

export function useUpdateDifficultArea() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: string;
      payload: import("./types").UpdateDifficultAreaInput;
    }) => {
      return apiClient.put(`${path}/${id}`, payload);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: difficultAreasQueryKeys.all,
      });
    },
  });
}

export function useDeleteDifficultArea() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      return apiClient.delete(`${path}/${id}`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: difficultAreasQueryKeys.all,
      });
    },
  });
}

export function useBatchDeleteDifficultAreas() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (ids: string[]) => {
      return apiClient.post(`${path}/batch-delete`, { ids });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: difficultAreasQueryKeys.all,
      });
    },
  });
}
