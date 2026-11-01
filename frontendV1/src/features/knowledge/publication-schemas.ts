import { z } from "zod";
import type {
  CompiledDocumentStatus,
  DecisionAction,
} from "./publication-types.ts";

export const DOCUMENT_KEY_REGEX = /^[a-z0-9][a-z0-9_.-]*$/;
export const SHA256_HEX_REGEX = /^[0-9a-f]{64}$/;

export const createDocumentSchema = z.object({
  document_key: z
    .string()
    .min(1, "Document key không được để trống")
    .max(120, "Document key tối đa 120 ký tự")
    .regex(
      DOCUMENT_KEY_REGEX,
      "Key chỉ gồm chữ thường không dấu, số, gạch ngang, gạch dưới hoặc dấu chấm (bắt đầu bằng chữ hoặc số)",
    ),
  title: z
    .string()
    .transform((val) => val.trim())
    .pipe(
      z
        .string()
        .min(1, "Tiêu đề tài liệu không được để trống")
        .max(255, "Tiêu đề tối đa 255 ký tự"),
    ),
  compilation_run_id: z
    .string()
    .min(1, "Chưa chọn lượt biên soạn")
    .max(64, "Mã lượt biên soạn không hợp lệ"),
});

export const registerVersionSchema = z.object({
  compilation_run_id: z
    .string()
    .min(1, "Chưa chọn lượt biên soạn")
    .max(64, "Mã lượt biên soạn không hợp lệ"),
});

export const findingResolutionSchema = z.object({
  finding_id: z
    .string()
    .regex(
      SHA256_HEX_REGEX,
      "ID vấn đề (finding_id) phải là chuỗi SHA-256 hợp lệ",
    ),
  decision: z.enum(["accepted_risk", "not_an_issue"]),
  reason: z
    .string()
    .transform((val) => val.trim())
    .pipe(
      z
        .string()
        .min(10, "Lý do giải trình tối thiểu 10 ký tự")
        .max(2000, "Lý do giải trình tối đa 2000 ký tự"),
    ),
});

export const reviewAckSchema = z.object({
  review_id: z.string().min(1, "Mã review không được rỗng").max(64),
  report_sha256: z
    .string()
    .regex(SHA256_HEX_REGEX, "Hash báo cáo phải là chuỗi SHA-256 hợp lệ"),
  confirmed_reviewed: z.literal(true),
  resolutions: z.array(findingResolutionSchema).default([]),
  retrieval_metadata_sha256: z
    .string()
    .regex(SHA256_HEX_REGEX, "Hash metadata truy xuất không hợp lệ")
    .optional(),
});

export const decisionPreviewSchema = z
  .object({
    action: z.enum(["approve", "publish", "withdraw"]),
    reason: z
      .string()
      .transform((val) => val.trim())
      .pipe(
        z
          .string()
          .min(1, "Lý do quyết định không được để trống")
          .max(1000, "Lý do tối đa 1000 ký tự"),
      ),
    review_ack: reviewAckSchema.optional().nullable(),
    review_skip: z
      .object({
        confirmed_skip: z.literal(true),
        version_id: z.string().min(1).max(64),
        bundle_sha256: z.string().regex(SHA256_HEX_REGEX),
        retrieval_metadata_sha256: z
          .string()
          .regex(SHA256_HEX_REGEX)
          .optional(),
      })
      .optional(),
  })
  .refine(
    (value) =>
      !value.review_skip ||
      (value.action === "approve" &&
        !value.review_ack &&
        value.reason.length >= 10),
    "Cần xác nhận và lý do bỏ qua review; chỉ chọn một cách duyệt.",
  );

export const decisionCommitSchema = z.object({
  preview_id: z.string().min(1, "Mã preview không được để trống").max(64),
  preview_sha256: z
    .string()
    .regex(SHA256_HEX_REGEX, "Hash bản xem trước không hợp lệ"),
});

export function slugifyKey(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "d")
    .toLowerCase()
    .replace(/[^a-z0-9_.-]+/g, "-")
    .replace(/^[-_.]+|[-_.]+$/g, "")
    .slice(0, 80);
}

export function generatePublicationIdempotencyKey(prefix = "pub"): string {
  return `${prefix}_${crypto.randomUUID().replace(/-/g, "")}`;
}

export function formatPublicationStatus(status: CompiledDocumentStatus): {
  label: string;
  badgeClass: string;
} {
  switch (status) {
    case "draft":
      return {
        label: "Bản nháp",
        badgeClass: "bg-muted text-muted-foreground border-border",
      };
    case "approved":
      return {
        label: "Đã duyệt",
        badgeClass: "bg-info/10 text-info border-info/30",
      };
    case "published":
      return {
        label: "Đang xuất bản",
        badgeClass: "bg-success/15 text-success border-success/30 font-medium",
      };
    case "superseded":
      return {
        label: "Đã thay thế",
        badgeClass: "bg-muted/80 text-muted-foreground/80 border-border",
      };
    case "withdrawn":
      return {
        label: "Đã thu hồi",
        badgeClass: "bg-destructive/10 text-destructive border-destructive/30",
      };
    default:
      return {
        label: status,
        badgeClass: "bg-muted text-muted-foreground border-border",
      };
  }
}

export function formatDecisionAction(action: DecisionAction): {
  label: string;
  verb: string;
  variant: "default" | "destructive" | "outline" | "secondary";
} {
  switch (action) {
    case "approve":
      return {
        label: "Duyệt phiên bản",
        verb: "duyệt",
        variant: "secondary",
      };
    case "publish":
      return {
        label: "Xuất bản phiên bản",
        verb: "xuất bản",
        variant: "default",
      };
    case "withdraw":
      return {
        label: "Thu hồi phiên bản",
        verb: "thu hồi",
        variant: "destructive",
      };
    default:
      return {
        label: action,
        verb: action,
        variant: "outline",
      };
  }
}

export function formatPublicationError(
  code: string | undefined,
  fallbackMessage = "",
): string {
  switch (code) {
    case "compiled_document_key_exists":
      return "Document key đã tồn tại trong kho này. Vui lòng chọn tài liệu có sẵn để thêm phiên bản mới.";
    case "compiled_run_registered":
      return "Lượt biên soạn này đã được đăng ký thành phiên bản tài liệu trước đó.";
    case "compiled_document_not_found":
      return "Không tìm thấy tài liệu biên soạn.";
    case "compiled_version_not_found":
      return "Không tìm thấy phiên bản biên soạn.";
    case "publication_review_required":
      return "Cần có lượt rà soát (Review) hoàn tất khớp phiên bản trước khi duyệt.";
    case "publication_review_invalid":
      return "Báo cáo rà soát không khớp với phiên bản hiện tại.";
    case "publication_review_stale":
      return "Báo cáo rà soát đã thay đổi, vui lòng xem lại và xác nhận lại.";
    case "publication_review_unresolved":
      return "Cần giải trình đầy đủ từng vấn đề trong báo cáo rà soát (không thiếu, không thừa, không trùng).";
    case "publication_metadata_review_required":
      return "Cần xác nhận đã xem đúng metadata truy xuất của phiên bản trước khi duyệt.";
    case "retrieval_metadata_invalid":
      return "Metadata truy xuất không hợp lệ: target phải tồn tại trong bản biên soạn, mỗi giá trị phải xuất hiện trong trích đoạn nguồn và không được trùng target.";
    case "publication_bundle_changed":
      return "Nội dung hoặc metadata đã khác bản đã đăng ký/duyệt. Vui lòng đăng ký lại phiên bản.";
    case "publication_approval_required":
      return "Phiên bản phải được duyệt (Approve) trước khi có thể xuất bản.";
    case "publication_transition_invalid":
      return "Trạng thái hiện tại của phiên bản không cho phép thực hiện thao tác này.";
    case "publication_preview_not_found":
      return "Không tìm thấy thông tin xem trước (Preview) quyết định.";
    case "publication_preview_expired":
      return "Thông tin xem trước quyết định đã hết hạn. Vui lòng xem trước lại.";
    case "publication_preview_mismatch":
      return "Nội dung xác nhận không khớp với thông tin đã xem trước.";
    case "publication_preview_stale":
      return "Trạng thái tài liệu hoặc phiên bản đã thay đổi. Vui lòng tạo bản xem trước mới.";
    case "publication_preview_consumed":
      return "Bản xem trước quyết định này đã được sử dụng.";
    case "published_compilation_not_found":
      return "Tài liệu chưa có phiên bản nào đang xuất bản.";
    case "idempotency_conflict":
      return "Khóa Idempotency-Key đã được sử dụng cho một yêu cầu khác.";
    default:
      return (
        fallbackMessage ||
        "Đã xảy ra lỗi trong quá trình xử lý tài liệu biên soạn."
      );
  }
}
