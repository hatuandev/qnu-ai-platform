export type SupportStatus =
  | "submitted"
  | "processing"
  | "resolved"
  | "rejected"
  | "cancelled";
export type SupportRequestType =
  | "change_room"
  | "extend"
  | "check_out"
  | "other";

export const supportStatusLabels: Record<SupportStatus, string> = {
  submitted: "Mới gửi",
  processing: "Đang xử lý",
  resolved: "Đã giải quyết",
  rejected: "Từ chối",
  cancelled: "Đã hủy",
};

export type SupportBadgeVariant =
  | "secondary"
  | "destructive"
  | "success"
  | "warning"
  | "info";

export const supportStatusVariants: Record<SupportStatus, SupportBadgeVariant> =
  {
    submitted: "info",
    processing: "warning",
    resolved: "success",
    rejected: "destructive",
    cancelled: "secondary",
  };

export const supportTypeLabels: Record<SupportRequestType, string> = {
  change_room: "Đổi phòng",
  extend: "Gia hạn",
  check_out: "Trả phòng",
  other: "Khác",
};
export type SupportRequest = {
  id: string;
  studentCode: string;
  studentName: string;
  requestType: SupportRequestType;
  title: string;
  content: string;
  status: SupportStatus;
  assignedTo?: string | null;
  resolvedAt?: string | null;
  created: string;
  commentCount: number;
};
export type SupportRequestDetail = SupportRequest & {
  studentId: string;
  residenceId?: string | null;
  createdBy?: string | null;
  lastModified: string;
  lastModifiedBy?: string | null;
};
export type SupportComment = {
  id: string;
  supportRequestId: string;
  comment: string;
  createdBy: string;
  createdAt: string;
};
export type SupportHistory = {
  id: string;
  fromStatus?: SupportStatus | null;
  toStatus: SupportStatus;
  note?: string | null;
  changedBy?: string | null;
  changedAt: string;
};
export type SupportPage = {
  items: SupportRequest[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};
export type SupportListParams = {
  status?: SupportStatus;
  requestType?: SupportRequestType;
  search?: string;
  page: number;
  pageSize: number;
};
