import type {
  AssistantReadiness,
  AssistantReadinessStatus,
} from "@/features/assistants/types";

export const READINESS_BADGE: Record<
  AssistantReadinessStatus,
  {
    label: string;
    variant: "success" | "warning" | "destructive" | "secondary" | "info";
  }
> = {
  empty: { label: "Chưa có tài liệu xuất bản", variant: "warning" },
  syncing: { label: "Đang chuẩn bị", variant: "info" },
  ready: { label: "Sẵn sàng", variant: "success" },
  outdated: { label: "Cần cập nhật chỉ mục", variant: "warning" },
  not_indexed: { label: "Chưa lập chỉ mục", variant: "warning" },
  failed: { label: "Chuẩn bị thất bại", variant: "destructive" },
  uncertain: { label: "Chưa xác định", variant: "warning" },
};

export function readinessDetail(readiness: AssistantReadiness): string {
  const served = readiness.served_document_count;
  const published = readiness.published_document_count;
  switch (readiness.status) {
    case "empty":
      return "Bộ sưu tập chưa có tài liệu xuất bản nào. Trợ lý sẽ báo thiếu căn cứ thay vì trả lời bằng kiến thức ngoài kho.";
    case "syncing":
      return `Đang chuẩn bị ${published} tài liệu xuất bản; hiện ${served} tài liệu đã sẵn sàng phục vụ.`;
    case "ready":
      return `${served}/${published} tài liệu xuất bản đang được trợ lý sử dụng để trả lời.`;
    case "outdated":
      return `${served}/${published} tài liệu đang phục vụ; có bản xuất bản mới chưa vào chỉ mục.`;
    case "not_indexed":
      return `${published} tài liệu đã xuất bản nhưng chưa có chỉ mục hoạt động.`;
    case "failed":
      return `Chuẩn bị chỉ mục thất bại. ${served}/${published} tài liệu còn phục vụ; mở kho tri thức để xem chi tiết.`;
    case "uncertain":
      return `Chưa xác định được trạng thái chỉ mục. ${served}/${published} tài liệu còn phục vụ; mở kho tri thức để kiểm tra.`;
  }
}
