import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/app/api/client";
import type {
  RoomType,
  RoomTypesListParams,
  RoomTypesPage,
} from "@/features/room-types/types";

const roomTypesPath = "/RoomTypes";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isRoomType(value: unknown): value is RoomType {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.code === "string" &&
    typeof value.name === "string" &&
    typeof value.capacity === "number" &&
    typeof value.isActive === "boolean" &&
    typeof value.roomCount === "number"
  );
}

function isRoomTypesPage(value: unknown): value is RoomTypesPage {
  return (
    isRecord(value) &&
    Array.isArray(value.items) &&
    value.items.every(isRoomType) &&
    typeof value.total === "number" &&
    typeof value.page === "number" &&
    typeof value.pageSize === "number" &&
    typeof value.totalPages === "number"
  );
}

export const roomTypesQueryKeys = {
  all: ["room-types"] as const,
  list: (params: RoomTypesListParams) =>
    [...roomTypesQueryKeys.all, "list", params] as const,
  detail: (id: string) => [...roomTypesQueryKeys.all, "detail", id] as const,
};

export function useRoomTypesQuery(params: RoomTypesListParams) {
  return useQuery({
    queryKey: roomTypesQueryKeys.list(params),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(roomTypesPath, {
        searchParams: {
          SearchCodeOrName: params.searchCodeOrName,
          IsActive: params.isActive,
          PageIndex: params.page,
          PageSize: params.pageSize,
        },
      });
      if (!isRoomTypesPage(response)) {
        throw new Error("Phản hồi danh sách loại phòng không đúng định dạng.");
      }
      return response;
    },
    placeholderData: (previous) => previous,
  });
}

export function useRoomTypeQuery(id: string) {
  return useQuery({
    queryKey: roomTypesQueryKeys.detail(id),
    enabled: Boolean(id),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(`${roomTypesPath}/${id}`);
      if (!isRoomType(response)) {
        throw new Error("Phản hồi chi tiết loại phòng không đúng định dạng.");
      }
      return response;
    },
  });
}

export function useCreateRoomType() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: RoomTypeInput) =>
      apiClient.post<string>(roomTypesPath, input),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: roomTypesQueryKeys.all }),
  });
}

export function useUpdateRoomType() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: RoomTypeInput }) =>
      apiClient.put<void>(`${roomTypesPath}/${id}`, { id, ...input }),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: roomTypesQueryKeys.all });
      void queryClient.invalidateQueries({
        queryKey: roomTypesQueryKeys.detail(variables.id),
      });
    },
  });
}

export function useDeactivateRoomType() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.put<void>(`${roomTypesPath}/${id}/deactivate`),
    onSuccess: (_data, id) => {
      void queryClient.invalidateQueries({ queryKey: roomTypesQueryKeys.all });
      void queryClient.invalidateQueries({
        queryKey: roomTypesQueryKeys.detail(id),
      });
    },
  });
}

export function useDeleteRoomType() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete<void>(`${roomTypesPath}/${id}`),
    onSuccess: (_data, id) => {
      void queryClient.invalidateQueries({ queryKey: roomTypesQueryKeys.all });
      void queryClient.invalidateQueries({
        queryKey: roomTypesQueryKeys.detail(id),
      });
    },
  });
}

export type RoomTypeInput = {
  code?: string;
  name: string;
  capacity: number;
  description?: string;
};
