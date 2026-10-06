import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/app/api/client";
import type {
  AdministrativeAreaListParams,
  AdministrativeAreaPage,
  CreatePriorityObjectInput,
  PriorityObject,
  PriorityObjectEligibleAreaDto,
  PriorityObjectEligibleAreaListParams,
  PriorityObjectEligibleAreasPage,
  PriorityObjectsListParams,
  PriorityObjectsPage,
  UpdatePriorityObjectInput,
} from "@/features/priority-objects/types";

const path = "/PriorityObjects";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isPriorityObject(value: unknown): value is PriorityObject {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.code === "string" &&
    typeof value.name === "string" &&
    typeof value.score === "number" &&
    (value.description === null ||
      value.description === undefined ||
      typeof value.description === "string") &&
    typeof value.isActive === "boolean" &&
    typeof value.created === "string" &&
    typeof value.lastModified === "string"
  );
}

function isPriorityObjectsPage(value: unknown): value is PriorityObjectsPage {
  return (
    isRecord(value) &&
    Array.isArray(value.items) &&
    value.items.every(isPriorityObject) &&
    typeof value.total === "number" &&
    typeof value.page === "number" &&
    typeof value.pageSize === "number" &&
    typeof value.totalPages === "number"
  );
}

function isPriorityObjectEligibleAreaDto(
  value: unknown,
): value is PriorityObjectEligibleAreaDto {
  return (
    isRecord(value) &&
    typeof value.priorityObjectId === "string" &&
    typeof value.administrativeAreaId === "string" &&
    typeof value.externalCode === "string" &&
    typeof value.name === "string"
  );
}

function isEligibleAreasPage(
  value: unknown,
): value is PriorityObjectEligibleAreasPage {
  return (
    isRecord(value) &&
    Array.isArray(value.items) &&
    value.items.every(isPriorityObjectEligibleAreaDto) &&
    typeof value.total === "number" &&
    typeof value.page === "number" &&
    typeof value.pageSize === "number" &&
    typeof value.totalPages === "number"
  );
}

function isAdministrativeArea(
  value: unknown,
): value is AdministrativeAreaPage["items"][number] {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.externalCode === "string" &&
    typeof value.name === "string"
  );
}

function isAdministrativeAreaPage(
  value: unknown,
): value is AdministrativeAreaPage {
  return (
    isRecord(value) &&
    Array.isArray(value.items) &&
    value.items.every(isAdministrativeArea) &&
    typeof value.total === "number" &&
    typeof value.page === "number" &&
    typeof value.pageSize === "number" &&
    typeof value.totalPages === "number"
  );
}

export const priorityObjectsQueryKeys = {
  all: ["priority-objects"] as const,
  list: (params: PriorityObjectsListParams) =>
    [...priorityObjectsQueryKeys.all, "list", params] as const,
  eligibleAreas: (
    priorityObjectId: string,
    params: PriorityObjectEligibleAreaListParams,
  ) =>
    [
      ...priorityObjectsQueryKeys.all,
      "eligible-areas",
      priorityObjectId,
      params,
    ] as const,
  provinces: (priorityObjectId: string) =>
    [...priorityObjectsQueryKeys.all, "provinces", priorityObjectId] as const,
  administrativeAreas: ["administrative-areas"] as const,
};

export function usePriorityObjectsQuery(params: PriorityObjectsListParams) {
  return useQuery({
    queryKey: priorityObjectsQueryKeys.list(params),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(path, {
        searchParams: {
          SearchCodeOrName: params.searchCodeOrName,
          VerificationType: params.verificationType,
          IsActive: params.isActive,
          PageIndex: params.page,
          PageSize: params.pageSize,
        },
      });
      if (!isPriorityObjectsPage(response)) {
        throw new Error(
          "Phản hồi danh sách đối tượng ưu tiên không đúng định dạng.",
        );
      }
      return response;
    },
    placeholderData: (previous) => previous,
  });
}

export function usePriorityObjectProvincesQuery(priorityObjectId: string) {
  return useQuery({
    queryKey: priorityObjectsQueryKeys.provinces(priorityObjectId),
    queryFn: async () => {
      const response = await apiClient.get<string[]>(
        `${path}/${priorityObjectId}/provinces`,
      );
      if (!Array.isArray(response)) {
        return [];
      }
      return response;
    },
    enabled: Boolean(priorityObjectId),
    staleTime: 5 * 60 * 1000, // cache for 5 minutes
  });
}

export function useEligibleAreasQuery(
  priorityObjectId: string,
  params: PriorityObjectEligibleAreaListParams,
) {
  return useQuery({
    queryKey: priorityObjectsQueryKeys.eligibleAreas(priorityObjectId, params),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(
        `${path}/${priorityObjectId}/eligible-areas`,
        {
          searchParams: {
            Search: params.search,
            ProvinceName: params.provinceName,
            IsActive: params.isActive,
            PageIndex: params.page,
            PageSize: params.pageSize,
          },
        },
      );
      if (!isEligibleAreasPage(response)) {
        throw new Error(
          "Phản hồi danh sách địa bàn đủ điều kiện không đúng định dạng.",
        );
      }
      return response;
    },
    enabled: Boolean(priorityObjectId),
    placeholderData: (previous) => previous,
  });
}

export function useAdministrativeAreasQuery(
  params: AdministrativeAreaListParams,
) {
  return useQuery({
    queryKey: [
      ...priorityObjectsQueryKeys.administrativeAreas,
      params,
    ] as const,
    queryFn: async () => {
      const response = await apiClient.get<unknown>("/AdministrativeAreas", {
        searchParams: {
          Search: params.search,
          ProvinceCode: params.provinceCode,
          DivisionType: params.divisionType,
          PageIndex: params.page,
          PageSize: params.pageSize,
        },
      });
      if (!isAdministrativeAreaPage(response)) {
        throw new Error(
          "Phản hồi danh sách đơn vị hành chính không đúng định dạng.",
        );
      }
      return response;
    },
    placeholderData: (previous) => previous,
  });
}

function invalidate(client: ReturnType<typeof useQueryClient>) {
  void client.invalidateQueries({ queryKey: priorityObjectsQueryKeys.all });
  void client.invalidateQueries({ queryKey: ["student"] });
}

function invalidateEligibleAreas(
  client: ReturnType<typeof useQueryClient>,
  priorityObjectId: string,
) {
  void client.invalidateQueries({
    queryKey: [
      ...priorityObjectsQueryKeys.all,
      "eligible-areas",
      priorityObjectId,
    ],
  });
  void client.invalidateQueries({
    queryKey: priorityObjectsQueryKeys.list({ page: 1, pageSize: 1 }),
  });
  invalidate(client);
}

export function useCreatePriorityObject() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: CreatePriorityObjectInput) =>
      apiClient.post<string>(path, input),
    onSuccess: () => invalidate(client),
  });
}

export function useUpdatePriorityObject() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      input,
    }: {
      id: string;
      input: UpdatePriorityObjectInput;
    }) => apiClient.put<void>(`${path}/${id}`, { id, ...input }),
    onSuccess: (_data, variables) => {
      invalidateEligibleAreas(client, variables.id);
    },
  });
}

export function useDeactivatePriorityObject() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.put<void>(`${path}/${id}/deactivate`),
    onSuccess: () => invalidate(client),
  });
}

export function useDeletePriorityObject() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.delete<void>(`${path}/${id}`),
    onSuccess: () => invalidate(client),
  });
}

export function useDeletePriorityObjectsBatch() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (priorityObjectIds: string[]) =>
      apiClient.post<void>(`${path}/batch-delete`, { priorityObjectIds }),
    onSuccess: () => invalidate(client),
  });
}

export function useAddEligibleAreaMutation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      priorityObjectId,
      administrativeAreaId,
    }: {
      priorityObjectId: string;
      administrativeAreaId: string;
    }) =>
      apiClient.post<void>(`${path}/${priorityObjectId}/eligible-areas`, {
        administrativeAreaId,
      }),
    onSuccess: (_data, variables) => {
      invalidateEligibleAreas(client, variables.priorityObjectId);
    },
  });
}

export function useRemoveEligibleAreaMutation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      priorityObjectId,
      administrativeAreaId,
      hardDelete,
    }: {
      priorityObjectId: string;
      administrativeAreaId: string;
      hardDelete?: boolean;
    }) =>
      apiClient.delete<void>(
        `${path}/${priorityObjectId}/eligible-areas/${administrativeAreaId}`,
        {
          searchParams: { hardDelete },
        },
      ),
    onSuccess: (_data, variables) => {
      invalidateEligibleAreas(client, variables.priorityObjectId);
    },
  });
}
