import type { PreparationIntent, PreparationStatus } from "./preparation-types";

const ACTIVE_PREPARATION_STATUSES: ReadonlySet<PreparationStatus> = new Set([
  "queued",
  "waiting_ocr",
  "compiling",
]);

const STATUS_LABELS: Record<PreparationStatus, string> = {
  queued: "Đã ghi nhận",
  waiting_ocr: "Đang đọc nội dung",
  compiling: "Đang tạo bản nháp",
  ready: "Bản nháp sẵn sàng",
  failed: "Chưa hoàn tất",
  uncertain: "Chưa rõ trạng thái",
  cancelled: "Đã hủy",
};

const STATUS_HINTS: Record<PreparationStatus, string> = {
  queued: "Yêu cầu đã được lưu trên máy chủ và đang chờ bước kế tiếp.",
  waiting_ocr:
    "Hệ thống đang đọc nội dung tài liệu. Bạn có thể đóng trang, yêu cầu vẫn tiếp tục.",
  compiling: "Hệ thống đang tạo bản nháp có dẫn chứng từ bản văn bản đã lưu.",
  ready: "Bản nháp đã sẵn sàng để bạn xem và quyết định bước tiếp theo.",
  failed: "Yêu cầu dừng trước khi tạo xong bản nháp.",
  uncertain:
    "Chưa xác định được kết quả cuối cùng. Hãy kiểm tra tài liệu trước khi gửi lại.",
  cancelled: "Yêu cầu đã hủy; hệ thống không chạy bước kế tiếp.",
};

const ERROR_MESSAGES: Record<string, string> = {
  preparation_source_changed:
    "Tệp nguồn đã thay đổi so với lúc gửi yêu cầu. Hãy mở lại phiên bản hiện tại và chuẩn bị lại.",
  preparation_text_version_invalid:
    "Bản văn bản đã lưu không còn khớp với lượt đọc nội dung. Hãy chọn bản văn bản mới nhất.",
  preparation_text_version_not_ready:
    "Bản văn bản đã chọn chưa sẵn sàng. Hãy đợi đọc nội dung xong rồi thử lại.",
  preparation_text_version_not_found:
    "Không tìm thấy bản văn bản đã chọn trên máy chủ. Hãy chọn lại.",
  preparation_ocr_run_not_found:
    "Không tìm thấy lượt đọc nội dung đã chọn. Hãy chọn lại.",
  preparation_ocr_run_unusable:
    "Lượt đọc nội dung đã chọn chưa hoàn tất hoặc không còn dùng được.",
  preparation_ocr_run_missing:
    "Yêu cầu đang thiếu lượt đọc nội dung. Hãy thử lại.",
  preparation_topic_required:
    "Tài liệu chưa có tiêu đề. Hãy đổi tên tài liệu trước khi chuẩn bị.",
  idempotency_conflict:
    "Yêu cầu trùng mã nhưng khác nội dung. Hãy đóng hộp thoại và thử lại.",
  provider_not_found: "Model đã chọn chưa được cấp cho workspace này.",
  provider_capability_mismatch: "Model đã chọn không hỗ trợ hội thoại (chat).",
  provider_inactive: "Model đã chọn đang tạm ngưng hoạt động.",
  model_not_configured:
    "Chưa chọn model mặc định cho chức năng này. Hãy cấu hình trong ModelOps.",
  quota_exceeded: "Workspace đã hết quota cho thao tác này.",
};

export function isPreparationActive(
  intent: Pick<PreparationIntent, "status"> | null | undefined,
): boolean {
  return intent ? ACTIVE_PREPARATION_STATUSES.has(intent.status) : false;
}

export function preparationStatusLabel(status: PreparationStatus): string {
  return STATUS_LABELS[status] ?? status;
}

export function preparationStatusHint(status: PreparationStatus): string {
  return STATUS_HINTS[status] ?? "";
}

export function preparationStatusVariant(
  status: PreparationStatus,
):
  | "default"
  | "secondary"
  | "outline"
  | "destructive"
  | "success"
  | "warning"
  | "info" {
  switch (status) {
    case "queued":
    case "waiting_ocr":
    case "compiling":
      return "info";
    case "ready":
      return "success";
    case "failed":
    case "uncertain":
      return "destructive";
    case "cancelled":
      return "outline";
    default:
      return "secondary";
  }
}

export function formatPreparationError(
  code: string | null | undefined,
): string {
  if (!code) {
    return "Chuẩn bị nội dung chưa hoàn tất. Hãy thử lại hoặc kiểm tra tài liệu nguồn.";
  }
  return (
    ERROR_MESSAGES[code] ??
    "Chuẩn bị nội dung chưa hoàn tất. Hãy thử lại hoặc kiểm tra tài liệu nguồn."
  );
}

export function shortHash(hash: string | null | undefined): string {
  if (!hash) return "";
  return hash.slice(0, 12);
}
