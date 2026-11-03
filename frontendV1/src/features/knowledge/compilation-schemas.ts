import { z } from "zod";
import type {
  AutoReviewStatus,
  CompilationOrigin,
  CompilationStatus,
  DraftAssessmentStatus,
  ReviewStatus,
  SourceAssessmentStatus,
} from "./compilation-types";

// ==========================================
// Zod Validation Schemas
// ==========================================

export const draftParagraphSchema = z.object({
  text: z.string().min(1, "Nội dung đoạn không được rỗng").max(20000),
  citations: z
    .array(z.string().min(1))
    .min(1, "Mỗi đoạn cần ít nhất 1 citation"),
});

export const draftSectionSchema = z.object({
  heading: z.string().min(1, "Tiêu đề mục không được rỗng").max(500),
  paragraphs: z
    .array(draftParagraphSchema)
    .min(1, "Mục cần ít nhất 1 đoạn văn"),
});

export const draftContentSchema = z.object({
  title: z.string().min(1, "Tiêu đề bản biên soạn không được rỗng").max(500),
  sections: z.array(draftSectionSchema).min(1, "Cần ít nhất 1 mục nội dung"),
  unknowns: z.array(z.string().min(1).max(2000)).default([]),
});

export const compilationRequestSchema = z
  .object({
    topic: z
      .string()
      .transform((val) => val.trim())
      .pipe(
        z
          .string()
          .min(1, "Chủ đề biên soạn không được để trống")
          .max(2000, "Chủ đề tối đa 2000 ký tự"),
      ),
    ocr_run_ids: z
      .array(z.string().min(1).max(64))
      .min(1, "Chọn ít nhất 1 lượt xử lý OCR")
      .max(20, "Tối đa 20 lượt xử lý OCR")
      .refine(
        (items) => new Set(items).size === items.length,
        "Không được chọn trùng lượt OCR",
      ),
    text_versions: z.record(z.string(), z.number().int().min(0)).default({}),
    provider_id: z.string().nullable().optional(),
    max_output_tokens: z
      .number()
      .int()
      .positive("Số token phải là số nguyên dương")
      .nullable()
      .optional(),
    structured_output: z.boolean().default(false),
    source_first: z.boolean().optional(),
    auto_review: z.boolean().default(true),
    review_provider_id: z.string().nullable().optional(),
    review_max_output_tokens: z
      .number()
      .int()
      .positive("Số token review phải là số nguyên dương")
      .nullable()
      .optional(),
    review_structured_output: z.boolean().default(false),
  })
  .refine(
    (data) => {
      const runSet = new Set(data.ocr_run_ids);
      return Object.keys(data.text_versions).every((id) => runSet.has(id));
    },
    {
      message: "Phiên bản văn bản phải thuộc OCR đã chọn.",
      path: ["text_versions"],
    },
  );

export const editPreviewRequestSchema = z.object({
  expected_bundle_sha256: z
    .string()
    .regex(/^[a-f0-9]{64}$/, "Bundle SHA-256 không hợp lệ"),
  reason: z
    .string()
    .transform((val) => val.trim())
    .pipe(
      z
        .string()
        .min(1, "Lý do chỉnh sửa không được để trống")
        .max(2000, "Lý do tối đa 2000 ký tự"),
    ),
  review_id: z.string().nullable().optional(),
  content: draftContentSchema,
});

export const acceptEditSchema = z.object({
  preview_id: z.string().min(1, "Thiếu preview ID").max(64),
  preview_sha256: z
    .string()
    .regex(/^[a-f0-9]{64}$/, "Preview SHA-256 không hợp lệ"),
});

export const manualReviewRequestSchema = z.object({
  provider_id: z.string().nullable().optional(),
  max_output_tokens: z
    .number()
    .int()
    .positive("Số token review phải là số nguyên dương")
    .nullable()
    .optional(),
  structured_output: z.boolean().default(false),
});

// ==========================================
// Formatting & Status Helpers
// ==========================================

export function formatCompilationStatus(status: CompilationStatus): {
  label: string;
  variant: "default" | "secondary" | "destructive" | "outline";
} {
  switch (status) {
    case "queued":
      return { label: "Đang chờ xếp lịch", variant: "secondary" };
    case "running":
      return { label: "Đang biên soạn", variant: "default" };
    case "completed":
      return { label: "Đã hoàn thành", variant: "outline" };
    case "failed":
      return { label: "Thất bại", variant: "destructive" };
    case "uncertain":
      return { label: "Chưa chắc chắn", variant: "destructive" };
    case "cancelled":
      return { label: "Đã hủy", variant: "secondary" };
    default:
      return { label: status, variant: "outline" };
  }
}

export function formatCompilationOrigin(origin: CompilationOrigin): {
  label: string;
  isEdit: boolean;
} {
  switch (origin) {
    case "user_edit":
      return { label: "Người dùng chỉnh sửa", isEdit: true };
    default:
      return { label: "AI Biên soạn", isEdit: false };
  }
}

export function formatAutoReviewStatus(status: AutoReviewStatus | "none"): {
  label: string;
  variant: "default" | "secondary" | "destructive" | "outline";
} {
  switch (status) {
    case "cancelled":
      return { label: "Đã dừng rà soát", variant: "outline" };
    case "queued":
      return { label: "Đang chờ review tự động", variant: "secondary" };
    case "running":
      return { label: "Đang rà soát tự động", variant: "default" };
    case "completed":
      return { label: "Đã hoàn thành review", variant: "outline" };
    case "failed":
      return { label: "Review tự động lỗi", variant: "destructive" };
    case "uncertain":
      return { label: "Review chưa chắc chắn", variant: "destructive" };
    default:
      return { label: "Chưa có review tự động", variant: "secondary" };
  }
}

export function formatReviewStatus(status: ReviewStatus): {
  label: string;
  variant: "default" | "secondary" | "destructive" | "outline";
} {
  switch (status) {
    case "cancelled":
      return { label: "Đã dừng rà soát", variant: "outline" };
    case "queued":
      return { label: "Đang chờ reviewer", variant: "secondary" };
    case "running":
      return { label: "Đang đánh giá", variant: "default" };
    case "completed":
      return { label: "Hoàn tất đánh giá", variant: "outline" };
    case "failed":
      return { label: "Đánh giá lỗi", variant: "destructive" };
    case "uncertain":
      return { label: "Đánh giá không chắc chắn", variant: "destructive" };
    default:
      return { label: status, variant: "outline" };
  }
}

export function formatReviewVerdict(
  verdict: "needs_attention" | "no_issues_detected" | null | undefined,
): {
  label: string;
  variant: "destructive" | "default" | "secondary";
  description: string;
} {
  switch (verdict) {
    case "needs_attention":
      return {
        label: "Có nội dung cần xem lại",
        variant: "destructive",
        description:
          "Phát hiện các điểm có thể bị bỏ sót, suy diễn không đủ căn cứ hoặc mâu thuẫn nguồn.",
      };
    case "no_issues_detected":
      return {
        label: "Chưa phát hiện vấn đề",
        variant: "default",
        description:
          "Trong phạm vi nguồn và bản nháp đã đối chiếu, reviewer không tìm thấy điểm mâu thuẫn.",
      };
    default:
      return {
        label: "Chưa có kết luận",
        variant: "secondary",
        description: "Báo cáo chưa hoàn tất hoặc không xác định được verdict.",
      };
  }
}

export function formatSourceAssessmentStatus(status: SourceAssessmentStatus): {
  label: string;
  description: string;
  badgeClass: string;
} {
  switch (status) {
    case "covered":
      return {
        label: "Đã phản ánh",
        description: "Ý từ nguồn đã có vị trí tương ứng trong bản nháp.",
        badgeClass: "bg-success/15 text-success border-success/30",
      };
    case "omitted":
      return {
        label: "Có thể bỏ sót ý",
        description: "Ý trong nguồn chưa thấy được diễn đạt trong bản nháp.",
        badgeClass: "bg-destructive/15 text-destructive border-destructive/30",
      };
    case "out_of_scope":
      return {
        label: "Ngoài phạm vi chủ đề",
        description: "Nội dung nguồn nằm ngoài chủ đề biên soạn.",
        badgeClass: "bg-muted text-muted-foreground border-border",
      };
    case "uncertain":
      return {
        label: "Cần đối chiếu thêm",
        description: "Chưa đủ căn cứ để kết luận nguồn đã phản ánh hay chưa.",
        badgeClass: "bg-warning/15 text-warning border-warning/30",
      };
    default:
      return {
        label: status,
        description: "",
        badgeClass: "bg-muted text-muted-foreground",
      };
  }
}

export function formatDraftAssessmentStatus(status: DraftAssessmentStatus): {
  label: string;
  description: string;
  badgeClass: string;
} {
  switch (status) {
    case "supported":
      return {
        label: "Có căn cứ nguồn",
        description: "Đoạn biên soạn khớp với bằng chứng nguồn.",
        badgeClass: "bg-success/15 text-success border-success/30",
      };
    case "contradicted":
      return {
        label: "Có thể diễn giải sai",
        description: "Đoạn biên soạn mâu thuẫn hoặc đảo ngược ý so với nguồn.",
        badgeClass: "bg-destructive/15 text-destructive border-destructive/30",
      };
    case "unsupported":
      return {
        label: "Chưa thấy căn cứ",
        description:
          "Không tìm thấy bằng chứng nguồn hỗ trợ cho phát biểu này.",
        badgeClass: "bg-destructive/15 text-destructive border-destructive/30",
      };
    case "uncertain":
      return {
        label: "Cần đối chiếu thêm",
        description: "Chưa đủ cơ sở để khẳng định đúng hay sai.",
        badgeClass: "bg-warning/15 text-warning border-warning/30",
      };
    default:
      return {
        label: status,
        description: "",
        badgeClass: "bg-muted text-muted-foreground",
      };
  }
}

export function formatCompilationError(
  code: string | undefined,
  fallbackMessage: string = "",
): string {
  switch (code) {
    case "compilation_not_found":
      return "Không tìm thấy lượt biên soạn trong kho tri thức.";
    case "compilation_source_mismatch":
      return "Bằng chứng OCR hoặc bản sửa đã bị thay đổi so với thời điểm yêu cầu.";
    case "ocr_run_not_found":
      return "Một trong các lượt OCR đã chọn không tồn tại hoặc không thuộc kho này.";
    case "compilation_draft_invalid":
      return "Mô hình trả bản nháp không đúng cấu trúc yêu cầu.";
    case "compilation_draft_empty":
      return "Không có nội dung đủ căn cứ để tạo bản nháp từ nguồn đã chọn.";
    case "compilation_source_limits_exceeded":
      return "Nguồn vượt dung lượng cấu trúc của một bản nháp. Hãy chọn ít nguồn hơn cho lượt này.";
    case "compilation_failed":
      return "Hệ thống gặp lỗi khi xử lý kết quả biên soạn.";
    case "chat_output_truncated":
      return "Phản hồi của mô hình bị cắt trước khi nhóm biên soạn hoàn tất.";
    case "compilation_citation_invalid":
      return "Bản nháp có citation không thuộc tập bằng chứng nguồn đã cấp.";
    case "compilation_edit_stale":
      return "Bản xem trước đã hết hạn hoặc bản gốc đã có chỉnh sửa mới. Vui lòng tạo bản xem trước mới.";
    case "compilation_edit_empty":
      return "Nội dung chưa có thay đổi hoặc chưa nhập lý do chỉnh sửa.";
    case "compilation_edit_invalid":
      return "Bản sửa cần có nội dung và các citation phải thuộc nguồn đã ghim.";
    case "compilation_edit_not_found":
      return "Không tìm thấy bản xem trước của bạn.";
    case "compilation_edit_preview_changed":
      return "Bản xem trước không khớp với dữ liệu đã tạo.";
    case "idempotency_conflict":
      return "Khóa lưu trùng lặp với một thao tác khác.";
    case "compilation_auto_review_not_found":
      return "Chưa có yêu cầu review tự động cho lượt này.";
    case "compilation_review_invalid":
      return "Reviewer trả kết quả không đúng schema hoặc thiếu đối chiếu ID.";
    case "model_token_limits_stale":
      return "Thông số giới hạn của model đã cũ do mới đổi tên model. Vui lòng cập nhật hoặc xóa giới hạn cũ trong ModelOps.";
    case "model_input_budget_unknown":
      return "Chưa xác định được ngân sách đầu vào của model đã chọn.";
    case "model_output_limit_exceeded":
      return "Số token đầu ra yêu cầu vượt quá giới hạn tối đa đã khai báo của model.";
    case "model_context_limit_exceeded":
      return "Tổng ngữ cảnh và đầu ra vượt quá cửa sổ ngữ cảnh (context window) của model.";
    case "quota_exceeded":
    case "provider_rate_limited":
      return "Hết hạn mức (Quota) hoặc bị giới hạn tần suất (HTTP 429) từ nhà cung cấp AI.";
    case "provider_timeout":
      return "Quá thời gian chờ phản hồi từ nhà cung cấp AI (Timeout).";
    case "provider_response_malformed":
      return "Model trả về dữ liệu không đúng định dạng JSON/schema yêu cầu.";
    default:
      return (
        fallbackMessage || "Đã xảy ra lỗi trong quá trình xử lý biên soạn."
      );
  }
}

export function generateIdempotencyKey(): string {
  return `cmp_${crypto.randomUUID().replace(/-/g, "")}`;
}

export function validateReviewIdempotencyKey(key: string): boolean {
  if (!key || key.length < 8 || key.length > 128) return false;
  if (key.startsWith("auto:") || key.startsWith("edit:")) return false;
  return true;
}
