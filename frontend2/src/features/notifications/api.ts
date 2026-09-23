import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/app/api/client";
import type {
  MyNotification,
  NotificationDetail,
  NotificationsListParams,
  NotificationsPage,
} from "@/features/notifications/types";

const path = "/Notifications";
const isRecord = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null;
const isPage = (v: unknown): v is NotificationsPage =>
  isRecord(v) &&
  Array.isArray(v.items) &&
  typeof v.total === "number" &&
  typeof v.page === "number" &&
  typeof v.pageSize === "number" &&
  typeof v.totalPages === "number";
const isMyNotification = (v: unknown): v is MyNotification =>
  isRecord(v) &&
  typeof v.id === "string" &&
  typeof v.title === "string" &&
  typeof v.content === "string" &&
  typeof v.createdAt === "string";
const isMyNotificationList = (v: unknown): v is MyNotification[] =>
  Array.isArray(v) && v.every(isMyNotification);
export const notificationsQueryKeys = {
  all: ["notifications"] as const,
  list: (params: NotificationsListParams) =>
    [...notificationsQueryKeys.all, "list", params] as const,
  detail: (id: string) =>
    [...notificationsQueryKeys.all, "detail", id] as const,
  mine: (unreadOnly: boolean) =>
    [...notificationsQueryKeys.all, "mine", unreadOnly] as const,
  unreadCount: () => [...notificationsQueryKeys.all, "unread-count"] as const,
};
export function useNotificationsQuery(
  params: NotificationsListParams,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: notificationsQueryKeys.list(params),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(path, {
        searchParams: {
          Type: params.type,
          SearchTitle: params.search,
          PageIndex: params.page,
          PageSize: params.pageSize,
        },
      });
      if (!isPage(response))
        throw new Error("Phản hồi danh sách thông báo không đúng định dạng.");
      return response;
    },
    enabled: options?.enabled ?? true,
    placeholderData: (previous) => previous,
  });
}
export function useNotificationQuery(
  id: string,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: notificationsQueryKeys.detail(id),
    queryFn: () => apiClient.get<NotificationDetail>(`${path}/${id}`),
    enabled: Boolean(id) && (options?.enabled ?? true),
  });
}
export function useCreateNotification() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      title: string;
      content: string;
      type: string;
      sendToAllStudents?: boolean;
      studentRecipientIds: string[];
      userRecipientIds: string[];
    }) => apiClient.post<string>(path, input),
    onSuccess: () =>
      void client.invalidateQueries({ queryKey: notificationsQueryKeys.all }),
  });
}

export function useMyNotificationsQuery(unreadOnly = false) {
  return useQuery({
    queryKey: notificationsQueryKeys.mine(unreadOnly),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(`${path}/my`, {
        searchParams: { UnreadOnly: unreadOnly },
      });
      if (!isMyNotificationList(response))
        throw new Error("Phản hồi thông báo cá nhân không đúng định dạng.");
      return response;
    },
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}

export function useMyNotificationUnreadCountQuery() {
  return useQuery({
    queryKey: notificationsQueryKeys.unreadCount(),
    queryFn: async () => {
      const response = await apiClient.get<unknown>(`${path}/my/unread-count`);
      if (!isRecord(response) || typeof response.count !== "number")
        throw new Error(
          "Phản hồi số lượng thông báo chưa đọc không đúng định dạng.",
        );
      return response.count;
    },
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}

export function useMarkNotificationAsRead() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (notificationId: string) =>
      apiClient.put<void>(`${path}/${notificationId}/read`, {
        notificationId,
      }),
    onSuccess: () => {
      void client.invalidateQueries({
        queryKey: notificationsQueryKeys.mine(false),
      });
      void client.invalidateQueries({
        queryKey: notificationsQueryKeys.mine(true),
      });
      void client.invalidateQueries({
        queryKey: notificationsQueryKeys.unreadCount(),
      });
    },
  });
}
