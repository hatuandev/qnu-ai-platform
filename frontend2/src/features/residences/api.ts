import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/app/api/client";
import { assignmentsQueryKeys } from "@/features/assignments/api";
import type {
  ResidenceDetail,
  ResidenceHistory,
  ResidencesListParams,
  ResidencesPage,
} from "@/features/residences/types";
import { roomsQueryKeys } from "@/features/rooms/api";

const path = "/Residences";
const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;
const isPage = (value: unknown): value is ResidencesPage =>
  isRecord(value) &&
  Array.isArray(value.items) &&
  typeof value.total === "number" &&
  typeof value.page === "number" &&
  typeof value.pageSize === "number" &&
  typeof value.totalPages === "number";

export const residencesQueryKeys = {
  all: ["residences"] as const,
  list: (params: ResidencesListParams) =>
    [...residencesQueryKeys.all, "list", params] as const,
  detail: (id: string) => [...residencesQueryKeys.all, "detail", id] as const,
  history: (id: string) => [...residencesQueryKeys.all, "history", id] as const,
};

export function useResidencesQuery(params: ResidencesListParams) {
  return useQuery({
    queryKey: residencesQueryKeys.list(params),
    enabled: params.enabled !== false,
    queryFn: async () => {
      const response = await apiClient.get<unknown>(path, {
        searchParams: {
          BuildingId: params.buildingId,
          FloorId: params.floorId,
          RoomId: params.roomId,
          RegistrationPeriodId: params.registrationPeriodId,
          AcademicYearId: params.academicYearId,
          Status: params.status,
          SearchStudentCodeOrName: params.search,
          PageIndex: params.page,
          PageSize: params.pageSize,
        },
      });
      if (!isPage(response))
        throw new Error("Phản hồi danh sách cư trú không đúng định dạng.");
      return response;
    },
    placeholderData: (previous) => previous,
  });
}

export function useResidenceQuery(id: string) {
  return useQuery({
    queryKey: residencesQueryKeys.detail(id),
    queryFn: () => apiClient.get<ResidenceDetail>(`${path}/${id}`),
    enabled: Boolean(id),
  });
}

export function useResidenceHistoryQuery(id: string) {
  return useQuery({
    queryKey: residencesQueryKeys.history(id),
    queryFn: () => apiClient.get<ResidenceHistory[]>(`${path}/${id}/history`),
    enabled: Boolean(id),
  });
}

function invalidate(client: ReturnType<typeof useQueryClient>, id?: string) {
  void client.invalidateQueries({ queryKey: residencesQueryKeys.all });
  void client.invalidateQueries({ queryKey: assignmentsQueryKeys.all });
  void client.invalidateQueries({ queryKey: roomsQueryKeys.all });
  if (id)
    void client.invalidateQueries({ queryKey: residencesQueryKeys.detail(id) });
}

export function useCheckIn() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      assignmentId: string;
      startDate: string;
      expectedEndDate?: string;
      note?: string;
    }) => apiClient.post<string>(`${path}/check-in`, input),
    onSuccess: () => invalidate(client),
  });
}

export type CheckInBatchInput = {
  assignmentIds?: string[];
  registrationPeriodId?: string;
  startDate: string;
  expectedEndDate?: string;
  note?: string;
};

export type CheckInBatchResult = {
  totalRequested: number;
  succeededCount: number;
  failedCount: number;
  succeededResidenceIds: string[];
  failureMessages: string[];
};

export function useCheckInBatch() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: CheckInBatchInput) =>
      apiClient.post<CheckInBatchResult>(`${path}/check-in-batch`, input),
    onSuccess: () => invalidate(client),
  });
}

export function useCheckOut() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      actualEndDate,
      note,
    }: {
      id: string;
      actualEndDate: string;
      note?: string;
    }) =>
      apiClient.post<void>(`${path}/${id}/check-out`, {
        residenceId: id,
        actualEndDate,
        note,
      }),
    onSuccess: (_data, variables) => invalidate(client, variables.id),
  });
}

export function useRevokeResidence() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      actualEndDate,
      note,
    }: {
      id: string;
      actualEndDate: string;
      note?: string;
    }) =>
      apiClient.post<void>(`${path}/${id}/revoke`, {
        residenceId: id,
        actualEndDate,
        note,
      }),
    onSuccess: (_data, variables) => invalidate(client, variables.id),
  });
}

export function useTransferResidence() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      newRoomId,
      note,
    }: {
      id: string;
      newRoomId: string;
      note?: string;
    }) =>
      apiClient.post<void>(`${path}/${id}/transfer`, {
        residenceId: id,
        newRoomId,
        note,
      }),
    onSuccess: (_data, variables) => invalidate(client, variables.id),
  });
}

export function useExtendResidence() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      newExpectedEndDate,
      note,
    }: {
      id: string;
      newExpectedEndDate: string;
      note?: string;
    }) =>
      apiClient.post<void>(`${path}/${id}/extend`, {
        residenceId: id,
        newExpectedEndDate,
        note,
      }),
    onSuccess: (_data, variables) => invalidate(client, variables.id),
  });
}
