import type { IndexReadiness } from "./index-types";

/** Shared labels so every summary read describes readiness the same way. */
export const READINESS_LABELS: Record<IndexReadiness["status"], string> = {
  ready: "Sẵn sàng tra cứu",
  not_indexed: "Chưa cập nhật cho trợ lý AI",
  outdated: "Bản phục vụ chưa khớp",
  unavailable: "Không đọc được trạng thái phục vụ",
};
