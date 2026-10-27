import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/app/api/client";
import type { Floor } from "@/features/floors/types";

const floorsPath = (buildingId: string) =>
  `/DormitoryBuildings/${buildingId}/Floors`;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isFloor(value: unknown): value is Floor {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.buildingId === "string" &&
    typeof value.floorNumber === "number" &&
    typeof value.name === "string" &&
    (value.status === "active" || value.status === "inactive") &&
    typeof value.roomCount === "number"
  );
}

export const floorsQueryKeys = {
  all: ["floors"] as const,
  list: (buildingId: string) =>
    [...floorsQueryKeys.all, "list", buildingId] as const,
  detail: (buildingId: string, id: string) =>
    [...floorsQueryKeys.all, "detail", buildingId, id] as const,
};

export function useFloorsQuery(buildingId?: string) {
  return useQuery({
    queryKey: floorsQueryKeys.list(buildingId ?? ""),
    enabled: Boolean(buildingId),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(
        floorsPath(buildingId ?? ""),
      );
      if (!Array.isArray(response) || !response.every(isFloor)) {
        throw new Error("Phản hồi danh sách tầng không đúng định dạng.");
      }
      return response;
    },
  });
}

export function useFloorQuery(buildingId: string, id: string) {
  return useQuery({
    queryKey: floorsQueryKeys.detail(buildingId, id),
    enabled: Boolean(buildingId && id),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(
        `${floorsPath(buildingId)}/${id}`,
      );
      if (!isFloor(response)) {
        throw new Error("Phản hồi chi tiết tầng không đúng định dạng.");
      }
      return response;
    },
  });
}

export function useCreateFloor() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      buildingId,
      input,
    }: {
      buildingId: string;
      input: FloorFormInput;
    }) =>
      apiClient.post<string>(floorsPath(buildingId), { buildingId, ...input }),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: floorsQueryKeys.list(variables.buildingId),
      });
    },
  });
}

export function useUpdateFloor() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      buildingId,
      id,
      input,
    }: {
      buildingId: string;
      id: string;
      input: FloorFormInput;
    }) =>
      apiClient.put<void>(`${floorsPath(buildingId)}/${id}`, {
        buildingId,
        id,
        ...input,
      }),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: floorsQueryKeys.list(variables.buildingId),
      });
      void queryClient.invalidateQueries({
        queryKey: floorsQueryKeys.detail(variables.buildingId, variables.id),
      });
    },
  });
}

export function useDeactivateFloor() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ buildingId, id }: { buildingId: string; id: string }) =>
      apiClient.put<void>(`${floorsPath(buildingId)}/${id}/deactivate`),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: floorsQueryKeys.list(variables.buildingId),
      });
      void queryClient.invalidateQueries({
        queryKey: floorsQueryKeys.detail(variables.buildingId, variables.id),
      });
      void queryClient.invalidateQueries({
        queryKey: ["buildings"],
      });
    },
  });
}

export function useDeleteFloor() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ buildingId, id }: { buildingId: string; id: string }) =>
      apiClient.delete<void>(`${floorsPath(buildingId)}/${id}`),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: floorsQueryKeys.list(variables.buildingId),
      });
      void queryClient.invalidateQueries({
        queryKey: floorsQueryKeys.detail(variables.buildingId, variables.id),
      });
      void queryClient.invalidateQueries({
        queryKey: ["buildings"],
      });
    },
  });
}

export type FloorFormInput = {
  floorNumber?: number;
  name: string;
};
