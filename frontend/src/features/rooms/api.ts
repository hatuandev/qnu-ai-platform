import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/app/api/client";
import type {
  CreateRoomInput,
  EditableRoomStatus,
  RoomDetail,
  RoomStatus,
  RoomsListParams,
  RoomsPage,
  UpdateRoomInput,
} from "@/features/rooms/types";

const roomsPath = "/DormitoryRooms";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isRoom(value: unknown): value is RoomsPage["items"][number] {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.code === "string" &&
    typeof value.name === "string" &&
    typeof value.buildingCode === "string" &&
    typeof value.floorNumber === "number" &&
    typeof value.roomTypeName === "string" &&
    typeof value.capacity === "number" &&
    typeof value.operationalCapacity === "number" &&
    typeof value.occupiedPlaces === "number" &&
    typeof value.availablePlaces === "number" &&
    typeof value.status === "string"
  );
}

function isRoomDetail(value: unknown): value is RoomDetail {
  return (
    isRoom(value) &&
    typeof (value as Record<string, unknown>).buildingId === "string" &&
    typeof (value as Record<string, unknown>).floorId === "string" &&
    typeof (value as Record<string, unknown>).roomTypeId === "string" &&
    typeof (value as Record<string, unknown>).created === "string" &&
    typeof (value as Record<string, unknown>).lastModified === "string"
  );
}

function isRoomsPage(value: unknown): value is RoomsPage {
  return (
    isRecord(value) &&
    Array.isArray(value.items) &&
    value.items.every(isRoom) &&
    typeof value.total === "number" &&
    typeof value.page === "number" &&
    typeof value.pageSize === "number" &&
    typeof value.totalPages === "number"
  );
}

export const roomsQueryKeys = {
  all: ["rooms"] as const,
  list: (params: RoomsListParams) =>
    [...roomsQueryKeys.all, "list", params] as const,
  detail: (id: string) => [...roomsQueryKeys.all, "detail", id] as const,
};

export function useRoomsQuery(params: RoomsListParams) {
  return useQuery({
    queryKey: roomsQueryKeys.list(params),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(roomsPath, {
        searchParams: {
          BuildingId: params.buildingId,
          FloorId: params.floorId,
          RoomTypeId: params.roomTypeId,
          Status: params.status,
          SearchCodeOrName: params.searchCodeOrName,
          PageIndex: params.page,
          PageSize: params.pageSize,
        },
      });
      if (!isRoomsPage(response)) {
        throw new Error("Phản hồi danh sách phòng không đúng định dạng.");
      }
      return response;
    },
    placeholderData: (previous) => previous,
  });
}

export function useRoomQuery(id: string) {
  return useQuery({
    queryKey: roomsQueryKeys.detail(id),
    enabled: Boolean(id),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(`${roomsPath}/${id}`);
      if (!isRoomDetail(response)) {
        throw new Error("Phản hồi chi tiết phòng không đúng định dạng.");
      }
      return response;
    },
  });
}

export function useCreateRoom() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateRoomInput) =>
      apiClient.post<string>(roomsPath, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: roomsQueryKeys.all });
    },
  });
}

export function useUpdateRoom() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: UpdateRoomInput }) =>
      apiClient.put<void>(`${roomsPath}/${id}`, { id, ...input }),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: roomsQueryKeys.all });
      void queryClient.invalidateQueries({
        queryKey: roomsQueryKeys.detail(variables.id),
      });
    },
  });
}

export function useUpdateRoomStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: EditableRoomStatus }) =>
      apiClient.put<void>(`${roomsPath}/${id}/status`, { id, status }),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: roomsQueryKeys.all });
      void queryClient.invalidateQueries({
        queryKey: roomsQueryKeys.detail(variables.id),
      });
    },
  });
}

export function useDeleteRoom() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.delete<void>(`${roomsPath}/${id}`),
    onSuccess: (_data, id) => {
      void queryClient.invalidateQueries({ queryKey: roomsQueryKeys.all });
      void queryClient.invalidateQueries({
        queryKey: roomsQueryKeys.detail(id),
      });
      void queryClient.invalidateQueries({ queryKey: ["buildings"] });
      void queryClient.invalidateQueries({ queryKey: ["floors"] });
      void queryClient.invalidateQueries({ queryKey: ["fee-rates"] });
    },
  });
}

export const roomStatusLabels: Record<RoomStatus, string> = {
  available: "Đang sử dụng",
  full: "Đã đủ chỗ",
  maintenance: "Bảo trì",
  inactive: "Ngừng sử dụng",
};
