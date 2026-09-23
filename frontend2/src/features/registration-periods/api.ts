import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/app/api/client";
import type {
  RegistrationPeriod,
  RegistrationPeriodInput,
  RegistrationPeriodRoomRules,
  RegistrationPeriodRoomRulesParams,
  RegistrationPeriodsListParams,
  RegistrationPeriodsPage,
  UpdateRegistrationPeriodRoomRulesInput,
} from "@/features/registration-periods/types";

const path = "/RegistrationPeriods";
export const registrationPeriodsQueryKeys = {
  all: ["registration-periods"] as const,
  detail: (id: string) =>
    [...registrationPeriodsQueryKeys.all, "detail", id] as const,
  list: (params: RegistrationPeriodsListParams) =>
    [...registrationPeriodsQueryKeys.all, "list", params] as const,
  roomRules: (id: string) =>
    [...registrationPeriodsQueryKeys.all, "room-rules", id] as const,
};

export function useRegistrationPeriodQuery(
  periodId: string | undefined,
  enabled = true,
) {
  return useQuery({
    queryKey: registrationPeriodsQueryKeys.detail(periodId ?? ""),
    enabled: Boolean(periodId) && enabled,
    queryFn: () => apiClient.get<RegistrationPeriod>(`${path}/${periodId}`),
  });
}

export function useRegistrationPeriodsQuery(
  params: RegistrationPeriodsListParams,
) {
  return useQuery({
    queryKey: registrationPeriodsQueryKeys.list(params),
    queryFn: () =>
      apiClient.get<RegistrationPeriodsPage>(path, {
        searchParams: {
          SearchCodeOrName: params.search,
          Status: params.status,
          AcademicYearId: params.academicYearId,
          PageIndex: params.page,
          PageSize: params.pageSize,
        },
      }),
    placeholderData: (previous) => previous,
  });
}

export function useRegistrationPeriodRoomRulesQuery(
  periodId: string | undefined,
  enabled?: boolean,
): ReturnType<typeof useQuery<RegistrationPeriodRoomRules>>;
export function useRegistrationPeriodRoomRulesQuery(
  periodId: string | undefined,
  params?: RegistrationPeriodRoomRulesParams,
  enabled?: boolean,
): ReturnType<typeof useQuery<RegistrationPeriodRoomRules>>;
export function useRegistrationPeriodRoomRulesQuery(
  periodId: string | undefined,
  paramsOrEnabled?: RegistrationPeriodRoomRulesParams | boolean,
  maybeEnabled = true,
) {
  const params =
    typeof paramsOrEnabled === "object" ? paramsOrEnabled : undefined;
  const enabled =
    typeof paramsOrEnabled === "boolean" ? paramsOrEnabled : maybeEnabled;

  return useQuery({
    queryKey: [
      ...registrationPeriodsQueryKeys.roomRules(periodId ?? ""),
      params?.buildingCode ?? "all",
      params?.floorNumber,
    ],
    enabled: Boolean(periodId) && enabled,
    queryFn: () => {
      const searchParams: Record<string, string | number | undefined> = {};
      if (params?.buildingCode && params.buildingCode !== "all") {
        searchParams.buildingCode = params.buildingCode;
      }
      if (params?.floorNumber !== undefined) {
        searchParams.floorNumber = params.floorNumber;
      }
      return apiClient.get<RegistrationPeriodRoomRules>(
        `${path}/${periodId}/room-rules`,
        { searchParams },
      );
    },
    placeholderData: (previous) => previous,
  });
}

function invalidate(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({
    queryKey: registrationPeriodsQueryKeys.all,
  });
}
export function useCreateRegistrationPeriod() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: RegistrationPeriodInput) =>
      apiClient.post<string>(path, input),
    onSuccess: () => invalidate(queryClient),
  });
}

export function useUpdateRegistrationPeriod() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      input,
    }: {
      id: string;
      input: RegistrationPeriodInput;
    }) => apiClient.put<void>(`${path}/${id}`, { id, ...input }),
    onSuccess: () => invalidate(queryClient),
  });
}

export function useUpdateRegistrationPeriodRoomRules() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      input,
    }: {
      id: string;
      input: UpdateRegistrationPeriodRoomRulesInput;
    }) =>
      apiClient.put<void>(`${path}/${id}/room-rules`, {
        registrationPeriodId: id,
        ...input,
      }),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: registrationPeriodsQueryKeys.roomRules(variables.id),
      });
    },
  });
}

export function useNotifyRoomSelection() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.post<number>(`${path}/${id}/room-selection-notification`),
    onSuccess: (_data, id) => {
      void queryClient.invalidateQueries({
        queryKey: registrationPeriodsQueryKeys.roomRules(id),
      });
      void queryClient.invalidateQueries({
        queryKey: registrationPeriodsQueryKeys.all,
      });
    },
  });
}

export function useFinalizeRoomAllocation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.put<void>(`${path}/${id}/room-rules/finalize`),
    onSuccess: (_data, id) => {
      void queryClient.invalidateQueries({
        queryKey: registrationPeriodsQueryKeys.roomRules(id),
      });
      void queryClient.invalidateQueries({
        queryKey: registrationPeriodsQueryKeys.all,
      });
    },
  });
}
export function useRegistrationPeriodTransition() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      action,
    }: {
      id: string;
      action: "open" | "close" | "archive" | "restore" | "deactivate";
    }) =>
      action === "deactivate"
        ? apiClient.delete<void>(`${path}/${id}`)
        : apiClient.put<void>(`${path}/${id}/${action}`),
    onSuccess: () => invalidate(queryClient),
  });
}

export function useDeleteRegistrationPeriodsBatch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (registrationPeriodIds: string[]) =>
      apiClient.post<void>(`${path}/batch-delete`, { registrationPeriodIds }),
    onSuccess: () => invalidate(queryClient),
  });
}
