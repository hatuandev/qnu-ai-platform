import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/app/api/client";
import type {
  AcademicYear,
  AcademicYearsListParams,
  AcademicYearsPage,
} from "@/features/academic-years/types";

const academicYearsPath = "/AcademicYears";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isAcademicYear(value: unknown): value is AcademicYear {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.code === "string" &&
    typeof value.name === "string" &&
    typeof value.startDate === "string" &&
    typeof value.endDate === "string" &&
    typeof value.isCurrent === "boolean" &&
    typeof value.registrationPeriodCount === "number"
  );
}

function isAcademicYearsPage(value: unknown): value is AcademicYearsPage {
  return (
    isRecord(value) &&
    Array.isArray(value.items) &&
    value.items.every(isAcademicYear) &&
    typeof value.total === "number" &&
    typeof value.page === "number" &&
    typeof value.pageSize === "number" &&
    typeof value.totalPages === "number"
  );
}

export const academicYearsQueryKeys = {
  all: ["academic-years"] as const,
  list: (params: AcademicYearsListParams) =>
    [...academicYearsQueryKeys.all, "list", params] as const,
  detail: (id: string) =>
    [...academicYearsQueryKeys.all, "detail", id] as const,
};

export function useAcademicYearsQuery(params: AcademicYearsListParams) {
  return useQuery({
    queryKey: academicYearsQueryKeys.list(params),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(academicYearsPath, {
        searchParams: {
          SearchCodeOrName: params.searchCodeOrName,
          IsCurrent: params.isCurrent,
          PageIndex: params.page,
          PageSize: params.pageSize,
        },
      });
      if (!isAcademicYearsPage(response)) {
        throw new Error("Phản hồi danh sách năm học không đúng định dạng.");
      }
      return response;
    },
    placeholderData: (previous) => previous,
  });
}

export function useAcademicYearQuery(id: string) {
  return useQuery({
    queryKey: academicYearsQueryKeys.detail(id),
    enabled: Boolean(id),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(
        `${academicYearsPath}/${id}`,
      );
      if (!isAcademicYear(response)) {
        throw new Error("Phản hồi chi tiết năm học không đúng định dạng.");
      }
      return response;
    },
  });
}

export function useCreateAcademicYear() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: AcademicYearInput) =>
      apiClient.post<string>(academicYearsPath, input),
    onSuccess: () =>
      void queryClient.invalidateQueries({
        queryKey: academicYearsQueryKeys.all,
      }),
  });
}

export function useUpdateAcademicYear() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: AcademicYearInput }) =>
      apiClient.put<void>(`${academicYearsPath}/${id}`, { id, ...input }),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: academicYearsQueryKeys.all,
      });
      void queryClient.invalidateQueries({
        queryKey: academicYearsQueryKeys.detail(variables.id),
      });
    },
  });
}

export function useDeactivateAcademicYear() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.put<void>(`${academicYearsPath}/${id}/deactivate`),
    onSuccess: (_data, id) => {
      void queryClient.invalidateQueries({
        queryKey: academicYearsQueryKeys.all,
      });
      void queryClient.invalidateQueries({
        queryKey: academicYearsQueryKeys.detail(id),
      });
    },
  });
}

export function useDeleteAcademicYear() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiClient.delete<void>(`${academicYearsPath}/${id}`),
    onSuccess: (_data, id) => {
      void queryClient.invalidateQueries({
        queryKey: academicYearsQueryKeys.all,
      });
      void queryClient.invalidateQueries({
        queryKey: academicYearsQueryKeys.detail(id),
      });
      void queryClient.invalidateQueries({
        queryKey: ["registration-periods"],
      });
      void queryClient.invalidateQueries({ queryKey: ["fee-rates"] });
    },
  });
}

export type AcademicYearInput = {
  code?: string;
  name: string;
  startDate: string;
  endDate: string;
  isCurrent: boolean;
};
