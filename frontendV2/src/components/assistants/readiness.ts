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

/** Label for assistant without knowledge base collections (pure LLM mode). */
export const UNBOUND_LABEL = "Hội thoại trực tiếp";
export const UNBOUND_DETAIL =
  "Không gắn kho tri thức · Trợ lý hội thoại trực tiếp với mô hình AI theo Persona.";

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
    if (published === 0) {
      return "Chế độ hội thoại trực tiếp với mô hình AI";
    }
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
