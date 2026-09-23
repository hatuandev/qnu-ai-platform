import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/app/api/client";
import type {
  Building,
  BuildingsListParams,
  BuildingsPage,
  CreateBuildingInput,
  UpdateBuildingInput,
} from "@/features/buildings/types";

const buildingsPath = "/DormitoryBuildings";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isBuildingsPage(value: unknown): value is BuildingsPage {
  return (
    isRecord(value) &&
    Array.isArray(value.items) &&
    typeof value.total === "number" &&
    typeof value.page === "number" &&
    typeof value.pageSize === "number" &&
    typeof value.totalPages === "number"
  );
}

function isBuilding(value: unknown): value is Building {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.code === "string" &&
    typeof value.name === "string" &&
    typeof value.status === "string"
  );
}

export const buildingsQueryKeys = {
  all: ["buildings"] as const,
  list: (params: BuildingsListParams) =>
    [...buildingsQueryKeys.all, "list", params] as const,
  detail: (id: string) => [...buildingsQueryKeys.all, "detail", id] as const,
};

export function useBuildingsQuery(params: BuildingsListParams) {
  return useQuery({
    queryKey: buildingsQueryKeys.list(params),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(buildingsPath, {
        searchParams: {
          SearchCodeOrName: params.searchCodeOrName,
          Status: params.status,
          PageIndex: params.page,
          PageSize: params.pageSize,
        },
      });
      if (!isBuildingsPage(response)) {
        throw new Error("Phản hồi danh sách tòa nhà không đúng định dạng.");
      }
      return response;
    },
    placeholderData: (previous) => previous,
  });
}

export function useBuildingQuery(id: string) {
  return useQuery({
    queryKey: buildingsQueryKeys.detail(id),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(`${buildingsPath}/${id}`);
      if (!isBuilding(response)) {
        throw new Error("Phản hồi chi tiết tòa nhà không đúng định dạng.");
      }
      return response;
    },
    enabled: Boolean(id),
  });
}

export function useCreateBuilding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateBuildingInput) =>
      apiClient.post<string>(buildingsPath, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: buildingsQueryKeys.all });
    },
  });
}

export function useUpdateBuilding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: UpdateBuildingInput }) =>
      apiClient.put<void>(`${buildingsPath}/${id}`, { id, ...input }),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: buildingsQueryKeys.all });
      void queryClient.invalidateQueries({
        queryKey: buildingsQueryKeys.detail(variables.id),
      });
    },
  });
}

export function useDeactivateBuilding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.put<void>(`${buildingsPath}/${id}/deactivate`),
    onSuccess: (_data, id) => {
      void queryClient.invalidateQueries({ queryKey: buildingsQueryKeys.all });
      void queryClient.invalidateQueries({
        queryKey: buildingsQueryKeys.detail(id),
      });
    },
  });
}

export function useDeleteBuilding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete<void>(`${buildingsPath}/${id}`),
    onSuccess: (_data, id) => {
      void queryClient.invalidateQueries({ queryKey: buildingsQueryKeys.all });
      void queryClient.invalidateQueries({
        queryKey: buildingsQueryKeys.detail(id),
      });
    },
  });
}
