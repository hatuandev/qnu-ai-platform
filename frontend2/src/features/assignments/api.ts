import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/app/api/client";
import type {
  Assignment,
  AssignmentsListParams,
  AssignmentsPage,
  AssignmentWorkspace,
  EligibleApplicationsPage,
  Room,
  RoomAssignmentByRoom,
} from "@/features/assignments/types";
import { roomsQueryKeys } from "@/features/rooms/api";

const path = "/RoomAssignments";
const roomsPath = "/DormitoryRooms";
const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;
const isPage = (value: unknown): value is AssignmentsPage =>
  isRecord(value) &&
  Array.isArray(value.items) &&
  typeof value.total === "number" &&
  typeof value.page === "number" &&
  typeof value.pageSize === "number" &&
  typeof value.totalPages === "number";

export const assignmentsQueryKeys = {
  all: ["assignments"] as const,
  workspace: (registrationPeriodId?: string) =>
    [...assignmentsQueryKeys.all, "workspace", registrationPeriodId] as const,
  list: (params: AssignmentsListParams) =>
    [...assignmentsQueryKeys.all, "list", params] as const,
  eligible: (search?: string, registrationPeriodId?: string) =>
    [
      ...assignmentsQueryKeys.all,
      "eligible",
      search,
      registrationPeriodId,
    ] as const,
  room: (roomId: string) =>
    [...assignmentsQueryKeys.all, "room", roomId] as const,
  rooms: ["assignments", "rooms"] as const,
};

export function useAssignmentWorkspaceQuery(
  registrationPeriodId?: string,
  enabled = true,
) {
  return useQuery({
    queryKey: assignmentsQueryKeys.workspace(registrationPeriodId),
    enabled: Boolean(registrationPeriodId) && enabled,
    queryFn: () =>
      apiClient.get<AssignmentWorkspace>(`${path}/workspace`, {
        searchParams: { RegistrationPeriodId: registrationPeriodId },
      }),
  });
}

export function useAssignmentsQuery(params: AssignmentsListParams) {
  return useQuery({
    queryKey: assignmentsQueryKeys.list(params),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(path, {
        searchParams: {
          Status: params.status,
          SearchStudentCodeOrName: params.search,
          RegistrationPeriodId: params.registrationPeriodId,
          BuildingId: params.buildingId,
          FloorId: params.floorId,
          RoomId: params.roomId,
          PageIndex: params.page,
          PageSize: params.pageSize,
        },
      });
      if (!isPage(response))
        throw new Error("Phản hồi danh sách xếp phòng không đúng định dạng.");
      return response;
    },
    placeholderData: (previous) => previous,
  });
}

export function useEligibleApplicationsQuery(
  search?: string,
  registrationPeriodId?: string,
  enabled = true,
) {
  return useQuery({
    queryKey: assignmentsQueryKeys.eligible(search, registrationPeriodId),
    enabled: enabled && Boolean(registrationPeriodId),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(`${path}/eligible`, {
        searchParams: {
          SearchStudentCodeOrName: search,
          RegistrationPeriodId: registrationPeriodId,
          PageIndex: 1,
          PageSize: 50,
        },
      });
      if (!isRecord(response) || !Array.isArray(response.items))
        throw new Error("Phản hồi hồ sơ đủ điều kiện không đúng định dạng.");
      return response as EligibleApplicationsPage;
    },
  });
}

export function useRoomAssignmentsQuery(roomId: string) {
  return useQuery({
    queryKey: assignmentsQueryKeys.room(roomId),
    queryFn: () =>
      apiClient.get<RoomAssignmentByRoom[]>(`${path}/room/${roomId}`),
    enabled: Boolean(roomId),
  });
}

export function useAssignmentRoomsQuery(enabled = true) {
  return useQuery({
    queryKey: assignmentsQueryKeys.rooms,
    enabled,
    queryFn: async () => {
      const response = await apiClient.get<unknown>(roomsPath, {
        searchParams: { PageIndex: 1, PageSize: 100, Status: "available" },
      });
      if (!isRecord(response) || !Array.isArray(response.items))
        throw new Error("Phản hồi danh sách phòng không đúng định dạng.");
      return response.items as Room[];
    },
  });
}

export function useAssignStudent() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      applicationId: string;
      roomId: string;
      note?: string;
    }) => apiClient.post<string>(path, input),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: assignmentsQueryKeys.all });
      void client.invalidateQueries({ queryKey: roomsQueryKeys.all });
      void client.invalidateQueries({ queryKey: ["applications"] });
    },
  });
}

export function useCancelAssignment() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, note }: { id: string; note?: string }) =>
      apiClient.put<void>(`${path}/${id}/cancel`, { assignmentId: id, note }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: assignmentsQueryKeys.all });
      void client.invalidateQueries({ queryKey: roomsQueryKeys.all });
      void client.invalidateQueries({ queryKey: ["invoices"] });
      void client.invalidateQueries({ queryKey: ["applications"] });
    },
  });
}

export interface RefundAndCancelAssignmentInput {
  assignmentId: string;
  refundAmount: number;
  refundReason: string;
  bankName: string;
  bankAccountNumber: string;
  bankAccountHolder: string;
  transactionReference?: string;
}

export function useRefundAndCancelAssignment() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: RefundAndCancelAssignmentInput) =>
      apiClient.post<void>(
        `${path}/${input.assignmentId}/refund-and-cancel`,
        input,
      ),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: assignmentsQueryKeys.all });
      void client.invalidateQueries({ queryKey: roomsQueryKeys.all });
      void client.invalidateQueries({ queryKey: ["invoices"] });
      void client.invalidateQueries({ queryKey: ["applications"] });
    },
  });
}

export function useFinalizeRoomSelection() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (registrationPeriodId: string) =>
      apiClient.post<{ finalizedCount: number; skippedCount: number }>(
        `${path}/finalize-selection`,
        { registrationPeriodId },
      ),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: assignmentsQueryKeys.all });
      void client.invalidateQueries({ queryKey: roomsQueryKeys.all });
      void client.invalidateQueries({ queryKey: ["applications"] });
      void client.invalidateQueries({ queryKey: ["registration-periods"] });
    },
  });
}

export function useAssignmentQuery(id: string) {
  return useQuery({
    queryKey: [...assignmentsQueryKeys.all, "detail", id],
    queryFn: () => apiClient.get<Assignment>(`${path}/${id}`),
    enabled: Boolean(id),
  });
}
