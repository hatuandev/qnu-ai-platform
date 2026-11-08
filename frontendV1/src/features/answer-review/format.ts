import type {
  AnswerReviewItemStatus,
  AnswerReviewLabel,
  AnswerReviewStatus,
} from "@/features/answer-review/types";

type BadgeVariant =
  | "default"
  | "secondary"
  | "outline"
  | "destructive"
  | "success"
  | "warning"
  | "info";

export const ANSWER_REVIEW_LABEL_META: Record<
  AnswerReviewLabel,
  { label: string; variant: BadgeVariant }
> = {
  correct: { label: "Đúng", variant: "success" },
  missing: { label: "Thiếu nguồn", variant: "warning" },
  wrong_source: { label: "Sai nguồn", variant: "destructive" },
  wrong_year: { label: "Sai năm", variant: "warning" },
};

export const ANSWER_REVIEW_STATUS_META: Record<
  AnswerReviewStatus,
  { label: string; variant: BadgeVariant }
> = {
  running: { label: "Đang chạy", variant: "info" },
  completed: { label: "Đã có kết quả", variant: "success" },
  failed: { label: "Có câu hỏi lỗi", variant: "destructive" },
  uncertain: { label: "Chưa xác định", variant: "warning" },
};

export const ANSWER_REVIEW_ITEM_STATUS_META: Record<
  AnswerReviewItemStatus,
  { label: string; variant: BadgeVariant }
> = {
  answered: { label: "Đã trả lời", variant: "success" },
  insufficient_evidence: { label: "Thiếu bằng chứng", variant: "warning" },
  failed: { label: "Lỗi", variant: "destructive" },
  uncertain: { label: "Chưa xác định", variant: "warning" },
};

/**
 * Maps answer-test error codes to honest Vietnamese explanations.
 * Model/infrastructure failures stay failures; they never become an answer.
 */
export function formatAnswerReviewError(
  code?: string | null,
  fallbackMessage?: string,
): string {
  if (!code) return fallbackMessage || "Đã xảy ra lỗi không xác định.";

  switch (code) {
    case "assistant_inactive":
      return "Trợ lý đang tạm dừng nên không thể chạy kiểm thử.";
    case "assistant_no_published_sources":
      return "Kho tri thức chưa có tài liệu xuất bản nào để kiểm thử. Hãy xuất bản tài liệu trước.";
    case "idempotency_conflict":
      return "Khóa kiểm thử đã dùng cho bộ câu hỏi khác. Thay đổi câu hỏi rồi chạy lại.";
    case "answer_review_item_not_ready":
      return "Chỉ gắn nhãn cho câu hỏi đã có kết quả trả lời hoặc kết quả thiếu bằng chứng.";
    case "answer_review_not_found":
      return "Không tìm thấy lần kiểm thử yêu cầu.";
    case "answer_review_cancelled":
      return "Lần kiểm thử đã bị hủy trước khi hoàn tất.";
    case "answer_review_not_run":
      return "Câu hỏi chưa được chạy do lần kiểm thử dừng trước khi xử lý.";
    case "answer_review_failed":
      return "Câu hỏi không hoàn tất được trong lần kiểm thử này.";
    case "workspace_forbidden":
      return "Bạn không có quyền gắn nhãn đánh giá trong workspace này.";
    case "chat_provider_unavailable":
      return "Model chat không khả dụng khi chạy kiểm thử. Đây là lỗi hạ tầng, không phải kết quả trả lời.";
    case "chat_output_truncated":
      return "Câu trả lời bị cắt do giới hạn đầu ra. Đây là lỗi cấu hình model, không phải kết quả đầy đủ.";
    case "answer_citation_invalid":
      return "Trích dẫn do model trả về không hợp lệ nên câu trả lời không được phát hành.";
    case "answer_context_budget_exceeded":
      return "Ngữ cảnh vượt ngân sách đã cấu hình nên câu hỏi không hoàn tất. Thu hẹp câu hỏi hoặc tăng ngân sách.";
    case "answer_not_supported":
      return "Câu trả lời không được nguồn trích dẫn hỗ trợ nên hệ thống không phát hành.";
    case "answer_verification_uncertain":
      return "Bước kiểm chứng chưa xác định được căn cứ của câu trả lời.";
    default:
      return fallbackMessage || `Yêu cầu thất bại với mã lỗi: ${code}`;
  }
}
