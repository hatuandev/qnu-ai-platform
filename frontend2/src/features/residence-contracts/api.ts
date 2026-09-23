import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/app/api/client";
import type {
  ResidenceContract,
  ResidenceContractDetail,
  ResidenceContractInput,
  ResidenceContractsListParams,
  ResidenceContractsPage,
  ResidenceContractUpdateInput,
} from "@/features/residence-contracts/types";

const path = "/ResidenceContracts";

export const residenceContractsQueryKeys = {
  all: ["residence-contracts"] as const,
  list: (params: ResidenceContractsListParams) =>
    [...residenceContractsQueryKeys.all, "list", params] as const,
  detail: (id: string) =>
    [...residenceContractsQueryKeys.all, "detail", id] as const,
};

export function useResidenceContractsQuery(
  params: ResidenceContractsListParams,
) {
  return useQuery({
    queryKey: residenceContractsQueryKeys.list(params),
    queryFn: () =>
      apiClient.get<ResidenceContractsPage>(path, {
        searchParams: {
          Search: params.search,
          Status: params.status,
          PageIndex: params.page,
          PageSize: params.pageSize,
        },
      }),
    placeholderData: (previous) => previous,
  });
}

export function useResidenceContractQuery(id: string) {
  return useQuery({
    queryKey: residenceContractsQueryKeys.detail(id),
    enabled: Boolean(id),
    queryFn: () => apiClient.get<ResidenceContractDetail>(`${path}/${id}`),
  });
}

function invalidate(client: ReturnType<typeof useQueryClient>, id?: string) {
  void client.invalidateQueries({
    queryKey: residenceContractsQueryKeys.all,
  });
  void client.invalidateQueries({ queryKey: ["residences"] });
  if (id) {
    void client.invalidateQueries({
      queryKey: residenceContractsQueryKeys.detail(id),
    });
  }
}

export function useCreateResidenceContract() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: ResidenceContractInput) =>
      apiClient.post<string>(path, input),
    onSuccess: () => invalidate(client),
  });
}

export function useUpdateResidenceContract() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      input,
    }: {
      id: string;
      input: ResidenceContractUpdateInput;
    }) => apiClient.put<void>(`${path}/${id}`, { id, ...input }),
    onSuccess: (_data, variables) => invalidate(client, variables.id),
  });
}

export function useSubmitResidenceContract() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.put<void>(`${path}/${id}/submit`, {}),
    onSuccess: (_data, id) => invalidate(client, id),
  });
}

export function useActivateResidenceContract() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.put<void>(`${path}/${id}/activate`, {}),
    onSuccess: (_data, id) => invalidate(client, id),
  });
}

export function useCancelResidenceContract() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.put<void>(`${path}/${id}/cancel`, {}),
    onSuccess: (_data, id) => invalidate(client, id),
  });
}

export const contractStatusLabels: Record<ResidenceContract["status"], string> =
  {
    draft: "Nháp",
    pending_signature: "Chờ ký",
    active: "Đang hiệu lực",
    cancelled: "Đã hủy",
  };

export const paymentPlanLabels: Record<string, string> = {
  one_time: "Một lần",
  monthly: "Hàng tháng",
};
