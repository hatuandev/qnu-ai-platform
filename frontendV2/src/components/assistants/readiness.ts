import type { AssistantReadinessStatus } from "@/api/assistants";

export const READINESS_MAP: Record<
  AssistantReadinessStatus,
  {
    label: string;
    variant: "success" | "info" | "warning" | "secondary" | "destructive";
  }
> = {
  empty: { label: "Chưa có nội dung", variant: "secondary" },
  syncing: { label: "Đang nạp chỉ mục", variant: "info" },
  ready: { label: "Sẵn sàng", variant: "success" },
  outdated: { label: "Cần cập nhật chỉ mục", variant: "warning" },
  not_indexed: { label: "Chưa nạp chỉ mục", variant: "secondary" },
  failed: { label: "Nạp chỉ mục lỗi", variant: "destructive" },
  uncertain: { label: "Chưa xác định", variant: "warning" },
};

/** An unbound assistant also reports readiness "empty"; say what is actually missing. */
export const UNBOUND_LABEL = "Chưa gắn kho";
export const UNBOUND_DETAIL =
  "Trợ lý chưa gắn kho tri thức. Gắn ít nhất một kho trong tab Cấu hình để bắt đầu phục vụ.";

/** Hero wording: a ready assistant serves answers, not just "ready". */
export function readinessHeroLabel(status: AssistantReadinessStatus): string {
  if (status === "ready") return "Sẵn sàng phục vụ";
  return READINESS_MAP[status].label;
}

export function readinessDetail(
  status: AssistantReadinessStatus,
  served: number,
  published: number,
): string {
  if (status === "ready") {
    return `${served}/${published} tài liệu đang được phục vụ`;
  }
  if (status === "empty") return "Kho chưa có tài liệu xuất bản";
  if (status === "syncing") return "Đang đồng bộ chỉ mục từ kho tri thức";
  if (status === "outdated" || status === "not_indexed") {
    return "Cần nạp lại chỉ mục để phục vụ nội dung mới";
  }
  if (published > 0) return `${published} tài liệu đã xuất bản`;
  return "Chưa kiểm tra được tài liệu phục vụ";
}
