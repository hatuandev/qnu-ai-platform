export type NotificationType =
  | "application_result"
  | "check_in"
  | "fee_due"
  | "room_selection"
  | "general";

export const notificationTypeLabels: Record<NotificationType, string> = {
  application_result: "Kết quả hồ sơ",
  check_in: "Nhận phòng",
  fee_due: "Thanh toán",
  room_selection: "Chọn phòng",
  general: "Thông báo chung",
};
export type Notification = {
  id: string;
  title: string;
  type: NotificationType;
  recipientCount: number;
  createdAt: string;
};
export type MyNotification = {
  id: string;
  title: string;
  content: string;
  type: NotificationType;
  createdAt: string;
  readAt?: string | null;
};
export type NotificationDetail = Notification & {
  content: string;
  createdBy?: string | null;
  recipients: Array<{
    id: string;
    studentId?: string | null;
    userId?: string | null;
    readAt?: string | null;
  }>;
};
export type NotificationsPage = {
  items: Notification[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};
export type NotificationsListParams = {
  type?: NotificationType;
  search?: string;
  page: number;
  pageSize: number;
};
