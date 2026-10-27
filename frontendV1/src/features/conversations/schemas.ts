import { z } from "zod";

/**
 * Validation rules strictly mirroring backend schemas:
 * - ConversationCreate: title 1-160 chars, assistant_id 1-64 chars
 * - ConversationUpdate: title 1-160 chars, status "active" | "archived"
 * - TurnRequest: question 1-8000 chars, expected_turn_no int >= 0
 */

export const conversationTitleSchema = z
  .string()
  .trim()
  .min(1, "Tiêu đề hội thoại không được để trống")
  .max(160, "Tiêu đề hội thoại tối đa 160 ký tự");

export const conversationStatusSchema = z.enum(["active", "archived"]);

export const conversationCreateSchema = z.object({
  assistant_id: z
    .string()
    .min(1, "Trợ lý không hợp lệ")
    .max(64, "Mã trợ lý tối đa 64 ký tự"),
  title: conversationTitleSchema.default("Hội thoại mới"),
});

export const conversationUpdateSchema = z.object({
  title: conversationTitleSchema,
  status: conversationStatusSchema,
});

export const turnQuestionSchema = z
  .string()
  .trim()
  .min(1, "Câu hỏi không được để trống")
  .max(8000, "Câu hỏi tối đa 8000 ký tự");

export const expectedTurnNoSchema = z
  .number()
  .int("Số thứ tự phải là số nguyên")
  .min(0, "Số thứ tự không thể âm");

export const turnRequestSchema = z.object({
  question: turnQuestionSchema,
  expected_turn_no: expectedTurnNoSchema,
});

export const conversationListSearchSchema = z.object({
  limit: z.coerce.number().int().min(1).max(100).default(20),
  offset: z.coerce.number().int().min(0).default(0),
});

export const DEFAULT_CONVERSATION_SEARCH = {
  limit: 20,
  offset: 0,
} as const;

/**
 * Generates an RFC 4122 v4 UUID or standard compliant fallback string
 * adhering to the backend regex: ^[A-Za-z0-9_.:-]+$ (1-128 chars).
 */
export function generateIdempotencyKey(): string {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID();
  }
  return `key_${Date.now()}_${Math.random().toString(36).slice(2, 12)}`;
}

/**
 * Maps standard backend error codes into honest, user-friendly Vietnamese explanations.
 */
export function formatConversationError(
  code?: string | null,
  fallbackMessage?: string,
): string {
  if (!code) return fallbackMessage || "Đã xảy ra lỗi không xác định.";

  switch (code) {
    case "conversation_busy":
      return "Hội thoại đang xử lý một lượt hỏi khác. Vui lòng đợi lượt hiện tại hoàn tất.";
    case "conversation_sequence_conflict":
      return "Lịch sử hội thoại đã thay đổi; vui lòng làm mới để cập nhật số thứ tự lượt hỏi mới nhất.";
    case "idempotency_conflict":
      return "Khóa Idempotency-Key đã được sử dụng cho câu hỏi khác. Vui lòng thử lại với lượt mới.";
    case "conversation_turn_running":
      return "Lượt hỏi này đang được xử lý bởi hệ thống.";
    case "conversation_assistant_changed":
      return "Cấu hình trợ lý đã thay đổi; cần tạo hội thoại mới để áp dụng cấu hình mới nhất.";
    case "assistant_inactive":
      return "Trợ lý AI này đã tạm dừng hoạt động; không thể gửi câu hỏi mới.";
    case "conversation_archived":
      return "Hội thoại đã được lưu trữ. Mở lại hội thoại để tiếp tục trò chuyện.";
    case "answer_evidence_changed":
      return "Nguồn tài liệu chứng minh đã thay đổi; câu trả lời cũ không còn hiệu lực.";
    case "conversation_turn_expired":
      return "Lượt hỏi đã hết hạn thực thi (quá thời hạn lease).";
    case "conversation_turn_interrupted":
      return "Lượt hỏi bị gián đoạn hoặc chưa thể xác định kết quả.";
    case "operation_cancelled":
      return "Lượt hỏi đã bị hủy trước khi hoàn tất (dừng trợ lý hoặc lưu trữ hội thoại). Không có câu trả lời nào được ghi nhận.";
    case "conversation_scope_conflict":
      return "Phạm vi metadata gửi kèm mâu thuẫn với phạm vi cố định của trợ lý. Bỏ bớt trường bị khóa hoặc mở hội thoại mới.";
    case "answer_not_supported":
      return "Câu trả lời không được nguồn trích dẫn hỗ trợ nên không được phát hành.";
    case "answer_verification_uncertain":
      return "Bước kiểm chứng chưa xác định được căn cứ của câu trả lời.";
    case "answer_verification_invalid":
      return "Báo cáo kiểm chứng do mô hình trả về không hợp lệ; lượt hỏi bị dừng để tránh phát hành câu trả lời chưa kiểm chứng.";
    case "answer_context_budget_exceeded":
      return "Ngữ cảnh vượt ngân sách byte đã cấu hình nên lượt hỏi không thể hoàn tất. Tăng ngân sách ngữ cảnh hoặc thu hẹp câu hỏi.";
    case "conversation_not_found":
      return "Không tìm thấy hội thoại yêu cầu.";
    case "conversation_turn_not_found":
      return "Không tìm thấy lượt hỏi yêu cầu.";
    default:
      return fallbackMessage || `Yêu cầu thất bại với mã lỗi: ${code}`;
  }
}
