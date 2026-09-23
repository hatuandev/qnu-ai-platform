import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/app/api/client";
import type {
  FeeRateInput,
  FeeRatesListParams,
  FeeRatesPage,
} from "@/features/fee-rates/types";

const path = "/FeeRates";

export const feeRatesQueryKeys = {
  all: ["fee-rates"] as const,
  list: (params: FeeRatesListParams) =>
    [...feeRatesQueryKeys.all, "list", params] as const,
};

export function useFeeRatesQuery(params: FeeRatesListParams) {
  return useQuery({
    queryKey: feeRatesQueryKeys.list(params),
    queryFn: () =>
      apiClient.get<FeeRatesPage>(path, {
        searchParams: {
          Search: params.search,
          AcademicYearId: params.academicYearId,
          RoomTypeId: params.roomTypeId,
          BuildingId: params.buildingId,
          FloorId: params.floorId,
          RoomId: params.roomId,
          IsActive: params.isActive,
          PageIndex: params.page,
          PageSize: params.pageSize,
        },
      }),
    placeholderData: (previous) => previous,
  });
}

function invalidate(client: ReturnType<typeof useQueryClient>) {
  void client.invalidateQueries({ queryKey: feeRatesQueryKeys.all });
  void client.invalidateQueries({ queryKey: ["invoices"] });
}

export function useCreateFeeRate() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: FeeRateInput) => apiClient.post<string>(path, input),
    onSuccess: () => invalidate(client),
  });
}

export function useUpdateFeeRate() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      input,
    }: {
      id: string;
      input: Omit<FeeRateInput, "academicYearId" | "roomTypeId" | "roomId">;
    }) => apiClient.put<void>(`${path}/${id}`, { id, ...input }),
    onSuccess: () => invalidate(client),
  });
}

export function useDeactivateFeeRate() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.put<void>(`${path}/${id}/deactivate`),
    onSuccess: () => invalidate(client),
  });
}

export function useDeleteFeeRate() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.delete<void>(`${path}/${id}`),
    onSuccess: () => invalidate(client),
  });
}

export function useDeleteFeeRatesBatch() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (feeRateIds: string[]) =>
      apiClient.post<void>(`${path}/batch-delete`, { feeRateIds }),
    onSuccess: () => invalidate(client),
  });
}
