import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/app/api/client";
import type {
  SupportComment,
  SupportHistory,
  SupportListParams,
  SupportPage,
  SupportRequestDetail,
} from "@/features/support/types";

const path = "/SupportRequests";
const isRecord = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null;
const isPage = (v: unknown): v is SupportPage =>
  isRecord(v) &&
  Array.isArray(v.items) &&
  typeof v.total === "number" &&
  typeof v.page === "number" &&
  typeof v.pageSize === "number" &&
  typeof v.totalPages === "number";
export const supportQueryKeys = {
  all: ["support"] as const,
  list: (params: SupportListParams) =>
    [...supportQueryKeys.all, "list", params] as const,
  detail: (id: string) => [...supportQueryKeys.all, "detail", id] as const,
  comments: (id: string) => [...supportQueryKeys.all, "comments", id] as const,
  history: (id: string) => [...supportQueryKeys.all, "history", id] as const,
};
export function useSupportQuery(
  params: SupportListParams,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: supportQueryKeys.list(params),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(path, {
        searchParams: {
          Status: params.status,
          RequestType: params.requestType,
          SearchTitleOrContent: params.search,
          PageIndex: params.page,
          PageSize: params.pageSize,
        },
      });
      if (!isPage(response))
        throw new Error(
          "Phản hồi danh sách yêu cầu hỗ trợ không đúng định dạng.",
        );
      return response;
    },
    enabled: options?.enabled ?? true,
    placeholderData: (previous) => previous,
  });
}
export function useSupportDetailQuery(
  id: string,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: supportQueryKeys.detail(id),
    queryFn: () => apiClient.get<SupportRequestDetail>(`${path}/${id}`),
    enabled: Boolean(id) && (options?.enabled ?? true),
  });
}
export function useSupportCommentsQuery(
  id: string,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: supportQueryKeys.comments(id),
    queryFn: () => apiClient.get<SupportComment[]>(`${path}/${id}/comments`),
    enabled: Boolean(id) && (options?.enabled ?? true),
  });
}
export function useSupportHistoryQuery(
  id: string,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: supportQueryKeys.history(id),
    queryFn: () => apiClient.get<SupportHistory[]>(`${path}/${id}/history`),
    enabled: Boolean(id) && (options?.enabled ?? true),
  });
}
function invalidate(client: ReturnType<typeof useQueryClient>, id?: string) {
  void client.invalidateQueries({ queryKey: supportQueryKeys.all });
  if (id)
    void client.invalidateQueries({ queryKey: supportQueryKeys.detail(id) });
}
export function useCreateSupportRequest() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: Record<string, unknown>) =>
      apiClient.post<string>(path, input),
    onSuccess: () => invalidate(client),
  });
}
export function useProcessSupportRequest() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      newStatus,
      note,
    }: {
      id: string;
      newStatus: string;
      note?: string;
    }) =>
      apiClient.post<void>(`${path}/${id}/process`, {
        supportRequestId: id,
        newStatus,
        note,
      }),
    onSuccess: (_data, variables) => invalidate(client, variables.id),
  });
}
export function useAddSupportComment() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, comment }: { id: string; comment: string }) =>
      apiClient.post<void>(`${path}/${id}/comments`, {
        supportRequestId: id,
        comment,
      }),
    onSuccess: (_data, variables) => {
      invalidate(client, variables.id);
      void client.invalidateQueries({
        queryKey: supportQueryKeys.comments(variables.id),
      });
    },
  });
}
