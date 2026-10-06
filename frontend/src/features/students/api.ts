import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/app/api/client";
import type {
  Student,
  StudentDetail,
  StudentLookupDto,
  StudentsListParams,
  StudentsPage,
} from "@/features/students/types";

const path = "/Students";
const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;
const isPage = (value: unknown): value is StudentsPage =>
  isRecord(value) &&
  Array.isArray(value.items) &&
  typeof value.total === "number" &&
  typeof value.page === "number" &&
  typeof value.pageSize === "number" &&
  typeof value.totalPages === "number";
const isStudent = (value: unknown): value is Student =>
  isRecord(value) &&
  typeof value.id === "string" &&
  typeof value.studentCode === "string" &&
  typeof value.fullName === "string";
export const studentsQueryKeys = {
  all: ["students"] as const,
  list: (params: StudentsListParams) =>
    [...studentsQueryKeys.all, "list", params] as const,
  detail: (id: string) => [...studentsQueryKeys.all, "detail", id] as const,
  lookup: (studentCode: string) =>
    [...studentsQueryKeys.all, "lookup", studentCode] as const,
};

export function useLookupStudentQuery(
  studentCode: string,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: studentsQueryKeys.lookup(studentCode),
    queryFn: async () => {
      const response = await apiClient.get<StudentLookupDto>(
        `${path}/lookup/${encodeURIComponent(studentCode.trim())}`,
      );
      return response;
    },
    enabled: options?.enabled ?? Boolean(studentCode.trim()),
    retry: false,
  });
}
export function useStudentsQuery(
  params: StudentsListParams,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: studentsQueryKeys.list(params),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(path, {
        searchParams: {
          SearchCodeOrName: params.search,
          Status: params.status,
          Faculty: params.faculty,
          PageIndex: params.page,
          PageSize: params.pageSize,
        },
      });
      if (!isPage(response))
        throw new Error("Phản hồi danh sách sinh viên không đúng định dạng.");
      return response;
    },
    enabled: options?.enabled ?? true,
    placeholderData: (previous) => previous,
  });
}
export function useStudentQuery(id: string) {
  return useQuery({
    queryKey: studentsQueryKeys.detail(id),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(`${path}/${id}`);
      if (!isStudent(response))
        throw new Error("Phản hồi chi tiết sinh viên không đúng định dạng.");
      return response as StudentDetail;
    },
    enabled: Boolean(id),
  });
}
export function useCreateStudent() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: Record<string, unknown>) =>
      apiClient.post<string>(path, input),
    onSuccess: () =>
      void client.invalidateQueries({ queryKey: studentsQueryKeys.all }),
  });
}
export function useUpdateStudent() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      input,
    }: {
      id: string;
      input: Record<string, unknown>;
    }) => apiClient.put<void>(`${path}/${id}`, { id, ...input }),
    onSuccess: (_data, variables) => {
      void client.invalidateQueries({ queryKey: studentsQueryKeys.all });
      void client.invalidateQueries({
        queryKey: studentsQueryKeys.detail(variables.id),
      });
    },
  });
}
export function useDeactivateStudent() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.delete<void>(`${path}/${id}`),
    onSuccess: () =>
      void client.invalidateQueries({ queryKey: studentsQueryKeys.all }),
  });
}
